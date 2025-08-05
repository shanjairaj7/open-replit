import ast
import py_compile
import tempfile
import subprocess
import sys
import re
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PythonValidator:
    """Service to validate Python code for syntax and import errors"""
    
    @classmethod
    def validate_syntax(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Validate Python syntax using ast.parse"""
        errors = []
        
        try:
            # Try to parse the Python code
            ast.parse(content, filename=file_path)
        except SyntaxError as e:
            errors.append({
                'type': 'error',
                'file': file_path,
                'line': e.lineno or 1,
                'column': e.offset,
                'message': f'Syntax Error: {e.msg}'
            })
        except Exception as e:
            errors.append({
                'type': 'error',
                'file': file_path,
                'message': f'Parse Error: {str(e)}'
            })
        
        return errors
    
    @classmethod
    def validate_with_py_compile(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Validate Python using py_compile module"""
        errors = []
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Try to compile the file
            py_compile.compile(tmp_path, doraise=True)
        except py_compile.PyCompileError as e:
            # Extract error details from the exception message
            error_msg = str(e)
            match = re.search(r'line (\d+)', error_msg)
            line_num = int(match.group(1)) if match else 1
            
            errors.append({
                'type': 'error',
                'file': file_path,
                'line': line_num,
                'message': f'Compile Error: {error_msg}'
            })
        except Exception as e:
            errors.append({
                'type': 'error',
                'file': file_path,
                'message': f'Compilation Error: {str(e)}'
            })
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)
        
        return errors
    
    @classmethod
    def validate_imports(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Check for potentially problematic imports"""
        errors = []
        warnings = []
        
        # Parse the AST to find all imports
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        line_num = node.lineno
                        
                        # Check if module can be imported (basic check)
                        if not cls._is_standard_module(module_name):
                            warnings.append({
                                'type': 'warning',
                                'file': file_path,
                                'line': line_num,
                                'message': f'Import "{module_name}" may not be available in runtime environment'
                            })
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ''
                    line_num = node.lineno
                    
                    # Check relative imports
                    if node.level > 0:  # Relative import
                        warnings.append({
                            'type': 'warning',
                            'file': file_path,
                            'line': line_num,
                            'message': f'Relative import ({"." * node.level}{module_name}) may cause issues'
                        })
                    elif not cls._is_standard_module(module_name):
                        warnings.append({
                            'type': 'warning',
                            'file': file_path,
                            'line': line_num,
                            'message': f'Import from "{module_name}" may not be available in runtime environment'
                        })
        
        except:
            # If AST parsing fails, we already caught it in validate_syntax
            pass
        
        return errors + warnings
    
    @classmethod
    def validate_pydantic_models(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Validate Pydantic model definitions"""
        errors = []
        
        # Check if file uses Pydantic
        if 'from pydantic' not in content and 'import pydantic' not in content:
            return errors
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Pydantic model
                    is_pydantic = False
                    for base in node.bases:
                        if isinstance(base, ast.Name) and 'Model' in base.id:
                            is_pydantic = True
                        elif isinstance(base, ast.Attribute) and 'Model' in base.attr:
                            is_pydantic = True
                    
                    if is_pydantic:
                        # Check for common Pydantic issues
                        cls._check_pydantic_class(node, file_path, errors)
        
        except:
            pass
        
        return errors
    
    @classmethod
    def _check_pydantic_class(cls, class_node: ast.ClassDef, file_path: str, errors: List[Dict[str, any]]):
        """Check for common Pydantic model issues"""
        has_fields = False
        
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign):  # Type annotated assignment
                has_fields = True
                
                # Check for mutable defaults
                if item.value and isinstance(item.value, (ast.List, ast.Dict, ast.Set)):
                    errors.append({
                        'type': 'error',
                        'file': file_path,
                        'line': item.lineno,
                        'message': f'Mutable default value in Pydantic model "{class_node.name}". Use Field(default_factory=...)'
                    })
        
        if not has_fields:
            errors.append({
                'type': 'warning',
                'file': file_path,
                'line': class_node.lineno,
                'message': f'Pydantic model "{class_node.name}" has no fields defined'
            })
    
    @classmethod
    def validate_with_mypy(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Run mypy for type checking (if available)"""
        errors = []
        
        # Check if mypy is available
        try:
            subprocess.run(['mypy', '--version'], capture_output=True, check=True)
        except:
            return []  # mypy not available
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Run mypy
            result = subprocess.run(
                ['mypy', '--no-error-summary', '--no-color-output', tmp_path],
                capture_output=True,
                text=True
            )
            
            # Parse mypy output
            for line in result.stdout.splitlines():
                if ':' in line:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            error_type = parts[2].strip()
                            message = parts[3].strip()
                            
                            errors.append({
                                'type': 'warning' if 'note' in error_type else 'error',
                                'file': file_path,
                                'line': line_num,
                                'message': f'Type Error: {message}'
                            })
                        except:
                            pass
        
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        
        return errors
    
    @classmethod
    def _is_standard_module(cls, module_name: str) -> bool:
        """Check if module is a Python standard library module"""
        # Common standard library modules
        standard_modules = {
            'os', 'sys', 'json', 'datetime', 'time', 're', 'math', 'random',
            'collections', 'itertools', 'functools', 'typing', 'pathlib',
            'logging', 'asyncio', 'threading', 'subprocess', 'io', 'csv',
            'sqlite3', 'urllib', 'http', 'email', 'unittest', 'tempfile',
            'shutil', 'glob', 'pickle', 'base64', 'hashlib', 'uuid', 'copy',
            'dataclasses', 'enum', 'abc', 'contextlib', 'decimal', 'fractions'
        }
        
        # Check if it's a standard module or starts with a standard module
        base_module = module_name.split('.')[0]
        return base_module in standard_modules
    
    @classmethod
    def validate_python_file(cls, content: str, file_path: str, use_mypy: bool = False) -> List[Dict[str, any]]:
        """Comprehensive Python file validation"""
        all_errors = []
        
        # 1. Basic syntax validation
        all_errors.extend(cls.validate_syntax(content, file_path))
        
        # If syntax is valid, perform additional checks
        if not any(e['type'] == 'error' for e in all_errors):
            # 2. Compile validation
            all_errors.extend(cls.validate_with_py_compile(content, file_path))
            
            # 3. Import validation
            all_errors.extend(cls.validate_imports(content, file_path))
            
            # 4. Pydantic model validation
            all_errors.extend(cls.validate_pydantic_models(content, file_path))
            
            # 5. Type checking with mypy (optional)
            if use_mypy:
                all_errors.extend(cls.validate_with_mypy(content, file_path))
        
        return all_errors
    
    @classmethod
    def validate_all_python_files(cls, files: Dict[str, str], use_mypy: bool = False) -> Dict[str, List[Dict[str, any]]]:
        """Validate all Python files in the project"""
        all_errors = {}
        
        for file_path, content in files.items():
            if file_path.endswith('.py'):
                errors = cls.validate_python_file(content, file_path, use_mypy)
                if errors:
                    all_errors[file_path] = errors
        
        return all_errors
    
    @classmethod
    def format_validation_report(cls, errors: Dict[str, List[Dict[str, any]]]) -> str:
        """Format Python validation errors into a readable report"""
        if not errors:
            return "✅ No Python validation errors found!"
        
        report = "🐍 Python Validation Report:\n\n"
        
        error_count = 0
        warning_count = 0
        
        for file_path, file_errors in errors.items():
            report += f"📄 {file_path}:\n"
            for error in file_errors:
                icon = "❌" if error['type'] == 'error' else "⚠️"
                
                if error['type'] == 'error':
                    error_count += 1
                else:
                    warning_count += 1
                
                line_info = f" (line {error['line']})" if 'line' in error else ""
                col_info = f":{error['column']}" if 'column' in error else ""
                report += f"  {icon} {error['message']}{line_info}{col_info}\n"
            report += "\n"
        
        # Summary
        report += f"Summary: {error_count} errors, {warning_count} warnings\n"
        
        return report