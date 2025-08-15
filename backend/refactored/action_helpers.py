"""
Action Processing Helpers - Make action handlers and interrupt handlers more efficient
WITHOUT changing core functionality
"""

def create_interrupt_action(action_type: str, action: dict, custom_message: str = None) -> tuple:
    """
    Efficiently create interrupt action with standardized logging
    Returns: (should_interrupt, interrupt_action)
    """
    # Custom messages for specific action types
    if custom_message:
        print(f"\n🚨 CODER: INTERRUPT - {custom_message}")
    else:
        print(f"\n🚨 CODER: INTERRUPT - Detected {action_type} action")
    
    print(f"⚡ CODER: Breaking from action loop for {action_type}")
    return True, action

def add_conversation_messages(
    accumulated_content: str,
    user_content: str, 
    messages: list,
    conversation_history: list,
    log_details: bool = True
) -> None:
    """
    Efficiently add assistant and user messages to both lists
    Eliminates repetitive conversation management code
    """
    assistant_msg = {"role": "assistant", "content": accumulated_content}
    user_msg = {"role": "user", "content": user_content}
    
    # Add to both message lists
    messages.extend([assistant_msg, user_msg])
    conversation_history.extend([assistant_msg, user_msg])
    
    if log_details:
        print(f"📤 CODER: Adding assistant message ({len(assistant_msg['content'])} chars) to messages")
        print(f"📤 CODER: Adding user message ({len(user_msg['content'])} chars) to messages")
        print("💾 CODER: Adding messages to conversation history")

def process_action_detection(action: dict, self_obj) -> tuple:
    """
    Efficiently process action detection with standardized patterns
    Returns: (should_interrupt, interrupt_action)
    Reduces the massive if/elif chain
    """
    action_type = action.get('type')
    
    # Define interrupt actions with their specific handling
    interrupt_actions = {
        'read_file': lambda a: (f"Detected read_file action for {a.get('path')}", a),
        'run_command': lambda a: (f"Detected run_command action: {a.get('command')} in {a.get('cwd')}", a),
        'update_file': lambda a: _handle_update_file_detection(a, self_obj),
        'rename_file': lambda a: (f"Detected rename_file action: {a.get('path')} -> {a.get('new_name')}", a),
        'delete_file': lambda a: (f"Detected delete_file action for {a.get('path')}", a),
        'start_backend': lambda a: ("Detected start_backend action", a),
        'start_frontend': lambda a: ("Detected start_frontend action", a),
        'restart_backend': lambda a: ("Detected restart_backend action", a),
        'restart_frontend': lambda a: ("Detected restart_frontend action", a),
        'check_errors': lambda a: ("Detected check_errors action", a),
    }
    
    # Handle todo actions (inline processing)
    if action_type and action_type.startswith('todo_'):
        print(f"\n📋 CODER: Processing todo action inline: {action_type}")
        # Process todo actions inline without interrupting
        if hasattr(self_obj, '_handle_todo_actions'):
            self_obj._handle_todo_actions(action)
        else:
            print(f"📋 CODER: Todo action {action_type} - system doesn't support todos")
        
        # For todo_complete, interrupt AFTER processing
        if action_type == 'todo_complete':
            print(f"\n🚨 CODER: INTERRUPT - todo_complete processed, need continuation prompt")
            action['already_processed'] = True  # Mark as already handled
            return True, action
        
        return False, None  # Other todo actions don't interrupt
    
    # Handle interrupt actions
    if action_type in interrupt_actions:
        message, interrupt_action = interrupt_actions[action_type](action)
        return create_interrupt_action(action_type, interrupt_action, message)
    
    return False, None

def _handle_update_file_detection(action: dict, self_obj) -> tuple:
    """Handle special update_file validation logic"""
    file_path = action.get('path') or action.get('filePath')
    print(f"📝 CODER: Found update_file action for: {file_path}")
    
    if file_path:
        # Check if file was read (preserving exact original logic)
        if file_path not in self_obj.read_files_tracker and file_path not in self_obj.read_files_persistent:
            print(f"\n🚨 CODER: ERROR - File '{file_path}' not read before update!")
            print("⚠️ CODER: This should have been caught by early detection!")
            return "File not read before update - skipping", None  # Don't interrupt, just continue
        else:
            return f"Detected update_file action for {file_path}", action
    
    return "Update file action without path", None

def create_file_success_message(file_path: str, has_errors: bool = False, 
                               python_errors: str = "", typescript_errors: str = "") -> str:
    """
    Create standardized file creation success message
    Reduces repetitive message creation code
    """
    if has_errors:
        error_messages = []
        if python_errors:
            error_messages.append(f"Python validation errors:\n{python_errors}")
        if typescript_errors:
            error_messages.append(f"TypeScript validation errors:\n{typescript_errors}")
        
        return f"""✅ File '{file_path}' created.

**Static Analysis Results:**
{chr(10).join(error_messages)}

**NEXT STEPS:**
1. Fix these static errors first
2. If this is a backend service, create a test file (e.g., `backend/test_api.py`) to verify it works
3. Run the test file with `python backend/test_api.py`
4. Fix any runtime errors
5. Delete the test file when done

Continue with your implementation and testing."""
    else:
        return f"""✅ File '{file_path}' created successfully.

If this was a backend service:
1. Create a test file (e.g., `backend/test_api.py`) 
2. Write Python code to test your endpoints
3. Run it with `python backend/test_api.py`
4. Verify it works, then delete the test file."""

def create_read_file_error_message(file_path: str) -> str:
    """Create standardized read file error message"""
    return f"""❌ Error: Cannot update file '{file_path}' because it doesn't exist.

✅ SOLUTION: Use <action type="file" filePath="{file_path}">YOUR_FILE_CONTENT</action> to create the file first.

Do NOT use update_file for non-existent files. Use the file action to create it.

Please continue with your response."""

# Message templates for different action types
ACTION_SUCCESS_MESSAGES = {
    'update_file': lambda path: f"File '{path}' has been updated successfully. Please continue with your response.",
    'rename_file': lambda path, new_name: f"File '{path}' has been renamed to '{new_name}' successfully. Please continue with your response.",
    'delete_file': lambda path: f"File '{path}' has been deleted successfully. Please continue with your response.",
    'start_backend': lambda result: f"Backend service started successfully on port {result.get('backend_port')}. API available at {result.get('api_url')}. Please continue with your response.",
    'start_frontend': lambda result: f"Frontend service started successfully on port {result.get('frontend_port')}. Available at {result.get('frontend_url')}. Please continue with your response.",
    'restart_backend': lambda result: f"Backend service restarted successfully on port {result.get('backend_port')}. API available at {result.get('api_url')}. Please continue with your response.",
    'restart_frontend': lambda result: f"Frontend service restarted successfully on port {result.get('frontend_port')}. Available at {result.get('frontend_url')}. Please continue with your response.",
}

def get_action_success_message(action_type: str, **kwargs) -> str:
    """Get standardized success message for action type"""
    if action_type in ACTION_SUCCESS_MESSAGES:
        return ACTION_SUCCESS_MESSAGES[action_type](**kwargs)
    return f"Action '{action_type}' completed successfully. Please continue with your response."