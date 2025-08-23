"""
Conversation History to Streaming Format Converter

This module converts raw conversation history from Azure Blob Storage 
into the EXACT streaming format that the frontend expects, based on 
the actual live streaming API format and frontend stream handler.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional

class ConversationHistoryConverter:
    """Converts conversation history to frontend-compatible streaming format"""
    
    def __init__(self):
        self.action_counter = 1
        
    def convert_to_streaming_format(self, conversation_history: List[Dict], project_id: str) -> Dict[str, Any]:
        """
        Convert raw conversation history to exact streaming format
        
        Args:
            conversation_history: List of message objects from Azure storage
            project_id: Project identifier
            
        Returns:
            Dict containing streaming chunks in exact frontend format
        """
        streaming_chunks = []
        fake_conversation_id = f"conv_history_{project_id}"
        
        for i, message in enumerate(conversation_history):
            role = message.get("role")
            content = message.get("content", "")
            
            if role == "system":
                # Skip system messages - frontend doesn't handle them in streaming
                continue
            
            elif role == "user":
                # User messages as text chunks - EXACT format from live stream
                chunk = self._create_text_chunk(content, fake_conversation_id)
                streaming_chunks.append(chunk)
            
            elif role == "assistant":
                # Process assistant messages - may contain actions
                assistant_chunks = self._process_assistant_message(
                    content, fake_conversation_id, i
                )
                streaming_chunks.extend(assistant_chunks)
        
        return {
            "project_id": project_id,
            "conversation_id": fake_conversation_id,
            "message_count": len(conversation_history),
            "streaming_chunks_count": len(streaming_chunks),
            "streaming_chunks": streaming_chunks,
            "source": "azure_blob_storage",
            "format": "exact_frontend_match"
        }
    
    def _create_text_chunk(self, content: str, conversation_id: str) -> Dict[str, Any]:
        """Create a text chunk in exact live stream format"""
        return {
            "type": "text",
            "data": {
                "content": content
            },
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "action_id": None
        }
    
    def _create_assistant_message_chunk(self, content: str, conversation_id: str) -> Dict[str, Any]:
        """Create an assistant message chunk in exact live stream format"""
        return {
            "type": "assistant_message",
            "data": {
                "content": content
            },
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "action_id": None
        }
    
    def _process_assistant_message(self, content: str, conversation_id: str, message_index: int) -> List[Dict[str, Any]]:
        """
        Process assistant message content, extracting actions and text
        
        Returns list of streaming chunks (assistant_message, action_start, action_result)
        """
        chunks = []
        
        if "<action" in content and "</action>" in content:
            # Has actions - split content and process
            chunks.extend(self._split_content_with_actions(content, conversation_id, message_index))
        else:
            # Plain assistant message without actions
            chunk = self._create_assistant_message_chunk(content, conversation_id)
            chunks.append(chunk)
        
        return chunks
    
    def _split_content_with_actions(self, content: str, conversation_id: str, message_index: int) -> List[Dict[str, Any]]:
        """Split content into text and action parts, create appropriate chunks"""
        chunks = []
        
        # Split content around action tags
        parts = re.split(r'(<action[^>]*>.*?</action>)', content, flags=re.DOTALL)
        
        for j, part in enumerate(parts):
            if not part.strip():
                continue
                
            if part.startswith('<action'):
                # Process action
                action_chunks = self._process_action(part, conversation_id, message_index, j)
                chunks.extend(action_chunks)
            else:
                # Regular text content
                if part.strip():
                    chunk = self._create_assistant_message_chunk(part.strip(), conversation_id)
                    chunks.append(chunk)
        
        return chunks
    
    def _process_action(self, action_xml: str, conversation_id: str, message_index: int, part_index: int) -> List[Dict[str, Any]]:
        """
        Process a single action XML tag into action_start and action_result chunks
        
        Based on actual live streaming format from calculator test
        """
        # Extract action type and content
        action_match = re.search(r'<action[^>]*type="([^"]*)"[^>]*>(.*?)</action>', action_xml, re.DOTALL)
        if not action_match:
            return []
        
        action_type = action_match.group(1)
        action_content = action_match.group(2).strip()
        action_id = f"action_{self.action_counter}"
        self.action_counter += 1
        
        # Parse action details based on type - EXACT format from live stream
        action_details = self._parse_action_details(action_xml, action_type, action_content)
        
        timestamp = datetime.now().isoformat()
        
        # Create action_start chunk - EXACT format from live stream
        action_start = {
            "type": "action_start",
            "data": {
                "action_type": action_type,
                "action_details": action_details,
                "content": f"Creating {action_type}: {action_content[:50]}..." if action_content else f"Executing {action_type}..."
            },
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "action_id": action_id
        }
        
        # Create action_result chunk - EXACT format from live stream
        action_result = {
            "type": "action_result",
            "data": {
                "result": self._generate_action_result_message(action_type, action_details),
                "status": "success",
                "action_details": {
                    "action_type": action_type,
                    **self._get_simple_action_details(action_type, action_details),
                    "status": "success",
                    "result": "completed"
                }
            },
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "action_id": action_id
        }
        
        return [action_start, action_result]
    
    def _parse_action_details(self, action_xml: str, action_type: str, action_content: str) -> Dict[str, Any]:
        """
        Parse action details from XML attributes - EXACT format from live stream
        
        This matches the complex nested structure seen in actual streaming
        """
        # Extract all attributes
        attrs = {}
        attr_regex = r'(\w+)="([^"]*)"'
        for match in re.finditer(attr_regex, action_xml):
            key, value = match.groups()
            if key != "type":  # Skip type as it's handled separately
                attrs[key] = value
        
        # Build action_details structure based on action type
        if action_type == "todo_create":
            return {
                "action_type": "todo_create",
                "todo_id": attrs.get("id", f"todo_{self.action_counter}"),
                "description": action_content,
                "priority": attrs.get("priority", "medium"),
                "action_details": {
                    "type": "todo_create",
                    "path": "",
                    "command": "",
                    "cwd": "",
                    "new_name": "",
                    "id": attrs.get("id", f"todo_{self.action_counter}"),
                    "priority": attrs.get("priority", "medium"),
                    "integration": attrs.get("integration", "false"),
                    "status": "",
                    "integration_tested": "",
                    "query": "",
                    "content": action_content,
                    "raw_attrs": {
                        "type": "todo_create",
                        "id": attrs.get("id", f"todo_{self.action_counter}"),
                        "priority": attrs.get("priority", "medium"),
                        "integration": attrs.get("integration", "false")
                    }
                }
            }
        
        elif action_type == "file":
            file_path = attrs.get("filePath", "unknown")
            return {
                "action_type": "create_file",
                "file_path": file_path,
                "content": action_content,
                "action_details": {
                    "type": "create_file",
                    "path": file_path,
                    "command": "",
                    "cwd": "",
                    "new_name": "",
                    "id": "",
                    "priority": "",
                    "integration": "",
                    "status": "",
                    "integration_tested": "",
                    "query": "",
                    "content": action_content,
                    "raw_attrs": {
                        "type": "file",
                        "filePath": file_path
                    }
                }
            }
        
        elif action_type == "update_file":
            file_path = attrs.get("path", "unknown")
            return {
                "action_type": "update_file",
                "file_path": file_path,
                "content": action_content,
                "action_details": {
                    "type": "update_file",
                    "path": file_path,
                    "command": "",
                    "cwd": "",
                    "new_name": "",
                    "id": "",
                    "priority": "",
                    "integration": "",
                    "status": "",
                    "integration_tested": "",
                    "query": "",
                    "content": action_content,
                    "raw_attrs": {
                        "type": "update_file",
                        "path": file_path
                    }
                }
            }
        
        elif action_type == "run_command":
            command = attrs.get("command", action_content)
            cwd = attrs.get("cwd", "unknown")
            return {
                "action_type": "run_command",
                "command": command,
                "cwd": cwd,
                "action_details": {
                    "type": "run_command",
                    "path": "",
                    "command": command,
                    "cwd": cwd,
                    "new_name": "",
                    "id": "",
                    "priority": "",
                    "integration": "",
                    "status": "",
                    "integration_tested": "",
                    "query": "",
                    "content": action_content,
                    "raw_attrs": {
                        "type": "run_command",
                        "command": command,
                        "cwd": cwd
                    }
                }
            }
        
        else:
            # Generic action details
            return {
                "action_type": action_type,
                "content": action_content,
                "action_details": {
                    "type": action_type,
                    "path": attrs.get("path", ""),
                    "command": attrs.get("command", ""),
                    "cwd": attrs.get("cwd", ""),
                    "new_name": "",
                    "id": attrs.get("id", ""),
                    "priority": attrs.get("priority", ""),
                    "integration": attrs.get("integration", ""),
                    "status": "",
                    "integration_tested": "",
                    "query": "",
                    "content": action_content,
                    "raw_attrs": attrs
                }
            }
    
    def _get_simple_action_details(self, action_type: str, action_details: Dict[str, Any]) -> Dict[str, Any]:
        """Get simplified action details for action_result chunk"""
        if action_type == "todo_create":
            return {
                "todo_id": action_details.get("todo_id"),
            }
        elif action_type in ["file", "create_file"]:
            return {
                "file_path": action_details.get("file_path")
            }
        elif action_type == "update_file":
            return {
                "file_path": action_details.get("file_path")
            }
        elif action_type == "run_command":
            return {
                "command": action_details.get("command"),
                "cwd": action_details.get("cwd")
            }
        else:
            return {}
    
    def _generate_action_result_message(self, action_type: str, action_details: Dict[str, Any]) -> str:
        """Generate human-readable result message based on action type"""
        if action_type == "todo_create":
            return f"Todo action {action_type} completed"
        elif action_type == "file":
            file_path = action_details.get("file_path", "file")
            file_name = file_path.split("/")[-1] if "/" in file_path else file_path
            return f"Created file: {file_name}"
        elif action_type == "update_file":
            file_path = action_details.get("file_path", "file")
            file_name = file_path.split("/")[-1] if "/" in file_path else file_path
            return f"Updated file: {file_name}"
        elif action_type == "run_command":
            command = action_details.get("command", "command")
            return f"Executed command: {command}"
        else:
            return f"{action_type.replace('_', ' ').title()} completed successfully"