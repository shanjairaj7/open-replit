"""
Conversation Manager - Handles message creation and history management
Eliminates duplication of conversation management logic
"""

from typing import List, Dict, Optional, Any

class ConversationManager:
    """Manages conversation messages and history updates"""
    
    @staticmethod
    def create_continuation_messages(
        accumulated_content: str,
        user_content: str,
        messages: List[Dict],
        conversation_history: List[Dict]
    ) -> None:
        """
        Create and add continuation messages to both messages and conversation history
        
        Args:
            accumulated_content: The assistant's accumulated response so far
            user_content: The user's response/continuation message
            messages: The messages list to append to
            conversation_history: The conversation history to append to
        """
        assistant_msg = {"role": "assistant", "content": accumulated_content}
        user_msg = {"role": "user", "content": user_content}
        
        # Add to both messages and conversation history
        messages.append(assistant_msg)
        messages.append(user_msg)
        conversation_history.append(assistant_msg)
        conversation_history.append(user_msg)
        
        print(f"📤 Added assistant message ({len(assistant_msg['content'])} chars) to messages")
        print(f"📤 Added user message ({len(user_msg['content'])} chars) to messages")
        print("💾 Added messages to conversation history")
    
    @staticmethod
    def handle_check_errors_result(
        error_check_result: Dict,
        accumulated_content: str,
        messages: List[Dict],
        conversation_history: List[Dict]
    ) -> None:
        """
        Handle check_errors result with custom formatting
        """
        # Format the error results into a readable message
        backend_status = "✅ No errors" if error_check_result.get('summary', {}).get('backend_has_errors', True) == False else f"❌ {error_check_result.get('backend', {}).get('error_count', 0)} errors"
        frontend_status = "✅ No errors" if error_check_result.get('summary', {}).get('frontend_has_errors', True) == False else f"❌ {error_check_result.get('frontend', {}).get('error_count', 0)} errors"
        
        error_summary = f"""Error Check Results:
📊 Overall Status: {error_check_result.get('summary', {}).get('overall_status', 'unknown')}
🐍 Backend: {backend_status}
⚛️  Frontend: {frontend_status}
📈 Total Errors: {error_check_result.get('summary', {}).get('total_errors', 0)}

"""
        
        # Add detailed errors if any
        if error_check_result.get('backend', {}).get('errors'):
            error_summary += f"🐍 **Backend Errors:**\n```\n{error_check_result['backend']['errors'][:1000]}\n```\n\n"
        
        if error_check_result.get('frontend', {}).get('errors'):
            error_summary += f"⚛️  **Frontend Errors:**\n```\n{error_check_result['frontend']['errors'][:1000]}\n```\n\n"
        
        error_summary += "Please fix any critical errors and continue with your response."
        
        ConversationManager.create_continuation_messages(
            accumulated_content,
            error_summary,
            messages,
            conversation_history
        )
    
    @staticmethod
    def handle_create_file_result(
        create_result: Dict,
        accumulated_content: str,
        messages: List[Dict],
        conversation_history: List[Dict]
    ) -> None:
        """
        Handle create_file_realtime result with validation error checking
        """
        file_path = create_result.get('file_path')
        python_errors = create_result.get('python_errors', '')
        typescript_errors = create_result.get('typescript_errors', '')
        
        error_messages = []
        if python_errors:
            error_messages.append(f"Python validation errors:\n{python_errors}")
        if typescript_errors:
            error_messages.append(f"TypeScript validation errors:\n{typescript_errors}")
        
        if error_messages:
            user_content = f"""✅ File '{file_path}' created.

**Static Analysis Results:**
{'\n\n'.join(error_messages)}

**NEXT STEPS:**
1. Fix these static errors first
2. If this is a backend service, create a test file (e.g., `backend/test_api.py`) to verify it works
3. Run the test file with `python backend/test_api.py`
4. Fix any runtime errors
5. Delete the test file when done

Continue with your implementation and testing."""
        else:
            user_content = f"""✅ File '{file_path}' created successfully.

If this was a backend service:
1. Create a test file (e.g., `backend/test_api.py`) 
2. Write Python code to test your endpoints
3. Run it with `python backend/test_api.py`
4. Verify it works, then delete the test file."""
        
        ConversationManager.create_continuation_messages(
            accumulated_content,
            user_content,
            messages,
            conversation_history
        )
    
    @staticmethod
    def handle_todo_complete(
        todo_status: str,
        accumulated_content: str,
        messages: List[Dict],
        conversation_history: List[Dict]
    ) -> None:
        """
        Handle todo completion with status update
        """
        user_content = f"Great! You've completed a todo. Here's the current todo status:\n\n{todo_status}\n\nPlease continue with the next highest priority task."
        
        ConversationManager.create_continuation_messages(
            accumulated_content,
            user_content,
            messages,
            conversation_history
        )
    
    @staticmethod
    def add_todo_context(
        messages: List[Dict],
        conversation_history: List[Dict],
        todo_status: Optional[str]
    ) -> None:
        """
        Add todo status context to messages if available
        """
        if not todo_status:
            return
            
        print('---- TODOS -----\n')
        print(f"⚠️ Found todo status ({len(todo_status)} chars), adding to context")
        
        # Determine message based on whether todos exist
        if 'no todos created yet' in todo_status:
            note = "No todos have been created yet. Please plan and create todos to then follow and systematically work on tasks."
        else:
            note = "Continue with the highest priority todo."
        
        todo_msg = {"role": "user", "content": f"""
Current todo status:\n\n{todo_status}\n\n
Note: {note}
- Systematically work on each todo until all are completed, integrated and tested to make sure it works end to end. 
- As you work on each todo, update the todo status to in_progress. 
- Once you have completed a todo, update the todo status to completed.
- If you are not sure what to do next, check the todo status and pick the highest priority todo."""}
        
        messages.append(todo_msg)
        conversation_history.append(todo_msg)
        print(f"📤 Added todo status to messages and conversation history")
        print('---- TODOS -----\n')