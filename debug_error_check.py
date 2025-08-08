#!/usr/bin/env python3

import subprocess
import os
import sys
import json
import ast
import re
import tempfile
from pathlib import Path

def debug_python_error_check(backend_path):
    """Debug version of _run_python_error_check with extensive logging"""
    print(f"🔍 DEBUGGING ERROR CHECK: {backend_path}")
    print("="*60)
    
    errors = []
    warnings = []
    
    # Check if virtual environment exists
    venv_path = Path(backend_path) / "venv"
    venv_python = None
    
    print(f"\n📍 PHASE 1: Virtual Environment Detection")
    print(f"   Checking venv path: {venv_path}")
    
    # Try different venv locations
    possible_pythons = [
        venv_path / "bin" / "python",
        venv_path / "bin" / "python3",
        venv_path / "Scripts" / "python.exe",
        venv_path / "Scripts" / "python3.exe",
    ]
    
    for python_path in possible_pythons:
        print(f"   Testing: {python_path} - {'EXISTS' if python_path.exists() else 'NOT FOUND'}")
        if python_path.exists():
            venv_python = str(python_path)
            break
    
    if not venv_python:
        # Fallback to system Python
        python_cmd = "python3"
        if not subprocess.run([python_cmd, "--version"], capture_output=True).returncode == 0:
            python_cmd = "python"
        print(f"❌ No venv found, using system Python: {python_cmd}")
    else:
        python_cmd = venv_python
        print(f"✅ Using virtual environment Python: {python_cmd}")
    
    # Test the Python executable
    print(f"\n📍 PHASE 2: Python Executable Test")
    try:
        result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
        print(f"   Python version: {result.stdout.strip()}")
        print(f"   Return code: {result.returncode}")
    except Exception as e:
        print(f"   ❌ Error testing Python: {e}")
    
    # Get installed packages in venv
    print(f"\n📍 PHASE 3: Installed Packages Check")
    installed_packages = set()
    try:
        print(f"   Running: {python_cmd} -m pip list --format=json")
        result = subprocess.run(
            [python_cmd, '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"   Return code: {result.returncode}")
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            installed_packages = {pkg['name'].lower().replace('-', '_') for pkg in packages}
            print(f"   📦 Found {len(packages)} installed packages:")
            for pkg in sorted(packages):
                print(f"      {pkg['name']} {pkg['version']}")
        else:
            print(f"   ❌ pip list failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Could not list venv packages: {str(e)}")
    
    # Check specific packages we're looking for
    print(f"\n📍 PHASE 4: Target Package Check")
    target_packages = ['jose', 'python_jose', 'passlib', 'uvicorn', 'fastapi']
    for pkg in target_packages:
        if pkg in installed_packages:
            print(f"   ✅ {pkg} - FOUND in installed packages")
        else:
            print(f"   ❌ {pkg} - NOT FOUND in installed packages")
    
    # AST Analysis for imports
    print(f"\n📍 PHASE 5: AST Import Analysis")
    app_files = []
    exclude_dirs = {'test_env', 'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache'}
    
    for root, dirs, files in os.walk(backend_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py'):
                app_files.append(os.path.join(root, file))
    
    print(f"   📁 Found {len(app_files)} Python files:")
    for f in app_files:
        print(f"      {os.path.relpath(f, backend_path)}")
    
    # Track all imports found in the code
    all_imports = set()
    local_modules = set()
    
    for py_file in app_files:
        rel_path = os.path.relpath(py_file, backend_path)
        print(f"\n   🔍 Analyzing: {rel_path}")
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content, filename=py_file)
                file_imports = []
                
                # Collect all imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            all_imports.add(module)
                            file_imports.append(f"import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            if node.level == 0:  # Absolute import
                                all_imports.add(module)
                                file_imports.append(f"from {node.module} import ...")
                            else:  # Relative import
                                local_modules.add(module)
                
                print(f"      Imports found: {file_imports}")
                
            except SyntaxError as e:
                print(f"      ❌ SYNTAX ERROR at line {e.lineno}: {e.msg}")
                errors.append(f"❌ SYNTAX ERROR in {rel_path}:{e.lineno} - {e.msg}")
                
        except Exception as e:
            print(f"      ❌ FILE ERROR: {str(e)}")
            errors.append(f"❌ FILE ERROR in {rel_path} - {str(e)}")
    
    print(f"\n   📋 All unique imports found: {sorted(all_imports)}")
    print(f"   📋 Local modules: {sorted(local_modules)}")
    
    # Import Testing in Virtual Environment
    print(f"\n📍 PHASE 6: Import Testing in Virtual Environment")
    if venv_python:
        missing_imports = set()
        
        for import_name in sorted(all_imports):
            if import_name in local_modules or import_name in ['models', 'services', 'routers', 'dependencies']:
                print(f"   ⏭️  Skipping local module: {import_name}")
                continue  # Skip local modules
            
            print(f"   🧪 Testing import: {import_name}")
            # Test if import works in venv
            test_cmd = [python_cmd, '-c', f'import {import_name}; print("SUCCESS")']
            try:
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    missing_imports.add(import_name)
                    print(f"      ❌ Failed: {result.stderr.strip()}")
                    errors.append(f"❌ MISSING IMPORT: {import_name} - not available in virtual environment")
                else:
                    print(f"      ✅ Success: {result.stdout.strip()}")
            except subprocess.TimeoutExpired:
                print(f"      ⏱️ Timeout")
                warnings.append(f"Import test timeout for {import_name}")
            except Exception as e:
                print(f"      ❌ Error: {e}")
    else:
        print("   ⏭️  Skipping - no virtual environment")
    
    # Requirements.txt Check
    print(f"\n📍 PHASE 7: Requirements.txt Analysis")
    req_file = Path(backend_path) / "requirements.txt"
    if req_file.exists():
        print(f"   📄 Reading: {req_file}")
        with open(req_file, 'r') as f:
            requirements = f.read().strip().split('\n')
        
        print(f"   📋 Requirements found:")
        for req in requirements:
            if req and not req.startswith('#'):
                print(f"      {req}")
                
                # Parse requirement (handle ==, >=, ~=, etc.)
                base_req = re.split(r'[<>=~!]', req)[0].strip()
                
                # Remove extras (like [standard], [cryptography], [bcrypt])
                # Extract just the package name before any brackets
                if '[' in base_req:
                    req_name = base_req.split('[')[0].strip().lower().replace('-', '_')
                else:
                    req_name = base_req.lower().replace('-', '_')
                    
                print(f"         Base requirement: {base_req}")
                print(f"         Normalized name: {req_name}")
                
                # Check if it's installed
                if req_name not in installed_packages:
                    print(f"         ❌ NOT INSTALLED")
                    errors.append(f"❌ MISSING REQUIREMENT: {req} - not installed in virtual environment")
                else:
                    print(f"         ✅ INSTALLED")
    else:
        print(f"   ❌ requirements.txt not found")
    
    # Summary
    print(f"\n📍 PHASE 8: Summary")
    print(f"   Total errors: {len(errors)}")
    print(f"   Total warnings: {len(warnings)}")
    
    if errors:
        print(f"\n❌ ERRORS FOUND:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
    
    if warnings:
        print(f"\n⚠️ WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    return errors, warnings

if __name__ == "__main__":
    backend_path = '/Users/shanjairaj/local-projects/projects/want-crm-web-application-0808-152839/backend'
    errors, warnings = debug_python_error_check(backend_path)