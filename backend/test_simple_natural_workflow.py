#!/usr/local/bin/python3.13
"""
Simple Natural Workflow Demo - Without Complex Interrupts
Test the basic todo-driven development workflow
"""

import os
from backend.setup.test_groq_natural_workflow import NaturalWorkflowGroq

def test_simple_todo_app():
    """Test with a simple todo app that should work end-to-end"""
    print("🧠 Testing Simple Natural Workflow - Todo App")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable is required")
        return
    
    # Simple, clear request
    user_request = "Create a simple todo app where I can add tasks, mark them complete, and view my task list"
    
    print(f"🎯 Test Request: {user_request}")
    print("=" * 60)
    
    try:
        # Initialize system
        system = NaturalWorkflowGroq(
            api_key=api_key,
            project_name="Simple Todo App"
        )
        
        # Process the request
        print(f"\n🚀 Processing request with natural workflow...")
        system.process_request(user_request)
        
        # Show final todo status
        print(f"\n📋 Final Todo Status:")
        system._display_todos()
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_todo_app()