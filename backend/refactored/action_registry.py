"""
Action Registry System - Centralized action detection and dispatch
Eliminates duplication between base_test.py and index_fixed.py
"""

from typing import Dict, Callable, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class ActionConfig:
    """Configuration for an action type"""
    handler_method: str  # Method name on self object (e.g., '_handle_read_file_interrupt')
    requires_interrupt: bool  # Whether this action should interrupt streaming
    continue_message_template: str  # Template for continuation message
    error_message_template: Optional[str] = None  # Template for error message
    requires_file_read_check: bool = False  # Whether to check if file was read first
    process_inline: bool = False  # Whether to process immediately without interrupt

class ActionRegistry:
    """Central registry for all action types and their handling configuration"""
    
    def __init__(self):
        self.actions = self._initialize_actions()
        self.interrupt_actions = {k: v for k, v in self.actions.items() if v.requires_interrupt}
        self.inline_actions = {k: v for k, v in self.actions.items() if v.process_inline}
    
    def _initialize_actions(self) -> Dict[str, ActionConfig]:
        """Initialize all action configurations"""
        return {
            'read_file': ActionConfig(
                handler_method='_handle_read_file_interrupt',
                requires_interrupt=True,
                continue_message_template="File content for {path}:\n\n```\n{result}\n```\n\nPlease continue with your response based on this file content.",
                error_message_template="❌ Error: Cannot update file '{path}' because it doesn't exist.\n\n✅ SOLUTION: Use <action type=\"file\" filePath=\"{path}\">YOUR_FILE_CONTENT</action> to create the file first.\n\nDo NOT use update_file for non-existent files. Use the file action to create it.\n\nPlease continue with your response."
            ),
            
            'run_command': ActionConfig(
                handler_method='_handle_run_command_interrupt',
                requires_interrupt=True,
                continue_message_template="""Command output for `{command}` in {cwd}:
{result}

**Instructions:**
- These are the logs from the terminal command execution
- If there are any errors, warnings, or issues in the output above, please fix them immediately
- Use `<action type="read_file" path="..."/>` to examine files that have errors
- Use `<action type="update_file" path="...">` to fix any issues found
- Continue with your response and next steps after addressing any problems

Please continue with your next steps.."""
            ),
            
            'update_file': ActionConfig(
                handler_method='_handle_update_file_interrupt',
                requires_interrupt=True,
                continue_message_template="File '{path}' has been updated successfully. Please continue with your response.",
                requires_file_read_check=True
            ),
            
            'rename_file': ActionConfig(
                handler_method='_handle_rename_file_interrupt',
                requires_interrupt=True,
                continue_message_template="File '{path}' has been renamed to '{new_name}' successfully. Please continue with your response."
            ),
            
            'delete_file': ActionConfig(
                handler_method='_handle_delete_file_interrupt',
                requires_interrupt=True,
                continue_message_template="File '{path}' has been deleted successfully. Please continue with your response."
            ),
            
            'start_backend': ActionConfig(
                handler_method='_handle_start_backend_interrupt',
                requires_interrupt=True,
                continue_message_template="Backend service started successfully on port {backend_port}. API available at {api_url}. Please continue with your response.",
                error_message_template="❌ Backend failed to start. There are errors that need to be fixed before the backend can run. Please investigate and fix the backend errors, then try starting the backend again. Use check_errors or read relevant files to identify and resolve the issues."
            ),
            
            'start_frontend': ActionConfig(
                handler_method='_handle_start_frontend_interrupt',
                requires_interrupt=True,
                continue_message_template="Frontend service started successfully on port {frontend_port}. Available at {frontend_url}. Please continue with your response.",
                error_message_template="❌ Frontend failed to start. There may be errors that need to be fixed before the frontend can run. Please investigate and fix any frontend errors, then try starting the frontend again. Use check_errors or read relevant files to identify and resolve the issues."
            ),
            
            'restart_backend': ActionConfig(
                handler_method='_handle_restart_backend_interrupt',
                requires_interrupt=True,
                continue_message_template="Backend service restarted successfully on port {backend_port}. API available at {api_url}. Please continue with your response.",
                error_message_template="❌ Backend restart failed. There are likely errors that need to be fixed before the backend can run. Please investigate and fix the backend errors, then try restarting the backend again. Use check_errors or read relevant files to identify and resolve the issues."
            ),
            
            'restart_frontend': ActionConfig(
                handler_method='_handle_restart_frontend_interrupt',
                requires_interrupt=True,
                continue_message_template="Frontend service restarted successfully on port {frontend_port}. Available at {frontend_url}. Please continue with your response.",
                error_message_template="❌ Frontend restart failed. There may be errors that need to be fixed before the frontend can run. Please investigate and fix any frontend errors, then try restarting the frontend again. Use check_errors or read relevant files to identify and resolve the issues."
            ),
            
            'check_errors': ActionConfig(
                handler_method='_handle_check_errors_interrupt',
                requires_interrupt=True,
                continue_message_template=None  # Custom formatting in handler
            ),
            
            'create_file_realtime': ActionConfig(
                handler_method='_handle_create_file_realtime',
                requires_interrupt=True,
                continue_message_template=None  # Custom formatting in handler
            ),
            
            # Todo actions - processed inline
            'todo_create': ActionConfig(
                handler_method='_handle_todo_actions',
                requires_interrupt=False,
                process_inline=True,
                continue_message_template=None
            ),
            
            'todo_update': ActionConfig(
                handler_method='_handle_todo_actions',
                requires_interrupt=False,
                process_inline=True,
                continue_message_template=None
            ),
            
            'todo_complete': ActionConfig(
                handler_method='_handle_todo_actions',
                requires_interrupt=True,  # Needs continuation prompt after completion
                process_inline=True,  # But process inline first
                continue_message_template="Great! You've completed a todo. Here's the current todo status:\n\n{todo_status}\n\nPlease continue with the next highest priority task."
            ),
        }
    
    def should_interrupt(self, action_type: str) -> bool:
        """Check if an action type should interrupt streaming"""
        config = self.actions.get(action_type)
        return config.requires_interrupt if config else False
    
    def should_process_inline(self, action_type: str) -> bool:
        """Check if an action should be processed inline without interrupting"""
        config = self.actions.get(action_type)
        return config.process_inline if config else False
    
    def get_handler_method(self, action_type: str) -> Optional[str]:
        """Get the handler method name for an action type"""
        config = self.actions.get(action_type)
        return config.handler_method if config else None
    
    def get_continue_message(self, action_type: str, **kwargs) -> Optional[str]:
        """Get the formatted continuation message for an action"""
        config = self.actions.get(action_type)
        if config and config.continue_message_template:
            return config.continue_message_template.format(**kwargs)
        return None
    
    def get_error_message(self, action_type: str, **kwargs) -> Optional[str]:
        """Get the formatted error message for an action"""
        config = self.actions.get(action_type)
        if config and config.error_message_template:
            return config.error_message_template.format(**kwargs)
        return None
    
    def requires_file_read_check(self, action_type: str) -> bool:
        """Check if action requires verifying file was read first"""
        config = self.actions.get(action_type)
        return config.requires_file_read_check if config else False
    
    def process_action_detection(self, action: dict, self_obj: Any) -> Tuple[bool, Optional[dict]]:
        """
        Process detected action and determine if interrupt is needed
        Returns: (should_interrupt, interrupt_action)
        """
        action_type = action.get('type')
        
        # Handle inline processing
        if self.should_process_inline(action_type):
            handler_method = self.get_handler_method(action_type)
            if handler_method and hasattr(self_obj, handler_method):
                getattr(self_obj, handler_method)(action)
                
            # Check if we still need to interrupt after inline processing
            if action_type == 'todo_complete':
                action['already_processed'] = True
                return True, action
            return False, None
        
        # Handle interrupt actions
        if self.should_interrupt(action_type):
            # Special handling for update_file - check if file was read
            if self.requires_file_read_check(action_type):
                file_path = action.get('path') or action.get('filePath')
                if file_path:
                    if (file_path not in self_obj.read_files_tracker and 
                        file_path not in self_obj.read_files_persistent):
                        print(f"\n🚨 File '{file_path}' not read before update - need to read first!")
                        # Convert to read_file action
                        return True, {'type': 'read_file', 'path': file_path}
            
            return True, action
        
        return False, None

# Global registry instance
action_registry = ActionRegistry()