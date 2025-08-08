#!/usr/bin/env python3
"""
Test the error checking API flow locally
"""
import os
import sys
from pathlib import Path

# Add the current directory to path so we can import
sys.path.insert(0, str(Path(__file__).parent))

# Test in the backend boilerplate directory
backend_path = Path("boilerplate/backend-boilerplate")
os.chdir(backend_path)

def test_error_file_reading():
    """Test reading the .python-errors.txt file"""
    error_file_path = Path(".python-errors.txt")
    
    print(f"Testing error file reading...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Error file path: {error_file_path}")
    print(f"Error file exists: {error_file_path.exists()}")
    
    if error_file_path.exists():
        with open(error_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Error file content:")
        print(f"'{content}'")
        print(f"Content length: {len(content)}")
        print(f"Content repr: {repr(content)}")
        
        return {
            "errors": content,
            "status": {"executed": True, "success": True, "error": None}
        }
    else:
        print("No error file found!")
        return {
            "errors": "No error file found",
            "status": {"executed": True, "success": False, "error": "File not found"}
        }

def simulate_file_update():
    """Simulate the file update API call"""
    print("\n" + "="*50)
    print("SIMULATING FILE UPDATE API CALL")
    print("="*50)
    
    # Simulate the file path check
    file_path = "backend/test_new_error.py"
    print(f"File path: {file_path}")
    print(f"Is Python backend file: {file_path.startswith('backend/') and file_path.endswith('.py')}")
    
    if file_path.startswith("backend/") and file_path.endswith(".py"):
        print("✅ DETECTED PYTHON FILE - Would run error check")
        
        # Simulate the _run_python_error_check call
        result = test_error_file_reading()
        print(f"Error check result: {result}")
        
        # Simulate response building
        response = {"status": "updated", "file": file_path}
        response["python_errors"] = result["errors"]
        response["python_check_status"] = result["status"]
        
        print(f"Final API response: {response}")
        return response
    else:
        print("❌ Not a Python backend file")
        return {"status": "updated", "file": file_path}

if __name__ == "__main__":
    try:
        result = simulate_file_update()
        print(f"\n🎯 FINAL RESULT: {result}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()