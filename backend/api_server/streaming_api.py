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
from base_test_azure_hybrid import BoilerplatePersistentGroq

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
                    chunk = create_stream_chunk("action_result", {
                        "result": content,
                        "status": action_data.get("status") if action_data else "completed",
                        "action_details": action_data or {}
                    }, self.conversation_id, f"action_{action_counter}")
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
                
                # Thread-safe queue put
                stream_queue.put(chunk)
            
            # Yield initial message
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
                            yield create_stream_chunk("text", {
                                "content": "✅ Conversation completed successfully",
                                "final_result": data
                            }, self.conversation_id)
                        elif command == "ERROR":
                            yield create_stream_chunk("error", {
                                "error": data,
                                "message": "An error occurred during model execution"
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
            stream_callback("error", f"Model execution failed: {str(e)}")
            raise Exception(f"Model execution failed: {str(e)}")

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
        
        # Determine if this is create or update mode
        is_update_mode = bool(request.conversation_id and request.project_id)
        conversation_id = request.conversation_id or generate_conversation_id()
        
        print(f"📡 Generated conversation_id: {conversation_id}")
        print(f"📡 Update mode: {is_update_mode}")
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

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Model Conversation API Server")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /chat/stream - Stream chat with model")
    print("  GET /conversations - List all conversations")
    print("  GET /conversations/{id}/info - Get conversation details")
    print("  DELETE /conversations/{id} - Delete conversation")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8084)