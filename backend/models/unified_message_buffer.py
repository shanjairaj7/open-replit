"""
Unified Message Buffer System for Index Fixed
Accumulates all user messages with XML tags before adding single consolidated message
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class MessageType(Enum):
    """Types of messages that can be accumulated"""
    ACTION_RESULT = "action_result"
    TODO_STATUS = "todo_status"
    ERROR_CONTEXT = "error_context"
    FILE_CONTENT = "file_content"
    COMMAND_OUTPUT = "command_output"
    PROJECT_ERRORS = "project_errors"
    CONTINUATION = "continuation"

@dataclass
class MessageFragment:
    """Individual message fragment with type and content"""
    message_type: MessageType
    content: str
    action_type: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class UnifiedMessageBuffer:
    """
    Buffer that collects all user messages during an iteration
    and consolidates them into a single XML-tagged message
    """
    
    def __init__(self):
        self.fragments: List[MessageFragment] = []
        self.assistant_content: str = ""
        
    def set_assistant_content(self, content: str):
        """Set the assistant's accumulated content"""
        self.assistant_content = content
        
    def add_action_result(self, action_type: str, result: str, file_path: Optional[str] = None):
        """Add action result (file update, command execution, etc.)"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.ACTION_RESULT,
            content=result,
            action_type=action_type,
            file_path=file_path
        ))
        
    def add_file_content(self, file_path: str, content: str):
        """Add file content that was read"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.FILE_CONTENT,
            content=content,
            file_path=file_path
        ))
        
    def add_command_output(self, command: str, cwd: str, output: str):
        """Add command execution output"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.COMMAND_OUTPUT,
            content=output,
            metadata={"command": command, "cwd": cwd}
        ))
        
    def add_todo_status(self, todo_status: str):
        """Add todo status information"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.TODO_STATUS,
            content=todo_status
        ))
        
    def add_error_context(self, error_type: str, error_message: str):
        """Add error context information"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.ERROR_CONTEXT,
            content=error_message,
            metadata={"error_type": error_type}
        ))
        
    def add_project_errors(self, errors: str):
        """Add project-wide error information"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.PROJECT_ERRORS,
            content=errors
        ))
        
    def add_continuation_prompt(self, prompt: str):
        """Add continuation instruction"""
        self.fragments.append(MessageFragment(
            message_type=MessageType.CONTINUATION,
            content=prompt
        ))
    
    def has_content(self) -> bool:
        """Check if buffer has any message fragments"""
        return len(self.fragments) > 0
    
    def build_unified_message(self) -> str:
        """Build single unified message with XML tags for different content types"""
        if not self.fragments:
            return ""
            
        unified_content = ""
        
        # Group fragments by type for better organization
        fragments_by_type = {}
        for fragment in self.fragments:
            msg_type = fragment.message_type
            if msg_type not in fragments_by_type:
                fragments_by_type[msg_type] = []
            fragments_by_type[msg_type].append(fragment)
        
        # Add action results first
        if MessageType.ACTION_RESULT in fragments_by_type:
            unified_content += "<action_results>\n"
            for fragment in fragments_by_type[MessageType.ACTION_RESULT]:
                action_tag = f"action_type=\"{fragment.action_type}\""
                file_tag = f" file_path=\"{fragment.file_path}\"" if fragment.file_path else ""
                unified_content += f"<result {action_tag}{file_tag}>\n"
                unified_content += fragment.content
                unified_content += "\n</result>\n"
            unified_content += "</action_results>\n\n"
        
        # Add file content
        if MessageType.FILE_CONTENT in fragments_by_type:
            unified_content += "<file_contents>\n"
            for fragment in fragments_by_type[MessageType.FILE_CONTENT]:
                unified_content += f"<file path=\"{fragment.file_path}\">\n"
                unified_content += f"```\n{fragment.content}\n```\n"
                unified_content += "</file>\n"
            unified_content += "</file_contents>\n\n"
        
        # Add command outputs
        if MessageType.COMMAND_OUTPUT in fragments_by_type:
            unified_content += "<command_outputs>\n"
            for fragment in fragments_by_type[MessageType.COMMAND_OUTPUT]:
                command = fragment.metadata.get("command", "unknown")
                cwd = fragment.metadata.get("cwd", "unknown")
                unified_content += f"<command_result command=\"{command}\" cwd=\"{cwd}\">\n"
                unified_content += fragment.content
                unified_content += "\n</command_result>\n"
            unified_content += "</command_outputs>\n\n"
        
        # Add error context
        if MessageType.ERROR_CONTEXT in fragments_by_type:
            unified_content += "<error_context>\n"
            for fragment in fragments_by_type[MessageType.ERROR_CONTEXT]:
                error_type = fragment.metadata.get("error_type", "general") if fragment.metadata else "general"
                unified_content += f"<error type=\"{error_type}\">\n"
                unified_content += fragment.content
                unified_content += "\n</error>\n"
            unified_content += "</error_context>\n\n"
        
        # Add project errors
        if MessageType.PROJECT_ERRORS in fragments_by_type:
            unified_content += "<project_errors>\n"
            for fragment in fragments_by_type[MessageType.PROJECT_ERRORS]:
                unified_content += fragment.content
            unified_content += "\n</project_errors>\n\n"
        
        # Add todo status
        if MessageType.TODO_STATUS in fragments_by_type:
            unified_content += "<todo_status>\n"
            for fragment in fragments_by_type[MessageType.TODO_STATUS]:
                unified_content += fragment.content
            unified_content += "\n</todo_status>\n\n"
        
        # Add continuation prompts at the end
        if MessageType.CONTINUATION in fragments_by_type:
            unified_content += "<instructions>\n"
            for fragment in fragments_by_type[MessageType.CONTINUATION]:
                unified_content += fragment.content + "\n"
            unified_content += "</instructions>\n\n"
        
        # Add final continuation prompt if no specific continuation was added
        if MessageType.CONTINUATION not in fragments_by_type and self.has_content():
            unified_content += "<instructions>\n"
            unified_content += "Please continue with your response based on the above information.\n"
            unified_content += "</instructions>\n"
        
        return unified_content.strip()
    
    def create_message_pair(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Create assistant and user message pair for conversation"""
        if not self.has_content():
            return None, None
            
        assistant_msg = {"role": "assistant", "content": self.assistant_content}
        user_msg = {"role": "user", "content": self.build_unified_message()}
        
        return assistant_msg, user_msg
    
    def clear(self):
        """Clear all accumulated messages"""
        self.fragments.clear()
        self.assistant_content = ""

# Helper functions for common message patterns
def create_file_read_message(file_path: str, content: str) -> str:
    """Create standardized file read message"""
    buffer = UnifiedMessageBuffer()
    buffer.add_file_content(file_path, content)
    buffer.add_continuation_prompt("Please continue with your response based on this file content.")
    return buffer.build_unified_message()

def create_command_result_message(command: str, cwd: str, output: str) -> str:
    """Create standardized command result message"""
    buffer = UnifiedMessageBuffer()
    buffer.add_command_output(command, cwd, output)
    buffer.add_continuation_prompt(
        "- These are the logs from the terminal command execution\n"
        "- If there are any errors, warnings, or issues in the output above, please fix them immediately\n"
        "- Use `<action type=\"read_file\" path=\"...\"/>` to examine files that have errors\n"
        "- Use `<action type=\"update_file\" path=\"...\">` to fix any issues found\n"
        "- Continue with your response and next steps after addressing any problems"
    )
    return buffer.build_unified_message()

def create_action_result_message(action_type: str, result: str, file_path: str = None) -> str:
    """Create standardized action result message"""
    buffer = UnifiedMessageBuffer()
    buffer.add_action_result(action_type, result, file_path)
    buffer.add_continuation_prompt("Please continue with your response.")
    return buffer.build_unified_message()

def create_file_creation_message(file_path: str, has_errors: bool = False, 
                                python_errors: str = "", typescript_errors: str = "") -> str:
    """Create standardized file creation success message"""
    buffer = UnifiedMessageBuffer()
    
    if has_errors:
        error_messages = []
        if python_errors:
            error_messages.append(f"Python validation errors:\n{python_errors}")
        if typescript_errors:
            error_messages.append(f"TypeScript validation errors:\n{typescript_errors}")
        
        result = f"✅ File '{file_path}' created.\n\n**Static Analysis Results:**\n" + '\n\n'.join(error_messages)
        result += "\n\n**NEXT STEPS:**\n1. Fix these static errors first\n2. If this is a backend service, create a test file (e.g., `backend/test_api.py`) to verify it works\n3. Run the test file with `python backend/test_api.py`\n4. Fix any runtime errors\n5. Delete the test file when done"
        
        buffer.add_action_result("create_file", result, file_path)
        buffer.add_continuation_prompt("Continue with your implementation and testing.")
    else:
        result = f"✅ File '{file_path}' created successfully.\n\nIf this was a backend service:\n1. Create a test file (e.g., `backend/test_api.py`)\n2. Write Python code to test your endpoints\n3. Run it with `python backend/test_api.py`\n4. Verify it works, then delete the test file."
        
        buffer.add_action_result("create_file", result, file_path)
        buffer.add_continuation_prompt("Please continue with your response.")
    
    return buffer.build_unified_message()

# Example usage
if __name__ == "__main__":
    # Example of how to use the unified message buffer
    buffer = UnifiedMessageBuffer()
    buffer.set_assistant_content("I need to read the file and then update it...")
    
    # Add various message types
    buffer.add_file_content("src/app.py", "def hello():\n    print('world')")
    buffer.add_action_result("update_file", "File updated successfully", "src/app.py")
    buffer.add_todo_status("📋 todos/\n├── ✅ completed/ (1 items)\n└── ⏳ pending/ (2 items)")
    buffer.add_continuation_prompt("Please continue implementing the next feature.")
    
    # Build unified message
    unified = buffer.build_unified_message()
    print("Unified Message:")
    print("=" * 50)
    print(unified)
    print("=" * 50)
    
    # Create message pair
    assistant_msg, user_msg = buffer.create_message_pair()
    print(f"\nAssistant message: {len(assistant_msg['content'])} chars")
    print(f"User message: {len(user_msg['content'])} chars")