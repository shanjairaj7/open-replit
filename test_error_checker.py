#!/usr/bin/env python3

import sys
import subprocess
import tempfile
import os

def run_enterprise_error_check(backend_path):
    """Enterprise-grade error checking system"""
    errors = []
    
    # 1. PYRIGHT - Microsoft's language server (same as VSCode)
    try:
        result = subprocess.run([
            'pyright', '--outputformat', 'json', backend_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0 and result.stdout:
            import json
            try:
                pyright_data = json.loads(result.stdout)
                if 'generalDiagnostics' in pyright_data:
                    for diagnostic in pyright_data['generalDiagnostics']:
                        if diagnostic['severity'] == 'error':
                            errors.append(f"PYRIGHT ERROR: {diagnostic['message']} in {diagnostic['file']}:{diagnostic['range']['start']['line']}")
            except:
                pass
    except Exception as e:
        errors.append(f"PYRIGHT CHECK FAILED: {str(e)}")
    
    # 2. RUNTIME IMPORT VALIDATION - Test ALL imports
    python_files = []
    for root, dirs, files in os.walk(backend_path):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                python_files.append(os.path.join(root, file))
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract import statements
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                try:
                                    __import__(alias.name)
                                except ImportError as e:
                                    errors.append(f"IMPORT ERROR: Cannot import '{alias.name}' in {py_file} - {str(e)}")
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            try:
                                __import__(node.module)
                            except ImportError as e:
                                errors.append(f"IMPORT ERROR: Cannot import '{node.module}' in {py_file} - {str(e)}")
            except SyntaxError as e:
                errors.append(f"SYNTAX ERROR: {str(e)} in {py_file}")
        except Exception as e:
            errors.append(f"FILE READ ERROR: {str(e)} for {py_file}")
    
    # 3. FULL MODULE EXECUTION TEST - Try to load app.py
    try:
        sys.path.insert(0, backend_path)
        import importlib.util
        spec = importlib.util.spec_from_file_location('app', os.path.join(backend_path, 'app.py'))
        if spec and spec.loader:
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            print('✅ MODULE LOAD TEST: app.py loaded successfully')
    except Exception as e:
        errors.append(f"MODULE LOAD ERROR: Cannot load app.py - {str(e)}")
    finally:
        if backend_path in sys.path:
            sys.path.remove(backend_path)
    
    return errors

if __name__ == "__main__":
    # Test the system on the CRM backend
    backend_path = '/Users/shanjairaj/local-projects/projects/want-crm-web-application-0808-105000/backend'
    errors = run_enterprise_error_check(backend_path)

    print(f'\n🔍 ENTERPRISE ERROR CHECK RESULTS:')
    print(f'Found {len(errors)} critical errors:\n')

    for i, error in enumerate(errors, 1):
        print(f'{i}. {error}')

    if not errors:
        print('✅ NO ERRORS FOUND - Backend is ready to run!')
    else:
        print(f'\n❌ CRITICAL: {len(errors)} errors must be fixed before starting preview')