#!/usr/bin/env python3

import subprocess
import os
import sys
import json

def check_backend_runtime_errors(backend_path):
    """
    REAL runtime error checker that actually tries to start the backend
    in its own virtual environment
    """
    errors = []
    
    print(f"🔍 RUNTIME ERROR CHECK: {backend_path}")
    
    # Check if virtual environment exists
    venv_path = os.path.join(backend_path, 'venv')
    if not os.path.exists(venv_path):
        errors.append("CRITICAL: No virtual environment found at backend/venv")
        print("❌ No virtual environment found!")
        return errors
    
    # Get the python executable from the virtual environment
    venv_python = os.path.join(venv_path, 'bin', 'python')
    if not os.path.exists(venv_python):
        # Try Windows path
        venv_python = os.path.join(venv_path, 'Scripts', 'python.exe')
    
    if not os.path.exists(venv_python):
        errors.append(f"CRITICAL: Virtual environment Python not found at {venv_python}")
        print("❌ Virtual environment Python not found!")
        return errors
    
    print(f"✅ Found venv Python: {venv_python}")
    
    # Test 1: Try to import the app module in the virtual environment
    print("\n🚀 Testing app.py import in virtual environment...")
    test_import_cmd = [
        venv_python, '-c',
        'import sys; sys.path.insert(0, "."); import app; print("SUCCESS: app.py imported")'
    ]
    
    try:
        result = subprocess.run(
            test_import_cmd,
            cwd=backend_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            errors.append(f"IMPORT ERROR: {error_msg}")
            print(f"❌ Import failed: {error_msg}")
            
            # Extract specific missing module
            if "ModuleNotFoundError" in error_msg:
                import re
                match = re.search(r"No module named '([^']+)'", error_msg)
                if match:
                    missing_module = match.group(1)
                    errors.append(f"MISSING DEPENDENCY: {missing_module}")
                    print(f"❌ MISSING DEPENDENCY: {missing_module}")
        else:
            print(f"✅ {result.stdout.strip()}")
    
    except subprocess.TimeoutExpired:
        errors.append("TIMEOUT: App import took too long (possible infinite loop)")
        print("❌ TIMEOUT: Import took too long")
    except Exception as e:
        errors.append(f"RUNTIME ERROR: {str(e)}")
        print(f"❌ RUNTIME ERROR: {str(e)}")
    
    # Test 2: Try to actually start the FastAPI server
    print("\n🚀 Testing FastAPI server startup...")
    test_server_cmd = [
        venv_python, '-c',
        '''
import sys
sys.path.insert(0, ".")
from app import app
print("SUCCESS: FastAPI app created")
# Test if all routes load
for route in app.routes:
    print(f"  ✓ Route: {route.path}")
'''
    ]
    
    try:
        result = subprocess.run(
            test_server_cmd,
            cwd=backend_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            errors.append(f"STARTUP ERROR: {error_msg}")
            print(f"❌ Startup failed: {error_msg}")
        else:
            print(result.stdout.strip())
    
    except Exception as e:
        errors.append(f"STARTUP ERROR: {str(e)}")
        print(f"❌ STARTUP ERROR: {str(e)}")
    
    # Test 3: Check all required dependencies
    print("\n📦 Checking installed packages in venv...")
    pip_list_cmd = [venv_python, '-m', 'pip', 'list', '--format=json']
    
    try:
        result = subprocess.run(
            pip_list_cmd,
            cwd=backend_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            installed_packages = json.loads(result.stdout)
            installed_names = {pkg['name'].lower() for pkg in installed_packages}
            
            # Check requirements.txt
            req_file = os.path.join(backend_path, 'requirements.txt')
            if os.path.exists(req_file):
                with open(req_file, 'r') as f:
                    requirements = f.read().strip().split('\n')
                
                for req in requirements:
                    if req and not req.startswith('#'):
                        # Extract package name (handle ==, >=, etc.)
                        pkg_name = req.split('==')[0].split('>=')[0].split('<=')[0].strip().lower()
                        if pkg_name not in installed_names:
                            errors.append(f"MISSING PACKAGE: {pkg_name} (from requirements.txt)")
                            print(f"❌ MISSING PACKAGE: {pkg_name}")
    
    except Exception as e:
        print(f"⚠️  Could not check pip packages: {str(e)}")
    
    return errors

if __name__ == "__main__":
    backend_path = '/Users/shanjairaj/local-projects/projects/want-crm-web-application-0808-105000/backend'
    errors = check_backend_runtime_errors(backend_path)
    
    print(f'\n{"="*60}')
    print(f'📋 RUNTIME ERROR CHECK RESULTS:')
    print(f'{"="*60}')
    
    if errors:
        print(f'❌ Found {len(errors)} CRITICAL RUNTIME ERRORS:\n')
        for i, error in enumerate(errors, 1):
            print(f'{i}. {error}')
        print(f'\n⚠️  BACKEND WILL NOT START WITH THESE ERRORS!')
    else:
        print('✅ NO RUNTIME ERRORS - Backend should start successfully!')