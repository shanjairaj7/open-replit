from typing import Dict, AsyncGenerator, Optional
import json
import re
from app.services.code_validator import CodeValidator
import logging

logger = logging.getLogger(__name__)

class ValidationMiddleware:
    """Middleware to validate code in AI responses before streaming"""
    
    def __init__(self):
        self.current_files: Dict[str, str] = {}
        self.current_artifact_id: Optional[str] = None
        self.buffer = ""
        
    async def process_stream_with_validation(
        self, 
        stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """Process stream and validate files before completion"""
        
        async for chunk in stream:
            # Extract the actual content from the chunk format (0:"content")
            content_match = re.match(r'^0:"(.*)"\n?$', chunk)
            if content_match:
                # Unescape the content
                content = content_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                self.buffer += content
                
                # Extract any completed file actions
                self._extract_file_actions()
            
            # Pass through the chunk unchanged
            yield chunk
        
        # After stream completes, validate all files
        if self.current_files:
            validation_errors = CodeValidator.validate_all_files(self.current_files)
            
            if validation_errors:
                # Generate validation report as additional AI message
                report = CodeValidator.format_validation_report(validation_errors)
                logger.info(f"Validation errors found: {report}")
                
                # Stream validation report as text chunks
                yield f'0:"\\n\\n=== CODE VALIDATION REPORT ===\\n"\n'
                
                # Split report into lines and stream each
                for line in report.split('\n'):
                    if line:
                        escaped_line = json.dumps(line)[1:-1]
                        yield f'0:"{escaped_line}\\n"\n'
                
                # Add a shell action to run actual build test
                if self.current_artifact_id:
                    yield f'0:"\\n<boltAction type=\\"shell\\">npm run build 2>&1 || echo \\"Build contains errors - see above\\"</boltAction>\\n"\n'
                    yield f'0:"</boltArtifact>"\n'
    
    def _extract_file_actions(self):
        """Extract completed file actions from buffer"""
        # Look for artifact start
        artifact_match = re.search(r'<boltArtifact\s+id="([^"]+)"', self.buffer)
        if artifact_match:
            self.current_artifact_id = artifact_match.group(1)
        
        # Look for completed file actions with proper handling of multiline content
        file_action_pattern = r'<boltAction\s+type="file"\s+filePath="([^"]+)">(.*?)</boltAction>'
        
        for match in re.finditer(file_action_pattern, self.buffer, re.DOTALL):
            file_path = match.group(1)
            content = match.group(2)
            
            # Content is already unescaped from the stream processing
            # Just store it
            self.current_files[file_path] = content.strip()
            
            logger.debug(f"Extracted file: {file_path} ({len(content)} chars)")
            
            # Remove processed action from buffer to prevent re-processing
            self.buffer = self.buffer.replace(match.group(0), '', 1)
    
    def reset(self):
        """Reset state for new conversation"""
        self.current_files = {}
        self.current_artifact_id = None
        self.buffer = ""