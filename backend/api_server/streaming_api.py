"""
FastAPI Streaming Conversation API
Provides real-time streaming interface for model conversations with action tracking
"""
import os
import json
import uuid
import asyncio
import queue
import threading
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import the model system
from base_test_azure_hybrid import BoilerplatePersistentGroq, FrontendCommandInterrupt

app = FastAPI(title="Model Conversation API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for active conversations
active_conversations: Dict[str, BoilerplatePersistentGroq] = {}
conversation_metadata: Dict[str, dict] = {}

class ConversationRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    action_result: Optional[bool] = False

class StreamChunk(BaseModel):
    type: str  # "text", "action_start", "action_content", "action_result", "error"
    data: dict
    conversation_id: str
    timestamp: str
    action_id: Optional[str] = None

class ConversationInfo(BaseModel):
    conversation_id: str
    project_id: Optional[str]
    created_at: str
    last_activity: str
    message_count: int
    status: str

def generate_conversation_id() -> str:
    """Generate a unique conversation ID"""
    return f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

def get_api_key() -> str:
    """Get API key from environment"""
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is required")
    return api_key

def create_stream_chunk(chunk_type: str, data: dict, conversation_id: str, action_id: str = None) -> str:
    """Create a properly formatted stream chunk"""
    chunk = StreamChunk(
        type=chunk_type,
        data=data,
        conversation_id=conversation_id,
        timestamp=datetime.now().isoformat(),
        action_id=action_id
    )
    return f"data: {chunk.model_dump_json()}\n\n"

class StreamingModelWrapper:
    """Wrapper to capture model streaming and actions"""
    
    def __init__(self, model_system: BoilerplatePersistentGroq, conversation_id: str):
        self.model_system = model_system
        self.conversation_id = conversation_id
        self.current_action_id = None
        
        # Load existing streaming chunks from this conversation (cumulative approach)
        project_id = getattr(model_system, 'project_id', None)
        if project_id:
            try:
                from cloud_storage import AzureBlobStorage
                cloud_storage = AzureBlobStorage()
                self.streaming_chunks = cloud_storage.load_conversation_history_streaming(project_id)
                print(f"📦 Loaded {len(self.streaming_chunks)} existing streaming chunks from conversation")
            except Exception as e:
                print(f"⚠️ Failed to load existing streaming chunks: {e}")
                self.streaming_chunks = []
        else:
            self.streaming_chunks = []  # New conversation, start fresh
            
        self.last_save_count = len(self.streaming_chunks)  # Track baseline for saves
    
    async def stream_response(self, message: str) -> AsyncGenerator[str, None]:
        """Stream the model response with action tracking"""
        try:
            print(f"🌊 Starting stream_response for: {message[:30]}...")
            # Use a simple thread-safe queue
            import queue
            stream_queue = queue.Queue()
            action_counter = 0
            model_finished = threading.Event()
            
            def queue_callback(content_type: str, content: str, action_data: dict = None):
                """Callback to add content to stream queue (thread-safe)"""
                nonlocal action_counter
                
                if content_type == "action_start":
                    action_counter += 1
                    action_id = f"action_{action_counter}"
                    chunk = create_stream_chunk("action_start", {
                        "action_type": action_data.get("action_type") if action_data else "unknown",
                        "action_details": action_data or {},
                        "content": content
                    }, self.conversation_id, action_id)
                elif content_type == "action_result":
                    # Extract important fields to root level for file operations
                    data = {
                        "result": content,
                        "status": action_data.get("status") if action_data else "completed",
                        "action_details": action_data or {}
                    }
                    
                    # For file operations, include action_type and content at root level
                    if action_data:
                        action_type = action_data.get("action_type")
                        if action_type in ["read_file", "create_file", "update_file"]:
                            data["action_type"] = action_type
                            if "content" in action_data:
                                data["content"] = action_data["content"]
                            if "file_path" in action_data:
                                data["file_path"] = action_data["file_path"]
                    
                    chunk = create_stream_chunk("action_result", data, self.conversation_id, f"action_{action_counter}")
                elif content_type == "assistant_message":
                    chunk = create_stream_chunk("assistant_message", {
                        "content": content
                    }, self.conversation_id)
                elif content_type == "error":
                    chunk = create_stream_chunk("error", {
                        "error": content,
                        "action_details": action_data or {}
                    }, self.conversation_id)
                else:
                    # Legacy text type - convert to assistant message
                    chunk = create_stream_chunk("assistant_message", {
                        "content": content
                    }, self.conversation_id)
                
                # Collect streaming chunk in memory (save at strategic points for performance)
                try:
                    import json
                    
                    # Parse the chunk data to collect it
                    chunk_lines = chunk.split('\n')
                    data_line = next((line for line in chunk_lines if line.startswith('data: ')), None)
                    
                    if data_line:
                        chunk_json_str = data_line[6:]  # Remove 'data: '
                        chunk_data = json.loads(chunk_json_str)
                        
                        # Collect in memory for batch saving later
                        self.streaming_chunks.append(chunk_data)
                        
                        # Strategic saving at certain points
                        should_save_now = (
                            # Save every 10 chunks to avoid losing too much data
                            len(self.streaming_chunks) % 10 == 0 or
                            # Save after action_result chunks (good completion points)
                            content_type == "action_result" or
                            # Save after assistant_message chunks that look like completions
                            (content_type == "assistant_message" and 
                             ("completed" in content.lower() or "✅" in content or "finished" in content.lower()))
                        )
                        
                        if should_save_now:
                            # Non-blocking save in background thread
                            import threading
                            save_thread = threading.Thread(
                                target=self._save_streaming_chunks_sync, 
                                daemon=True
                            )
                            save_thread.start()
                            
                except Exception as e:
                    print(f"⚠️ Failed to collect streaming chunk: {e}")
                
                # Thread-safe queue put
                stream_queue.put(chunk)
            
            # Yield conversation/project identifiers FIRST (most important!)
            project_id = getattr(self.model_system, 'project_id', None)
            yield create_stream_chunk("conversation_info", {
                "conversation_id": self.conversation_id,
                "project_id": project_id,
                "timestamp": datetime.now().isoformat(),
                "status": "streaming_started"
            }, self.conversation_id)
            await asyncio.sleep(0.01)  # Allow immediate flush
            
            # Yield initial processing message
            yield create_stream_chunk("text", {
                "content": f"🚀 Processing your request: {message[:100]}..."
            }, self.conversation_id)
            await asyncio.sleep(0.01)  # Allow immediate flush
            
            # Start model execution in background thread
            def run_model():
                try:
                    result = self._execute_model_with_streaming(message, queue_callback)
                    stream_queue.put(("FINAL_RESULT", result))
                except Exception as e:
                    stream_queue.put(("ERROR", str(e)))
                finally:
                    model_finished.set()
                    stream_queue.put(("FINISHED", None))
            
            model_thread = threading.Thread(target=run_model, daemon=True)
            model_thread.start()
            
            # Stream content from queue with immediate yielding
            while True:
                try:
                    # Wait for items with very short timeout for real-time streaming
                    item = stream_queue.get(timeout=0.01)
                    
                    if isinstance(item, tuple):
                        command, data = item
                        if command == "FINAL_RESULT":
                            project_id = getattr(self.model_system, 'project_id', None)
                            yield create_stream_chunk("text", {
                                "content": "✅ Conversation completed successfully",
                                "final_result": data,
                                "project_id": project_id
                            }, self.conversation_id)
                        elif command == "ERROR":
                            project_id = getattr(self.model_system, 'project_id', None)
                            yield create_stream_chunk("error", {
                                "error": data,
                                "message": "An error occurred during model execution",
                                "project_id": project_id
                            }, self.conversation_id)
                        elif command == "FINISHED":
                            break
                    else:
                        # Regular stream chunk - yield immediately
                        yield item
                        await asyncio.sleep(0.001)  # Very brief pause for responsiveness
                        
                except queue.Empty:
                    # Check if model finished - if so, break after a short delay
                    if model_finished.is_set():
                        # Give a little time for any final messages
                        await asyncio.sleep(0.1)
                        # Check one more time for any remaining items
                        try:
                            while True:
                                item = stream_queue.get_nowait()
                                if isinstance(item, tuple) and item[0] == "FINISHED":
                                    break
                                elif not isinstance(item, tuple):
                                    yield item
                                    await asyncio.sleep(0.001)
                        except queue.Empty:
                            pass
                        break
                    # Continue waiting if model still running
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    yield create_stream_chunk("error", {
                        "error": str(e),
                        "message": "Error in streaming loop"
                    }, self.conversation_id)
                    break
        
        except Exception as e:
            yield create_stream_chunk("error", {
                "error": str(e),
                "message": "Failed to initialize streaming"
            }, self.conversation_id)
        finally:
            # Batch save all streaming chunks to Azure at the end
            await self._save_streaming_chunks_batch()
    
    def _execute_model_with_streaming(self, message: str, stream_callback) -> dict:
        """Execute the model request with proper action streaming"""
        try:
            # Initial status updates
            if hasattr(self.model_system, 'project_id') and self.model_system.project_id:
                stream_callback("assistant_message", f"I'll help you update your project: {self.model_system.project_id}")
                mode = "update"
            else:
                stream_callback("assistant_message", f"I'll create a new project for you based on your request.")
                mode = "creation"
            
            # Call the actual processing method with streaming callback
            if hasattr(self.model_system, '_process_update_request_with_interrupts'):
                result = self.model_system._process_update_request_with_interrupts(message, streaming_callback=stream_callback)
                
                # Save conversation history
                if hasattr(self.model_system, '_save_conversation_history'):
                    self.model_system._save_conversation_history()
            else:
                stream_callback("error", f"{mode} processing method not available")
                result = f"{mode} processing method not available"
            
            return {
                "status": "completed",
                "result": result,
                "project_id": getattr(self.model_system, 'project_id', None)
            }
            
        except Exception as e:
            print(f"🐛 STREAMING API: Exception caught - type: {type(e).__name__}, class name: {e.__class__.__name__}")
            
            # Check if this is a frontend command interrupt
            if e.__class__.__name__ == 'FrontendCommandInterrupt':
                print(f"🚨 STREAMING API: FRONTEND COMMAND INTERRUPT DETECTED: {e.command}")
                print(f"🚨 STREAMING API: About to return interrupted status...")
                
                # Send the command to frontend via stream
                stream_callback("action_start", f"Running frontend command: {e.command}", {
                    "action_type": "run_command",
                    "command": e.command,
                    "cwd": e.cwd,
                    "needs_interrupt": True,
                    "project_id": e.project_id
                })
                
                # Return interrupt signal instead of continuing
                interrupt_result = {
                    "status": "interrupted",
                    "reason": "frontend_command",
                    "command": e.command,
                    "cwd": e.cwd,
                    "project_id": e.project_id,
                    "message": f"Stream interrupted for frontend command: {e.command}"
                }
                print(f"🚨 STREAMING API: Returning interrupt result: {interrupt_result}")
                return interrupt_result
            else:
                print(f"🐛 STREAMING API: Not a frontend interrupt, exception: {e}")
                stream_callback("error", f"Model execution failed: {str(e)}")
                raise Exception(f"Model execution failed: {str(e)}")
    
    async def _save_streaming_chunks_batch(self):
        """Batch save all collected streaming chunks to Azure Blob Storage"""
        try:
            if not self.streaming_chunks:
                print("📦 No streaming chunks to save")
                return
            
            project_id = getattr(self.model_system, 'project_id', None)
            if not project_id:
                print("⚠️ No project_id available for saving streaming chunks")
                return
            
            from cloud_storage import AzureBlobStorage
            cloud_storage = AzureBlobStorage()
            
            # Save all chunks in one operation
            success = cloud_storage.save_conversation_history_streaming(project_id, self.streaming_chunks)
            
            if success:
                print(f"✅ Batch saved {len(self.streaming_chunks)} streaming chunks to Azure")
            else:
                print(f"❌ Failed to batch save {len(self.streaming_chunks)} streaming chunks")
            
        except Exception as e:
            print(f"⚠️ Error during batch save of streaming chunks: {e}")
    
    def _save_streaming_chunks_sync(self):
        """Synchronous version of streaming chunks save for background thread"""
        try:
            if not self.streaming_chunks:
                return
            
            # Only save if we have new chunks since last save
            chunks_to_save = len(self.streaming_chunks)
            if chunks_to_save <= self.last_save_count:
                return
            
            project_id = getattr(self.model_system, 'project_id', None)
            if not project_id:
                return
            
            from cloud_storage import AzureBlobStorage
            cloud_storage = AzureBlobStorage()
            
            # Save all chunks (including previously saved ones - overwrite approach)
            success = cloud_storage.save_conversation_history_streaming(project_id, self.streaming_chunks)
            
            if success:
                new_chunks = chunks_to_save - self.last_save_count
                print(f"💾 Saved {new_chunks} new streaming chunks ({chunks_to_save} total)")
                self.last_save_count = chunks_to_save
            
        except Exception as e:
            print(f"⚠️ Background save error: {e}")

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "healthy",
        "service": "Model Conversation API",
        "version": "1.0.0",
        "active_conversations": len(active_conversations)
    }

