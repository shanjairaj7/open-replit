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
        """Parse XML attributes from string with proper quote handling"""
        attrs = {}
        
        # Use a more robust regex-based approach that handles complex nested quotes
        # This pattern matches: attribute_name="value" where value can contain various quote patterns
        
        # First, let's handle the simple cases with a standard regex
        simple_pattern = r'(\w+)="([^"]*)"(?=\s|$|/>|>)'
        simple_matches = re.findall(simple_pattern, attr_string)
        
        # Track which parts we've processed
        processed_parts = set()
        
        for attr_name, attr_value in simple_matches:
            # Only use this if the value doesn't look like it was truncated
            # (i.e., doesn't contain unmatched quotes or incomplete shell commands)
            if not self._looks_like_truncated_command(attr_value):
                attrs[attr_name] = attr_value
                # Mark this part as processed
                pattern = f'{attr_name}="{re.escape(attr_value)}"'
                match = re.search(pattern, attr_string)
                if match:
                    for i in range(match.start(), match.end()):
                        if i < len(attr_string):
                            processed_parts.add(i)
            else:
                # This looks truncated, don't mark it as processed so complex parsing can handle it
                print(f"Detected truncated attribute '{attr_name}': '{attr_value[:50]}...', will use complex parsing")
        
        # For more complex cases, fall back to manual parsing
        # Focus on attributes that weren't successfully parsed by the simple regex
        remaining_attr_string = ""
        for i, char in enumerate(attr_string):
            if i not in processed_parts:
                remaining_attr_string += char
            else:
                remaining_attr_string += " "  # Preserve spacing
        
        # Clean up the remaining string
        remaining_attr_string = re.sub(r'\s+', ' ', remaining_attr_string).strip()
        
        if remaining_attr_string and '=' in remaining_attr_string:
            # Parse remaining attributes manually
            self._parse_complex_attributes(remaining_attr_string, attrs)
        
        return attrs
    
    def _looks_like_truncated_command(self, value: str) -> bool:
        """Check if a value looks like it was truncated during parsing"""
        # Check for patterns that suggest truncation
        truncation_indicators = [
            # Shell commands that end abruptly
            lambda v: '|' in v and any(v.endswith(f'| {cmd}') for cmd in ['grep', 'awk', 'sed', 'sort', 'cut']),
            # Unmatched quotes (more opening than closing or vice versa)
            lambda v: v.count("'") % 2 != 0,
            # Commands that end with quote followed by space (likely truncated)
            lambda v: re.search(r'[\'"] $', v),
            # grep -o patterns that look incomplete
            lambda v: 'grep -o' in v and ("'" in v or '"' in v) and not v.strip().endswith(("'", '"')),
            # Specific pattern: grep -o followed by unmatched quotes (like our failing case)
            lambda v: 'grep -o' in v and "'" in v and v.count("'") == 1,
            # Commands that have pipes but don't end with complete command words
            lambda v: '|' in v and not re.search(r'\w+\s*$', v.strip()),
        ]
        
        return any(indicator(value) for indicator in truncation_indicators)
    
    def _parse_complex_attributes(self, attr_string: str, attrs: dict):
        """Parse complex attributes that the simple regex couldn't handle"""
        # For command attributes specifically, be more liberal about quote handling
        
        # Look for command="..." patterns specifically
        command_pattern = r'command="([^"]*(?:"[^"]*"[^"]*)*)"'
        command_match = re.search(command_pattern, attr_string)
        
        if command_match:
            command_value = command_match.group(1)
            # If this looks like a complete shell command, use it
            if self._looks_like_complete_command(command_value):
                attrs['command'] = command_value
                return
        
        # Fall back to a more permissive approach for the command attribute
        # Look for command=" and then find the end by looking for " followed by next attribute or end
        if 'command="' in attr_string:
            start_idx = attr_string.find('command="') + len('command="')
            
            # Find the closing quote by looking for quote followed by (space + word + =) or end
            # Be more careful about quotes that might be inside shell commands
            end_idx = len(attr_string)
            for i in range(start_idx, len(attr_string)):
                if attr_string[i] == '"':
                    # Check what follows this quote
                    remaining = attr_string[i+1:].strip()
                    
                    # This quote ends the attribute if followed by:
                    # 1. Nothing (end of string)
                    # 2. XML end markers (/, >)  
                    # 3. Another XML attribute (word + =)
                    
                    # But NOT if it's followed by something that looks like:
                    # - Part of a regex pattern
                    # - Continuation of a shell command
                    
                    is_end_quote = False
                    
                    if not remaining:
                        # End of string
                        is_end_quote = True
                    elif remaining.startswith('/>') or remaining.startswith('>'):
                        # XML tag end
                        is_end_quote = True
                    elif re.match(r'\w+\s*=', remaining):
                        # Next attribute
                        is_end_quote = True
                    elif remaining.startswith('/'):
                        # Could be XML tag end or part of regex - check context
                        # If we're in a shell command context, this might be part of a regex
                        command_so_far = attr_string[start_idx:i]
                        if ('grep' in command_so_far and 
                            any(pattern in command_so_far for pattern in ['-o', '-E', '-P'])):
                            # This looks like a grep regex pattern, don't end here
                            is_end_quote = False
                        else:
                            is_end_quote = True
                    
                    if is_end_quote:
                        end_idx = i
                        break
            
            if end_idx > start_idx:
                command_value = attr_string[start_idx:end_idx]
                attrs['command'] = command_value
    
    def _looks_like_complete_command(self, value: str) -> bool:
        """Check if a command value looks complete"""
        # A complete command should:
        # 1. Not end abruptly with operators
        # 2. Have balanced quotes (for shell commands)
        # 3. End with reasonable command completion
        
        if not value.strip():
            return False
            
        # Don't end with pipe or incomplete operators
        if re.search(r'[|&;]$', value.strip()):
            return False
            
        # For grep commands with -o, should end with the pattern and pipe continuation
        if 'grep -o' in value:
            # Should have a pattern and possibly continue with pipe
            if re.search(r"grep -o '[^']+'\s*(\||$)", value) or re.search(r'grep -o "[^"]+"\s*(\||$)', value):
                return True
                
        return True
        
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
                    'query': attrs.get('query', ''),
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
                'query': attrs.get('query', ''),
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