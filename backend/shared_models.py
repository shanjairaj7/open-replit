"""
Shared models and classes to avoid circular imports
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Generator, Dict, Optional, List, Set, Any
from pydantic import BaseModel, Field


# Pydantic model for BoilerplatePersistentGroq state
class GroqAgentState(BaseModel):
    """Pydantic model representing the complete state of BoilerplatePersistentGroq"""
    
    # Core configuration
    api_key: str = Field(..., description="Groq API key")
    model: str = Field(default="moonshotai/kimi-k2-instruct", description="AI model to use")
    api_base_url: str = Field(default="http://206.189.229.208:8000/api", description="VPS API base URL")
    update_mode: bool = Field(default=False, description="Whether in update mode or creation mode")
    
    # Project identification
    project_id: Optional[str] = Field(None, description="Unique project identifier")
    project_name: Optional[str] = Field(None, description="Human-readable project name")
    
    # File management
    project_files: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="All project files with metadata")
    read_files_tracker: Set[str] = Field(default_factory=set, description="Files read in current session")
    read_files_persistent: Set[str] = Field(default_factory=set, description="Files read across all sessions")
    
    # Conversation and context
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Full conversation history")
    system_prompt: str = Field(default="", description="System prompt for the AI")
    project_summary: str = Field(default="No project summary available.", description="Comprehensive project summary")
    
    # Token tracking
    token_usage: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
            "sessions": []
        },
        description="Cumulative token usage across all sessions"
    )
    session_token_usage: Dict[str, Any] = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
            "started_at": datetime.now().isoformat()
        },
        description="Current session token usage"
    )
    
    # Preview URLs (set after preview starts)
    preview_url: Optional[str] = Field(None, description="Frontend preview URL")
    backend_url: Optional[str] = Field(None, description="Backend API URL")
    
    # Internal state
    last_plan_response: Optional[str] = Field(None, description="Last planning response for debugging")
    
    class Config:
        arbitrary_types_allowed = True  # Allow Path objects


class StreamingXMLParser:
    """Parse XML action tags from streaming responses"""
    
    def __init__(self):
        self.buffer = ""
        
    def _parse_attributes(self, attr_string: str) -> Dict[str, str]:
        """Parse XML attributes from string"""
        attrs = {}
        # Simple regex to parse key="value" pairs
        for match in re.finditer(r'(\w+)="([^"]*)"', attr_string):
            attrs[match.group(1)] = match.group(2)
        return attrs
        
    def process_chunk(self, chunk: str) -> Generator[Dict, None, None]:
        """Process a chunk of streaming data and yield complete actions"""
        self.buffer += chunk
        
        # Look for complete action tags
        while True:
            # Look for self-closing action tags
            self_closing_pattern = r'<action\s+([^>]*?)/>'
            self_closing_match = re.search(self_closing_pattern, self.buffer)
            
            if self_closing_match:
                # Parse attributes
                attrs = self._parse_attributes(self_closing_match.group(1))
                
                yield {
                    'type': attrs.get('type', ''),
                    'path': attrs.get('path', attrs.get('filePath', '')),
                    'command': attrs.get('command', ''),
                    'cwd': attrs.get('cwd', ''),
                    'new_name': attrs.get('new_name', ''),
                    'id': attrs.get('id', ''),
                    'priority': attrs.get('priority', ''),
                    'integration': attrs.get('integration', ''),
                    'status': attrs.get('status', ''),
                    'integration_tested': attrs.get('integration_tested', ''),
                    'content': '',
                    'raw_attrs': attrs
                }
                
                # Remove processed part from buffer
                self.buffer = self.buffer[self_closing_match.end():]
                continue
            
            # Look for start of action tag with content
            start_pattern = r'<action\s+([^>]*?)>'
            start_match = re.search(start_pattern, self.buffer)
            
            if not start_match:
                break
                
            # Look for corresponding end tag
            end_pattern = r'</action>'
            end_match = re.search(end_pattern, self.buffer[start_match.end():])
            
            if not end_match:
                break  # Wait for more content
                
            # Extract content between tags
            content_start = start_match.end()
            content_end = start_match.end() + end_match.start()
            content = self.buffer[content_start:content_end]
            
            # Strip unnecessary wrapper tags that models sometimes add
            content = self._strip_content_wrapper_tags(content)
            
            # Parse attributes
            attrs = self._parse_attributes(start_match.group(1))
            
            yield {
                'type': attrs.get('type', ''),
                'path': attrs.get('path', attrs.get('filePath', '')),
                'command': attrs.get('command', ''),
                'cwd': attrs.get('cwd', ''),
                'new_name': attrs.get('new_name', ''),
                'id': attrs.get('id', ''),
                'priority': attrs.get('priority', ''),
                'integration': attrs.get('integration', ''),
                'status': attrs.get('status', ''),
                'integration_tested': attrs.get('integration_tested', ''),
                'content': content,
                'raw_attrs': attrs
            }
            
            # Remove processed part from buffer
            self.buffer = self.buffer[start_match.end() + end_match.end():]
    
    def _strip_content_wrapper_tags(self, content: str) -> str:
        """Strip unnecessary wrapper tags that models sometimes add around file content"""
        content = content.strip()
        
        # Common wrapper tags that models use incorrectly
        wrapper_tags = [
            'content',
            'code', 
            'file-content',
            'file_content',
            'body',
            'text'
        ]
        
        for tag in wrapper_tags:
            # Check for opening and closing tags wrapping the entire content
            pattern = rf'^<{tag}[^>]*>\s*(.*?)\s*</{tag}>$'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                # Only strip if the tags wrap the ENTIRE content
                inner_content = match.group(1)
                # Make sure we're not removing content that should be part of the file
                # If the inner content looks like real file content (not just wrapped), extract it
                if inner_content.strip():
                    content = inner_content
                    break
        
        return content