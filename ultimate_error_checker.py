#!/usr/bin/env python3

import subprocess
import os
import sys
import json
import ast
import re
import tempfile
from pathlib import Path

def run_ultimate_error_check(backend_path):
    """
    Ultimate error checker that combines:
    1. AST syntax analysis
    2. Import validation
    3. Virtual environment runtime testing
    4. Dependency checking
    5. Actual server startup test
    """
    errors = []
    warnings = []
    
    print(f"🔍 ULTIMATE ERROR CHECK: {backend_path}")
    print("="*60)
    
    # PHASE 1: AST Syntax Analysis
    print("\n📝 PHASE 1: AST Syntax Analysis")
    print("-"*40)
    
    app_files = []
    exclude_dirs = {'test_env', 'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache'}
    
    for root, dirs, files in os.walk(backend_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py'):
                app_files.append(os.path.join(root, file))
    
    print(f"Found {len(app_files)} Python files to analyze")
    
    # Track all imports found in the code
    all_imports = set()
    local_modules = set()
    
    for py_file in app_files:
        rel_path = os.path.relpath(py_file, backend_path)
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content, filename=py_file)
                
                # Collect all imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            if node.level == 0:  # Absolute import
                                all_imports.add(module)
                            else:  # Relative import
                                local_modules.add(module)
                
                print(f"✅ {rel_path} - Syntax OK")
                
            except SyntaxError as e:
                errors.append(f"SYNTAX ERROR in {rel_path}:{e.lineno} - {e.msg}")
                print(f"❌ {rel_path} - Syntax Error at line {e.lineno}: {e.msg}")
                
        except Exception as e:
            errors.append(f"FILE ERROR in {rel_path} - {str(e)}")
            print(f"❌ {rel_path} - File Error: {str(e)}")
    
    # PHASE 2: Virtual Environment Check
    print("\n🐍 PHASE 2: Virtual Environment Check")
    print("-"*40)
    
    venv_path = os.path.join(backend_path, 'venv')
    venv_python = None
    
    # Try different venv locations
    possible_pythons = [
        os.path.join(venv_path, 'bin', 'python'),
        os.path.join(venv_path, 'bin', 'python3'),
        os.path.join(venv_path, 'Scripts', 'python.exe'),
        os.path.join(venv_path, 'Scripts', 'python3.exe'),
    ]
    
    for python_path in possible_pythons:
        if os.path.exists(python_path):
            venv_python = python_path
            break
    
    if not venv_python:
        errors.append("CRITICAL: No virtual environment found - backend cannot run")
        print("❌ No virtual environment found!")
        return errors, warnings
    
    print(f"✅ Found venv Python: {venv_python}")
    
    # PHASE 3: Import Testing in Virtual Environment
    print("\n📦 PHASE 3: Import Testing in Virtual Environment")
    print("-"*40)
    
    # Get installed packages in venv
    installed_packages = set()
    try:
        result = subprocess.run(
            [venv_python, '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            installed_packages = {pkg['name'].lower().replace('-', '_') for pkg in packages}
            print(f"✅ Found {len(installed_packages)} installed packages in venv")
    except Exception as e:
        warnings.append(f"Could not list venv packages: {str(e)}")
    
    # Test each import in the virtual environment
    missing_imports = set()
    
    for import_name in sorted(all_imports):
        if import_name in local_modules or import_name in ['models', 'services', 'routers', 'dependencies']:
            continue  # Skip local modules
        
        # Test if import works in venv
        test_cmd = [venv_python, '-c', f'import {import_name}']
        try:
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                missing_imports.add(import_name)
                errors.append(f"MISSING IMPORT: {import_name} - not available in virtual environment")
                print(f"❌ Missing: {import_name}")
            else:
                print(f"✅ Found: {import_name}")
        except subprocess.TimeoutExpired:
            warnings.append(f"Import test timeout for {import_name}")
    
    # PHASE 4: Full Module Load Test
    print("\n🚀 PHASE 4: Full Module Load Test")
    print("-"*40)
    
    # Create a test script that loads the app
    test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

# Try to import and create the app
try:
    from app import app
    print("SUCCESS: app module imported")
    
    # Check if it's a FastAPI app
    if hasattr(app, 'routes'):
        print(f"SUCCESS: FastAPI app created with {len(app.routes)} routes")
        for route in app.routes:
            if hasattr(route, 'path'):
                print(f"  ✓ Route: {route.path}")
    else:
        print("WARNING: app exists but doesn't appear to be a FastAPI app")
        
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
        tf.write(test_script)
        test_file = tf.name
    
    try:
        result = subprocess.run(
            [venv_python, test_file],
            cwd=backend_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Parse the error to find specific issues
            error_output = result.stderr + result.stdout
            
            # Look for ModuleNotFoundError
            module_matches = re.findall(r"ModuleNotFoundError: No module named '([^']+)'", error_output)
            for module in module_matches:
                errors.append(f"RUNTIME ERROR: Missing module '{module}' prevents server startup")
                print(f"❌ Runtime Error: Missing module '{module}'")
            
            # Look for ImportError
            import_matches = re.findall(r"ImportError: cannot import name '([^']+)'", error_output)
            for name in import_matches:
                errors.append(f"RUNTIME ERROR: Cannot import '{name}' - check if function/class exists")
                print(f"❌ Runtime Error: Cannot import '{name}'")
            
            # Look for AttributeError
            attr_matches = re.findall(r"AttributeError: module '([^']+)' has no attribute '([^']+)'", error_output)
            for module, attr in attr_matches:
                errors.append(f"RUNTIME ERROR: Module '{module}' has no attribute '{attr}'")
                print(f"❌ Runtime Error: Module '{module}' missing attribute '{attr}'")
            
            if not (module_matches or import_matches or attr_matches):
                # Generic error
                errors.append(f"RUNTIME ERROR: {error_output.strip()}")
                print(f"❌ Runtime Error: Failed to load app")
                
        else:
            print(result.stdout.strip())
            
    except subprocess.TimeoutExpired:
        errors.append("TIMEOUT: App load took too long (possible infinite loop)")
        print("❌ Timeout: App load took too long")
    finally:
        os.unlink(test_file)
    
    # PHASE 5: Requirements.txt Check
    print("\n📋 PHASE 5: Requirements Check")
    print("-"*40)
    
    req_file = os.path.join(backend_path, 'requirements.txt')
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            requirements = f.read().strip().split('\n')
        
        for req in requirements:
            if req and not req.startswith('#'):
                # Parse requirement (handle ==, >=, ~=, etc.)
                req_name = re.split(r'[<>=~!]', req)[0].strip().lower().replace('-', '_')
                
                # Check if it's installed
                if req_name not in installed_packages:
                    errors.append(f"MISSING REQUIREMENT: {req} - not installed in virtual environment")
                    print(f"❌ Missing requirement: {req}")
                else:
                    print(f"✅ Installed: {req_name}")
    
    # PHASE 6: Actual Server Start Test (if no errors so far)
    if not errors:
        print("\n🌐 PHASE 6: Server Start Test")
        print("-"*40)
        
        # Try to actually start the server
        start_cmd = [venv_python, '-m', 'uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '0']
        
        try:
            # Start server and immediately kill it (just testing if it starts)
            process = subprocess.Popen(
                start_cmd,
                cwd=backend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to see if it starts
            import time
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                # Server started successfully
                print("✅ Server starts successfully!")
                process.terminate()
            else:
                # Server crashed
                stdout, stderr = process.communicate()
                error_msg = stderr or stdout
                errors.append(f"SERVER CRASH: {error_msg}")
                print(f"❌ Server crashed: {error_msg}")
                
        except Exception as e:
            warnings.append(f"Could not test server start: {str(e)}")
    
    return errors, warnings

if __name__ == "__main__":
    backend_path = '/Users/shanjairaj/local-projects/projects/want-crm-web-application-0808-105000/backend'
    errors, warnings = run_ultimate_error_check(backend_path)
    
    print(f'\n{"="*60}')
    print(f'📊 ULTIMATE ERROR CHECK SUMMARY')
    print(f'{"="*60}')
    
    if warnings:
        print(f'\n⚠️  {len(warnings)} WARNINGS:')
        for warning in warnings:
            print(f'   - {warning}')
    
    if errors:
        print(f'\n❌ {len(errors)} CRITICAL ERRORS FOUND:')
        for i, error in enumerate(errors, 1):
            print(f'\n{i}. {error}')
        print(f'\n🚫 BACKEND WILL NOT RUN WITH THESE ERRORS!')
    else:
        print('\n✅ ALL CHECKS PASSED - Backend is ready to run!')