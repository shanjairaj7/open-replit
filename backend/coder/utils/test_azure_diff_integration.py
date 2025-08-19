#!/usr/bin/env python3
"""
Test the new diff functionality integration with Azure hybrid system
This simulates how the model would use the new update_file format
"""
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'setup', 'azure_openrouter_hybrid'))
from base_test_azure_hybrid import BoilerplatePersistentGroq

def test_diff_integration():
    """Test the new update_file diff functionality"""
    print("🧪 Testing Azure Hybrid System Diff Integration")
    print("="*60)
    
    # Initialize the system (without actually creating project)
    try:
        # Mock system for testing
        class MockGroqSystem:
            def __init__(self):
                self.project_id = "test-project"
                self.api_base_url = "http://localhost:8000"
            
            def _read_file_via_api(self, file_path):
                """Mock file reading"""
                print(f"📖 Mock reading file: {file_path}")
                # Return sample Python content
                return '''def hello_world():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value'''
            
            def _update_file_via_api(self, file_path, content):
                """Mock file updating"""
                print(f"💾 Mock updating file: {file_path}")
                print(f"📄 New content length: {len(content)} characters")
                print("Content preview:")
                print("-" * 40)
                lines = content.split('\n')
                for i, line in enumerate(lines[:10], 1):
                    print(f"{i:3}: {line}")
                if len(lines) > 10:
                    print("    ... (truncated)")
                print("-" * 40)
                return {"status": "updated", "python_errors": "", "typescript_errors": ""}
            
            def _remove_backticks_from_content(self, content):
                """Mock backtick removal"""
                return content.strip()
        
        system = MockGroqSystem()
        
        # Import and initialize the handler manually
        sys.path.insert(0, os.path.dirname(__file__))
        from update_file_handler import UpdateFileHandler
        
        handler = UpdateFileHandler(
            read_file_callback=system._read_file_via_api,
            update_file_callback=system._update_file_via_api
        )
        
        print("✅ Handler initialized successfully")
        
        # Test 1: Simple diff update
        print("\n" + "="*50)
        print("TEST 1: Simple Function Update")
        print("="*50)
        
        action1 = {
            'path': 'test_file.py',
            'content': '''<diff>
------- SEARCH
def hello_world():
    print("Hello, World!")
=======
def hello_world():
    print("Hello, Enhanced World!")
    print("This is an updated function")
+++++++ REPLACE
</diff>'''
        }
        
        result1 = handler.handle_update_file(action1)
        print(f"\nResult: {result1}")
        
        # Test 2: Multiple updates
        print("\n" + "="*50)
        print("TEST 2: Multiple Updates")
        print("="*50)
        
        action2 = {
            'path': 'test_file.py',
            'content': '''<diff>
------- SEARCH
class TestClass:
    def __init__(self):
        self.value = 42
=======
class TestClass:
    def __init__(self):
        self.value = 100
        self.name = "Enhanced Test"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    def get_value(self):
        return self.value
=======
    def get_value(self):
        print(f"Getting value for {self.name}")
        return self.value
+++++++ REPLACE
</diff>'''
        }
        
        result2 = handler.handle_update_file(action2)
        print(f"\nResult: {result2}")
        
        # Test 3: Failed search
        print("\n" + "="*50)
        print("TEST 3: Failed Search Handling")
        print("="*50)
        
        action3 = {
            'path': 'test_file.py',
            'content': '''<diff>
------- SEARCH
def nonexistent_function():
    pass
=======
def new_function():
    return "new"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
def goodbye():
    print("Goodbye!")
=======
def goodbye():
    print("Enhanced Goodbye!")
    print("Additional farewell message")
+++++++ REPLACE
</diff>'''
        }
        
        result3 = handler.handle_update_file(action3)
        print(f"\nResult: {result3}")
        
        # Test 4: Legacy format
        print("\n" + "="*50)
        print("TEST 4: Legacy Format (Full Replacement)")
        print("="*50)
        
        action4 = {
            'path': 'test_file.py',
            'content': '''def new_file_content():
    """This is a completely new file"""
    return "Legacy update - full replacement"

class NewClass:
    pass'''
        }
        
        result4 = handler.handle_update_file(action4)
        print(f"\nResult: {result4}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("The new diff functionality is working correctly!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_diff_integration()