@app.get("/conversations", response_model=List[ConversationInfo])
async def list_conversations():
    """List all active conversations"""
    conversations = []
    for conv_id, metadata in conversation_metadata.items():
        conversations.append(ConversationInfo(
            conversation_id=conv_id,
            project_id=metadata.get("project_id"),
            created_at=metadata.get("created_at"),
            last_activity=metadata.get("last_activity"),
            message_count=metadata.get("message_count", 0),
            status=metadata.get("status", "active")
        ))
    return conversations

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id in active_conversations:
        del active_conversations[conversation_id]
    if conversation_id in conversation_metadata:
        del conversation_metadata[conversation_id]
    return {"status": "deleted", "conversation_id": conversation_id}

@app.post("/chat/stream")
async def stream_chat(request: ConversationRequest):
    """Main streaming chat endpoint"""
    
    try:
        print(f"📡 Received streaming request: {request.message[:50]}...")
        
        # Check if this is an action result continuation (frontend sending command result back)
        is_action_result = getattr(request, 'action_result', False)
        
        # Determine if this is create or update mode
        # If we have a project_id, it's update mode (regardless of conversation_id)
        is_update_mode = bool(request.project_id)
        conversation_id = request.conversation_id or generate_conversation_id()
        
        print(f"📡 Generated conversation_id: {conversation_id}")
        print(f"📡 Update mode: {is_update_mode}")
        print(f"📡 Action result continuation: {is_action_result}")
        
        # Initialize or get existing model system
        if conversation_id not in active_conversations:
            api_key = get_api_key()
            
            if is_update_mode:
                # Update mode - use existing project
                print(f"🔄 Initializing update mode for project: {request.project_id}")
                model_system = BoilerplatePersistentGroq(
                    api_key=api_key,
                    project_id=request.project_id
                )
                mode = "update"
            else:
                # Create mode - generate new project name
                print(f"🚀 Initializing create mode")
                from base_test_azure_hybrid import generate_project_name
                
                base_project_name = generate_project_name(request.message)
                timestamp = datetime.now().strftime("%H%M%S")
                project_name = f"{base_project_name}-{timestamp}"
                
                model_system = BoilerplatePersistentGroq(api_key, project_name)
                mode = "create"
            
            active_conversations[conversation_id] = model_system
            conversation_metadata[conversation_id] = {
                "project_id": getattr(model_system, 'project_id', None),
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0,
                "status": "active",
                "mode": mode
            }
        else:
            model_system = active_conversations[conversation_id]
            conversation_metadata[conversation_id]["last_activity"] = datetime.now().isoformat()
        
        # Update message count
        conversation_metadata[conversation_id]["message_count"] += 1
        
        # Save user message to streaming conversation history (avoid command results)
        if not is_action_result:
            try:
                from cloud_storage import AzureBlobStorage
                
                project_id = getattr(model_system, 'project_id', None)
                if project_id:
                    user_message_chunk = {
                        "type": "user_message", 
                        "data": {
                            "content": request.message,
                            "message_type": "user"
                        },
                        "conversation_id": conversation_id,
                        "timestamp": datetime.now().isoformat(),
                        "action_id": None,
                        "is_command_result": False
                    }
                    
                    cloud_storage = AzureBlobStorage()
                    cloud_storage.append_streaming_chunk(project_id, user_message_chunk)
                    print(f"💾 Saved user message to streaming history")
                    
            except Exception as e:
                print(f"⚠️ Failed to save user message to streaming history: {e}")
        else:
            # This is a command result - save with special marker
            try:
                from cloud_storage import AzureBlobStorage
                
                project_id = getattr(model_system, 'project_id', None)
                if project_id:
                    command_result_chunk = {
                        "type": "user_message",
                        "data": {
                            "content": request.message,
                            "message_type": "user"
                        },
                        "conversation_id": conversation_id,
                        "timestamp": datetime.now().isoformat(),
                        "action_id": None,
                        "is_command_result": True
                    }
                    
                    cloud_storage = AzureBlobStorage()
                    cloud_storage.append_streaming_chunk(project_id, command_result_chunk)
                    print(f"💾 Saved command result to streaming history")
                    
            except Exception as e:
                print(f"⚠️ Failed to save command result to streaming history: {e}")
        
        # Create streaming wrapper
        streaming_wrapper = StreamingModelWrapper(model_system, conversation_id)
        
        # Return streaming response
        return StreamingResponse(
            streaming_wrapper.stream_response(request.message),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-ID": conversation_id,
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize conversation: {str(e)}")

@app.get("/conversations/{conversation_id}/info")
async def get_conversation_info(conversation_id: str):
    """Get detailed information about a conversation"""
    if conversation_id not in conversation_metadata:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    metadata = conversation_metadata[conversation_id]
    model_system = active_conversations.get(conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "metadata": metadata,
        "project_id": getattr(model_system, 'project_id', None) if model_system else None,
        "has_active_system": conversation_id in active_conversations
    }

@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Get the full conversation history for a specific conversation from Azure Blob Storage"""
    if conversation_id not in active_conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    model_system = active_conversations[conversation_id]
    project_id = getattr(model_system, 'project_id', None)
    
    if not project_id:
        raise HTTPException(status_code=404, detail="Project ID not found for conversation")
    
    # Load conversation history from Azure Blob Storage
    try:
        from cloud_storage import AzureBlobStorage
        cloud_storage = AzureBlobStorage()
        
        # Load conversation history using cloud storage method
        conversation_history = cloud_storage.load_conversation_history(project_id)
        
        return {
            "conversation_id": conversation_id,
            "project_id": project_id,
            "message_count": len(conversation_history),
            "messages": conversation_history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load conversation history: {str(e)}")

@app.get("/projects/{project_id}/history")
async def get_project_conversation_history(project_id: str):
    """Get conversation history directly by project ID from Azure Blob Storage"""
    try:
        from cloud_storage import AzureBlobStorage
        cloud_storage = AzureBlobStorage()
        
        # Load conversation history using cloud storage method
        conversation_history = cloud_storage.load_conversation_history(project_id)
        
        return {
            "project_id": project_id,
            "message_count": len(conversation_history),
            "messages": conversation_history,
            "source": "azure_blob_storage"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load conversation history: {str(e)}")

@app.get("/projects/{project_id}/history/streaming-format")
async def get_project_conversation_history_streaming_format(project_id: str):
    """Get conversation history in EXACT streaming format that frontend expects - from saved streaming data"""
    try:
        from cloud_storage import AzureBlobStorage
        
        cloud_storage = AzureBlobStorage()
        
        # First try to load from saved streaming conversation history
        streaming_chunks = cloud_storage.load_conversation_history_streaming(project_id)
        
        if streaming_chunks:
            # Return saved streaming data
            fake_conversation_id = f"conv_history_{project_id}"
            
            return {
                "project_id": project_id,
                "conversation_id": fake_conversation_id,
                "message_count": "calculated_from_streaming",
                "streaming_chunks_count": len(streaming_chunks),
                "streaming_chunks": streaming_chunks,
                "source": "azure_blob_storage_streaming",
                "format": "live_streaming_format"
            }
        
        else:
            # Fallback: convert from raw conversation history if no streaming data exists
            from conversation_history_converter import ConversationHistoryConverter
            
            print(f"⚠️ No streaming data found for {project_id}, converting from raw conversation history")
            conversation_history = cloud_storage.load_conversation_history(project_id)
            
            if conversation_history:
                converter = ConversationHistoryConverter()
                result = converter.convert_to_streaming_format(conversation_history, project_id)
                result["source"] = "azure_blob_storage_converted"
                result["format"] = "converted_from_raw"
                return result
            else:
                return {
                    "project_id": project_id,
                    "conversation_id": f"conv_history_{project_id}",
                    "message_count": 0,
                    "streaming_chunks_count": 0,
                    "streaming_chunks": [],
                    "source": "empty",
                    "format": "no_data_found"
                }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load conversation history in streaming format: {str(e)}")

# ===== WEBCONTAINER INTEGRATION ENDPOINTS =====

@app.post("/projects/create")
async def create_project_for_webcontainer(request: dict):
    """Create a new project for webcontainer using the same flow as streaming chat"""
    try:
        from base_test_azure_hybrid import BoilerplatePersistentGroq, generate_project_name
        
        # Get initial message to generate project name, default to generic name
        initial_message = request.get('initial_message', 'New WebContainer Project')
        
        print(f"🚀 Creating new project for webcontainer: {initial_message[:50]}")
        
        # Generate project name using same logic as streaming API
        base_project_name = generate_project_name(initial_message)
        timestamp = datetime.now().strftime("%H%M%S")
        project_name = f"{base_project_name}-{timestamp}"
        
        # Initialize model system - this calls create_project_via_cloud_storage
        api_key = get_api_key()
        model_system = BoilerplatePersistentGroq(api_key, project_name)
        project_id = model_system.project_id
        
        print(f"✅ Project created via cloud storage: {project_id}")
        
        # Get frontend files for webcontainer mounting
        cloud_storage = model_system.cloud_storage
        all_files = cloud_storage.list_files(project_id)
        
        # Filter frontend files for WebContainer (only exclude cache/temp files)
        frontend_files = []
        exclude_patterns = [
            # Project metadata (not needed in WebContainer)
            'conversation_history.json',
            'project_metadata.json', 
            'read_files_tracking.json',
            
            # Backend files (frontend-only mount)
            'backend/',
            
            # Cache and temporary files
            'node_modules/',
            '.git/',
            '.vscode/',
            '.idea/',
            'dist/',
            'build/',
            '.next/',
            'coverage/',
            
            # Lock files (WebContainer will regenerate)
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
        ]
        
        for file_path in all_files:
            if not file_path or file_path.startswith('backend/'):
                continue
            should_exclude = any(pattern in file_path for pattern in exclude_patterns)
            if should_exclude:
                continue
            
            # Remove 'frontend/' prefix for WebContainer mounting at root level
            if file_path.startswith('frontend/'):
                clean_path = file_path[9:]  # Remove 'frontend/' prefix
                if clean_path:  # Only add if there's content after removing prefix
                    frontend_files.append(clean_path)
            else:
                frontend_files.append(file_path)
        
        # Convert to WebContainer format
        webcontainer_files = convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)
        
        print(f"✅ Project ready for WebContainer: {project_id} with {len(frontend_files)} frontend files")
        
        return {
            "project_id": project_id,
            "project_name": project_name,
            "files": webcontainer_files,
            "message": f"Project created and ready: {project_name}"
        }
        
    except Exception as e:
        print(f"❌ Error creating project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@app.get("/projects/list")
async def list_projects():
    """Get list of all projects for webcontainer selector"""
    try:
        from cloud_storage import AzureBlobStorage
        cloud_storage = AzureBlobStorage()
        
        # Get all project folders from Azure
        all_files = []
        blob_list = cloud_storage.container_client.list_blobs()
        
        projects = {}
        for blob in blob_list:
            # Extract project ID from blob path (format: project_id/file_path)
            parts = blob.name.split('/', 1)
            if len(parts) >= 1:
                project_id = parts[0]
                if project_id and project_id not in projects:
                    # Get project metadata
                    projects[project_id] = {
                        "id": project_id,
                        "name": project_id.replace('-', ' ').title(),
                        "description": f"Project created from {project_id}",
                        "created_at": blob.last_modified.isoformat() if blob.last_modified else None,
                        "file_count": 0
                    }
                projects[project_id]["file_count"] += 1
        
        # Convert to list and sort by creation date
        project_list = list(projects.values())
        project_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"projects": project_list}
        
    except Exception as e:
        print(f"❌ Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

@app.get("/projects/{project_id}/frontend-files")
async def get_frontend_files(project_id: str):
    """Get frontend files from cloud project for WebContainer mounting"""
    try:
        from cloud_storage import AzureBlobStorage
        cloud_storage = AzureBlobStorage()
        
        # Get all files for this project
        all_files = cloud_storage.list_files(project_id)
        
        # Filter frontend files for WebContainer (only exclude cache/temp files)
        frontend_files = []
        
        # Exclude patterns that WebContainer doesn't need
        exclude_patterns = [
            # Project metadata (not needed in WebContainer)
            'conversation_history.json',
            'project_metadata.json', 
            'read_files_tracking.json',
            
            # Backend files (frontend-only mount)
            'backend/',
            
            # Cache and temporary files
            'node_modules/',
            '.git/',
            '.vscode/',
            '.idea/',
            'dist/',
            'build/',
            '.next/',
            'coverage/',
            
            # Lock files (WebContainer will regenerate)
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
        ]
        
        for file_path in all_files:
            if not file_path or file_path.startswith('backend/'):
                continue
                
            # Skip excluded patterns
            should_exclude = any(pattern in file_path for pattern in exclude_patterns)
            if should_exclude:
                continue
            
            # Remove 'frontend/' prefix for WebContainer mounting at root level
            if file_path.startswith('frontend/'):
                clean_path = file_path[9:]  # Remove 'frontend/' prefix
                if clean_path:  # Only add if there's content after removing prefix
                    frontend_files.append(clean_path)
            else:
                frontend_files.append(file_path)
        
        print(f"📁 Found {len(frontend_files)} frontend files for project {project_id}")
        
        # Convert to WebContainer mount format
        webcontainer_files = convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)
        
        return {"files": webcontainer_files, "project_id": project_id}
        
    except Exception as e:
        print(f"❌ Error getting frontend files for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frontend files: {str(e)}")

def convert_to_webcontainer_format(project_id: str, files_list: list, cloud_storage) -> dict:
    """Convert cloud files to WebContainer mount format"""
    try:
        webcontainer_files = {}
        
        for file_path in files_list:
            # For downloading, we need the original path with frontend/ prefix
            original_path = f"frontend/{file_path}" if not file_path.startswith('frontend/') else file_path
            
            # Download file content from cloud using original path
            content = cloud_storage.download_file(project_id, original_path)
            if content is None:
                print(f"⚠️ Could not download content for {original_path}")
                continue
            
            # Build nested structure for WebContainer
            path_parts = file_path.split('/')
            current_level = webcontainer_files
            
            # Navigate/create directory structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # This is the file
                    current_level[part] = {
                        'file': {
                            'contents': content
                        }
                    }
                else:
                    # This is a directory
                    if part not in current_level:
                        current_level[part] = {'directory': {}}
                    current_level = current_level[part]['directory']
        
        print(f"✅ Converted {len(files_list)} files to WebContainer format")
        return webcontainer_files
        
    except Exception as e:
        print(f"❌ Error converting files to WebContainer format: {e}")
        return {}

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Model Conversation API Server with WebContainer Integration")
    print("=" * 60)
    print("Endpoints:")
    print("  POST /chat/stream - Stream chat with model")
    print("  GET /conversations - List all conversations")
    print("  GET /conversations/{id}/info - Get conversation details")
    print("  DELETE /conversations/{id} - Delete conversation")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8084)