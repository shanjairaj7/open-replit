#!/usr/bin/env python3
"""
Test the VPS API logic locally with the updated error checker
"""
import subprocess
import os
import sys
from pathlib import Path

# Test in the backend boilerplate directory
backend_path = Path("boilerplate/backend-boilerplate")
os.chdir(backend_path)

def simulate_container_exec():
    """Simulate container.exec_run('python python-error-checker.py . --once')"""
    print("🔍 SIMULATING container.exec_run('python python-error-checker.py . --once')")
    
    try:
        # This is exactly what the VPS will run in the container
        result = subprocess.run(
            [sys.executable, "python-error-checker.py", ".", "--once"],
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Output length: {len(result.stdout + result.stderr)}")
        
        # Simulate the VPS logic
        if result.returncode != 0:
            output = result.stdout + result.stderr
        else:
            output = result.stdout
            
        print(f"Raw output: {repr(output)}")
        
        return {
            "exit_code": result.returncode,
            "output": output
        }
        
    except Exception as e:
        print(f"❌ Error running error checker: {e}")
        return {
            "exit_code": -1,
            "output": f"Error: {e}"
        }

def simulate_vps_api_response():
    """Simulate the complete VPS API file update flow"""
    print("\n" + "="*60)
    print("SIMULATING COMPLETE VPS API FILE UPDATE")
    print("="*60)
    
    # Simulate file creation
    file_path = "backend/test_error.py"
    print(f"File path: {file_path}")
    print(f"Is Python backend file: {file_path.startswith('backend/') and file_path.endswith('.py')}")
    
    if file_path.startswith("backend/") and file_path.endswith(".py"):
        print("✅ DETECTED PYTHON FILE - Running error check")
        
        # Simulate _run_python_error_check
        container_result = simulate_container_exec()
        
        # Simulate the VPS response building
        response = {
            "status": "updated", 
            "file": file_path,
            "python_errors": container_result["output"],
            "python_check_status": {
                "executed": True,
                "success": True,
                "error": None
            }
        }
        
        print(f"\n🎯 FINAL API RESPONSE:")
        print(f"Status: {response['status']}")
        print(f"File: {response['file']}")
        print(f"Python errors length: {len(response['python_errors'])}")
        print(f"Python errors preview: {repr(response['python_errors'][:200])}")
        
        return response
    else:
        print("❌ Not a Python backend file")
        return {"status": "updated", "file": file_path}

if __name__ == "__main__":
    try:
        print(f"Current directory: {os.getcwd()}")
        print(f"Error checker exists: {Path('python-error-checker.py').exists()}")
        
        result = simulate_vps_api_response()
        
        # Check if errors were actually returned
        if "python_errors" in result:
            if "Python validation errors:" in result["python_errors"] or "error:" in result["python_errors"]:
                print("\n✅ SUCCESS: API would return actual errors!")
            else:
                print(f"\n❌ PROBLEM: API returned: {repr(result['python_errors'][:100])}")
        else:
            print("\n❌ PROBLEM: No python_errors in response")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()