import re
import json
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class BoltMessageParser:
    """
    Stateful parser for extracting <boltArtifact> and <boltAction> tags from AI responses
    Matches the functionality of the frontend StreamingMessageParser exactly
    """
    
    def __init__(self):
        self.input = ""
        self.position = 0
        self.inside_artifact = False
        self.inside_action = False
        self.action_id = 0
        self.current_artifact = None
        self.current_action = None
        self.artifact_opened = False
        self.action_opened = False
        
    def parse_chunk(self, chunk: str) -> List[str]:
        """
        Parse a streaming chunk incrementally and return AI SDK formatted events
        Only processes new content beyond the last position
        
        CRITICAL: Handle streaming tags that are split across chunks
        """
        self.input += chunk
        events = []
        
        # Process accumulated input from current position
        while self.position < len(self.input):
            if not self.inside_artifact:
                # Look for artifact opening
                artifact_match = self._find_at_position(r'<boltArtifact\s+([^>]*)>', self.position)
                if artifact_match:
                    attrs = self._parse_attributes(artifact_match.group(1))
                    self.current_artifact = {
                        "id": attrs.get("id", ""),
                        "title": attrs.get("title", "")
                    }
                    self.inside_artifact = True
                    self.artifact_opened = True
                    self.position = artifact_match.end()
                    
                    # Send artifact open event ONCE
                    events.append(f'8:{json.dumps([{
                        "type": "artifact",
                        "id": self.current_artifact["id"],
                        "title": self.current_artifact["title"],
                        "status": "open"
                    }])}\n')
                    continue
                else:
                    # No artifact found, advance position
                    break
                    
            elif not self.inside_action:
                # Look for action opening
                action_match = self._find_at_position(r'<boltAction\s+([^>]*)>', self.position)
                if action_match:
                    attrs = self._parse_attributes(action_match.group(1))
                    self.current_action = {
                        "type": attrs.get("type", ""),
                        "filePath": attrs.get("filePath", ""),
                        "content": ""
                    }
                    self.inside_action = True
                    self.action_opened = True
                    self.position = action_match.end()
                    
                    # Send action open event ONCE
                    events.append(f'8:{json.dumps([{
                        "type": "action", 
                        "actionId": str(self.action_id),
                        "actionType": self.current_action["type"],
                        "filePath": self.current_action["filePath"],
                        "content": "",
                        "status": "open"
                    }])}\n')
                    continue
                else:
                    # Look for artifact closing
                    artifact_close = self._find_at_position(r'</boltArtifact>', self.position)
                    if artifact_close:
                        self.inside_artifact = False
                        self.position = artifact_close.end()
                        continue
                    else:
                        break
                        
            else:
                # Inside action, look for closing tag or collect content
                action_close = self._find_at_position(r'</boltAction>', self.position)
                
                # Check if we might have a partial closing tag at the end of input
                remaining_input = self.input[self.position:]
                if not action_close and ('</bolt' in remaining_input[-20:] or '</boltA' in remaining_input[-20:]):
                    # Might have partial closing tag, wait for more input
                    logger.info(f"PARSER: Waiting for complete closing tag, partial found: {repr(remaining_input[-20:])}")
                    break
                
                if action_close:
                    # Found closing tag - complete the action
                    content_between = self.input[self.position:action_close.start()]
                    self.current_action["content"] += content_between
                    
                    # Clean file content
                    if self.current_action["type"] == "file":
                        self.current_action["content"] = self._clean_file_content(self.current_action["content"])
                    
                    # DEBUG: Log action completion
                    logger.info(f"PARSER: Completing action {self.action_id}, file: {self.current_action['filePath']}, content length: {len(self.current_action['content'])}")
                    
                    # Send action complete event ONCE
                    events.append(f'8:{json.dumps([{
                        "type": "action",
                        "actionId": str(self.action_id), 
                        "actionType": self.current_action["type"],
                        "filePath": self.current_action["filePath"],
                        "content": self.current_action["content"],
                        "status": "complete"
                    }])}\n')
                    
                    # Reset action state and increment ID
                    self.inside_action = False
                    self.action_id += 1
                    self.current_action = None
                    self.position = action_close.end()
                    
                    # DEBUG: Log state after completion
                    logger.info(f"PARSER: Action completed, next action_id will be: {self.action_id}, position: {self.position}")
                    
                    # CRITICAL FIX: Continue processing to find more actions
                    # Don't break here - there might be more actions in the same chunk
                    continue
                else:
                    # No closing tag yet, collect remaining content
                    new_content = self.input[self.position:]
                    if new_content:
                        self.current_action["content"] += new_content
                        # Send full streaming updates
                        if self.current_action["type"] == "file":
                            events.append(f'8:{json.dumps([{
                                "type": "action",
                                "actionId": str(self.action_id),
                                "actionType": self.current_action["type"], 
                                "filePath": self.current_action["filePath"],
                                "content": self.current_action["content"],
                                "status": "streaming"
                            }])}\n')
                    
                    self.position = len(self.input)
                    break
                    
        return events
        
    def _find_at_position(self, pattern: str, pos: int) -> Optional[re.Match]:
        """Find pattern starting at specific position"""
        match = re.search(pattern, self.input[pos:])
        if match:
            # Create a match object with positions adjusted to full input
            start = pos + match.start()
            end = pos + match.end()
            
            class AdjustedMatch:
                def __init__(self, original_match, start_pos, end_pos):
                    self._match = original_match
                    self._start = start_pos
                    self._end = end_pos
                    
                def start(self):
                    return self._start
                    
                def end(self):
                    return self._end
                    
                def group(self, *args):
                    return self._match.group(*args)
                    
            return AdjustedMatch(match, start, end)
        return None
        
    def _parse_attributes(self, attr_string: str) -> Dict[str, str]:
        """Parse XML attributes from string"""
        attrs = {}
        attr_pattern = r'(\w+)=(["\'])(.*?)\2'
        for match in re.finditer(attr_pattern, attr_string):
            key, quote, value = match.groups()
            attrs[key] = value
        return attrs
        
    def _clean_file_content(self, content: str) -> str:
        """Remove markdown code block syntax from file content"""
        lines = content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines).strip()