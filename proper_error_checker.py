#!/usr/bin/env python3

import sys
import subprocess
import os
import ast

def run_proper_error_check(backend_path):
    """Proper error checking that only validates actual application code"""
    errors = []
    
    print(f"🔍 Scanning backend application code in: {backend_path}")
    
    # Only scan actual application Python files, exclude virtual environments
    app_files = []
    exclude_dirs = {'test_env', 'venv', '__pycache__', '.git', 'node_modules'}
    
    for root, dirs, files in os.walk(backend_path):
        # Remove excluded directories from the walk
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                app_files.append(os.path.join(root, file))
    
    print(f"📁 Found {len(app_files)} application Python files")
    for f in app_files:
        print(f"   - {os.path.relpath(f, backend_path)}")
    
    # Add backend path to Python path for proper imports
    sys.path.insert(0, backend_path)
    
    try:
        # Test each application file
        for py_file in app_files:
            rel_path = os.path.relpath(py_file, backend_path)
            print(f"\n🔍 Checking: {rel_path}")
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse and check imports
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module:
                                module_name = node.module
                                try:
                                    __import__(module_name)
                                    print(f"   ✅ {module_name}")
                                except ImportError as e:
                                    # Check if it's a local import that should exist
                                    if module_name in ['models', 'services', 'routers', 'dependencies']:
                                        errors.append(f"IMPORT ERROR: Cannot import '{module_name}' in {rel_path} - {str(e)}")
                                        print(f"   ❌ {module_name} - {str(e)}")
                                    elif module_name.startswith(('models.', 'services.', 'routers.')):
                                        errors.append(f"IMPORT ERROR: Cannot import '{module_name}' in {rel_path} - {str(e)}")
                                        print(f"   ❌ {module_name} - {str(e)}")
                                    else:
                                        # External dependency
                                        if 'jose' in module_name or 'passlib' in module_name or 'email_validator' in module_name:
                                            errors.append(f"DEPENDENCY ERROR: Missing package for '{module_name}' in {rel_path} - {str(e)}")
                                            print(f"   ❌ MISSING DEPENDENCY: {module_name} - {str(e)}")
                                        else:
                                            print(f"   ⚠️  External: {module_name} (may be optional)")
                        
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                try:
                                    __import__(alias.name)
                                    print(f"   ✅ {alias.name}")
                                except ImportError as e:
                                    if any(dep in alias.name for dep in ['jose', 'passlib', 'email_validator']):
                                        errors.append(f"DEPENDENCY ERROR: Missing package '{alias.name}' in {rel_path} - {str(e)}")
                                        print(f"   ❌ MISSING DEPENDENCY: {alias.name} - {str(e)}")
                                    else:
                                        print(f"   ⚠️  External: {alias.name} (may be optional)")
                
                except SyntaxError as e:
                    errors.append(f"SYNTAX ERROR: {str(e)} in {rel_path}")
                    print(f"   ❌ SYNTAX ERROR: {str(e)}")
            
            except Exception as e:
                errors.append(f"FILE READ ERROR: {str(e)} for {rel_path}")
                print(f"   ❌ FILE ERROR: {str(e)}")
        
        # Test if app.py can be loaded
        print(f"\n🚀 Testing app.py module load...")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('app', os.path.join(backend_path, 'app.py'))
            if spec and spec.loader:
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)
                print('   ✅ app.py loaded successfully')
        except Exception as e:
            errors.append(f"MODULE LOAD ERROR: Cannot load app.py - {str(e)}")
            print(f"   ❌ MODULE LOAD FAILED: {str(e)}")
    
    finally:
        # Clean up Python path
        if backend_path in sys.path:
            sys.path.remove(backend_path)
    
    return errors

if __name__ == "__main__":
    backend_path = '/Users/shanjairaj/local-projects/projects/want-crm-web-application-0808-105000/backend'
    errors = run_proper_error_check(backend_path)

    print(f'\n📋 PROPER ERROR CHECK RESULTS:')
    print(f'Found {len(errors)} actual application errors:\n')

    for i, error in enumerate(errors, 1):
        print(f'{i}. {error}')

    if not errors:
        print('✅ NO ERRORS FOUND - Backend is ready to run!')
    else:
        print(f'\n❌ CRITICAL: {len(errors)} real errors must be fixed before starting preview')