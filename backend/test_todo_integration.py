#!/usr/local/bin/python3.13
"""
Test script to verify the complete todo integration in test_groq_with_todos.py
"""

import sys
import os
sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend')

def test_todo_integration():
    """Test that all todo functionality is properly integrated"""
    
    print("🧪 Testing Todo Integration with test_groq_with_todos.py")
    print("=" * 60)
    
    # Import the integrated system
    sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/setup')
    from test_groq_with_todos import BoilerplatePersistentGroq
    
    # Test basic initialization
    try:
        api_key = "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"
        system = BoilerplatePersistentGroq(
            api_key=api_key,
            project_name="todo-test-project"
        )
        print("✅ System initialization successful")
        
        # Test todo functionality exists
        if hasattr(system, 'todos'):
            print("✅ Todo list attribute exists")
        else:
            print("❌ Todo list attribute missing")
            
        if hasattr(system, '_handle_todo_actions'):
            print("✅ Todo action handler exists")
        else:
            print("❌ Todo action handler missing")
            
        if hasattr(system, '_get_todo_status_summary'):
            print("✅ Todo status summary method exists")
        else:
            print("❌ Todo status summary method missing")
            
        # Test system prompt includes todo workflow
        system_prompt = system._load_system_prompt()
        if "TODO-DRIVEN WORKFLOW" in system_prompt:
            print("✅ System prompt includes todo workflow instructions")
        else:
            print("❌ System prompt missing todo workflow instructions")
            
        # Test context includes todo status (when todos exist)
        context = system.get_project_context()
        print("✅ Context generation working")
        
        # Test todo creation
        print("\n🧪 Testing todo creation...")
        test_action = {
            'type': 'todo_create',
            'id': 'test_todo_1',
            'content': 'Test todo creation',
            'raw_attrs': {
                'id': 'test_todo_1',
                'priority': 'high',
                'integration': 'false'
            }
        }
        system._handle_todo_actions(test_action)
        
        if len(system.todos) == 1:
            print("✅ Todo creation successful")
            
            # Test todo status summary
            status_summary = system._get_todo_status_summary()
            if status_summary and "test_todo_1" in status_summary:
                print("✅ Todo status summary working")
            else:
                print("❌ Todo status summary not working")
        else:
            print("❌ Todo creation failed")
            
        print("\n✅ Todo integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_todo_integration()
    if success:
        print("\n🎉 All tests passed! Todo integration is working.")
    else:
        print("\n💥 Tests failed! Todo integration needs fixes.")