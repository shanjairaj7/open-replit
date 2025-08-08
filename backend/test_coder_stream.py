#!/usr/bin/env python3
"""Test the coder's streaming behavior with multiple actions"""

import os
from pathlib import Path
from groq import Groq
from openai import OpenAI
from coder.index import coder
from shared_models import GroqAgentState

# Create a mock GroqAgentState for testing
class MockGroqAgentState:
    def __init__(self):
        self.client = OpenAI(
            base_url='https://openrouter.ai/api/v1', 
            api_key='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', 
            default_headers={"x-include-usage": 'true'}
        )
        self.model = "google/gemini-2.5-flash"
        self.token_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.read_files_tracker = set()
        self.read_files_persistent = set()
        self.conversation_history = []
        self.backend_dir = Path(__file__).parent
        self.project_id = "test-project"
        self.api_base_url = "http://localhost:8000/api"
    
    def _handle_read_file_interrupt(self, action):
        """Mock file reading"""
        file_path = action.get('path')
        print(f"\n📖 MOCK: Reading file {file_path}")
        return f"# Mock content of {file_path}\nprint('Hello from {file_path}')"
    
    def _handle_run_command_interrupt(self, action):
        """Mock command execution"""
        command = action.get('command')
        cwd = action.get('cwd', '')
        print(f"\n💻 MOCK: Running command '{command}' in {cwd}")
        return {"output": f"Mock output from: {command}", "success": True}
    
    def _handle_update_file_interrupt(self, action):
        """Mock file update"""
        file_path = action.get('path')
        content = action.get('content', '')
        print(f"\n✏️ MOCK: Updating file {file_path}")
        print(f"   Content preview: {content[:50]}...")
        return {"success": True}
    
    def _handle_create_file_realtime(self, action):
        """Mock file creation"""
        content = action.get('content', '')
        # Extract file path from content
        import re
        path_match = re.search(r'filePath="([^"]+)"', content)
        if path_match:
            file_path = path_match.group(1)
            print(f"\n🆕 MOCK: Creating file {file_path}")
            return {"success": True}
        return {"success": False}
    
    def _handle_rename_file_interrupt(self, action):
        """Mock file rename"""
        old_path = action.get('path')
        new_name = action.get('new_name')
        print(f"\n🔄 MOCK: Renaming {old_path} to {new_name}")
        return {"success": True}
    
    def _handle_delete_file_interrupt(self, action):
        """Mock file deletion"""
        file_path = action.get('path')
        print(f"\n🗑️ MOCK: Deleting file {file_path}")
        return {"success": True}


def test_multiple_actions_scenario():
    """Test a scenario with multiple actions in the response"""
    print("TEST: Multiple Actions in Stream")
    print("="*80)
    
    # Create mock state
    state = MockGroqAgentState()
    
    # Import the senior engineer prompt
    from coder.prompts import senior_engineer_prompt
    
    # Test messages that will generate multiple actions
    messages = [
        {
            "role": "system", 
            "content": senior_engineer_prompt
        },
        {
            "role": "user",
            "content": """Please do the following:
1. First read the config.py file
2. Run 'python --version' to check Python version  
3. Create a new file called hello.py with a simple hello world function
4. Update the existing main.py file to import the hello function

Use the appropriate action tags for each operation."""
        }
    ]
    
    print("📤 Sending request to generate multiple actions...")
    print("\nExpected behavior:")
    print("1. Should detect read_file for config.py and interrupt")
    print("2. Should detect run_command for python --version and interrupt")
    print("3. Should detect file creation for hello.py")
    print("4. Should detect update_file for main.py and check if it needs reading first")
    print("\n" + "-"*80 + "\n")
    
    # Run the coder
    try:
        result = coder(messages, state)
        print(f"\n\nFINAL RESULT: {result}")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()


def test_update_file_early_detection():
    """Test the early detection of update_file needing read"""
    print("\n\nTEST: Update File Early Detection")
    print("="*80)
    
    # Create mock state with no files read
    state = MockGroqAgentState()
    state.read_files_tracker = set()  # Empty - no files read
    
    # Import the senior engineer prompt
    from coder.prompts import senior_engineer_prompt
    
    messages = [
        {
            "role": "system", 
            "content": senior_engineer_prompt
        },
        {
            "role": "user",
            "content": "Please update the app.py file to add a new route /api/test that returns {'status': 'ok'}. Use the update_file action."
        }
    ]
    
    print("📤 Sending request to update a file that hasn't been read...")
    print("\nExpected behavior:")
    print("1. Should detect update_file action early in the stream")
    print("2. Should check if app.py was previously read")
    print("3. Should interrupt with read_file action before attempting update")
    print("\n" + "-"*80 + "\n")
    
    try:
        result = coder(messages, state)
        print(f"\n\nFINAL RESULT: {result}")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing Coder Streaming Behavior\n")
    
    # Uncomment the test you want to run
    test_multiple_actions_scenario()
    # test_update_file_early_detection()