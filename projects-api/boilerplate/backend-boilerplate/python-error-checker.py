#!/usr/bin/env python3
"""
Real-time Python error checker for bolt.diy VPS backend
Similar to ts-error-checker.js but for Python files
"""

import ast
import py_compile
import tempfile
import subprocess
import time
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import importlib.util
import os

class PythonErrorChecker:
    """Real-time Python error detection for backend files"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        # If we're already in the backend directory (like in Docker), use current directory
        if (Path(project_path) / "app.py").exists():
            self.backend_path = Path(project_path)
        else:
            self.backend_path = self.project_path / "backend"
        self.error_file = self.backend_path / ".python-errors.txt"
        
        # Track last modification times
        self.last_checked = {}
        
    def check_syntax_errors(self, content: str, file_path: str) -> List[str]:
        """Check for Python syntax errors using ast.parse"""
        errors = []
        
        try:
            ast.parse(content, filename=file_path)
        except SyntaxError as e:
            errors.append(f"{file_path}:{e.lineno}:{e.offset or 0} - Syntax Error: {e.msg}")
        except Exception as e:
            errors.append(f"{file_path}:1:0 - Parse Error: {str(e)}")
        
        return errors
    
    def check_compilation_errors(self, content: str, file_path: str) -> List[str]:
        """Check for Python compilation errors using py_compile"""
        errors = []
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            py_compile.compile(tmp_path, doraise=True)
        except py_compile.PyCompileError as e:
            error_msg = str(e)
            # Extract line number if available
            match = re.search(r'line (\d+)', error_msg)
            line_num = match.group(1) if match else "1"
            errors.append(f"{file_path}:{line_num}:0 - Compile Error: {error_msg}")
        except Exception as e:
            errors.append(f"{file_path}:1:0 - Compilation Error: {str(e)}")
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)
        
        return errors
    
    
    def check_import_errors(self, content: str, file_path: str) -> List[str]:
        """Check for basic import issues"""
        errors = []
        warnings = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if module_name.startswith('.') and not self._is_valid_relative_import(module_name, file_path):
                            warnings.append(f"{file_path}:{node.lineno}:0 - Warning: Relative import '{module_name}' may not resolve correctly")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('.'):
                        if not self._is_valid_relative_import(node.module, file_path):
                            warnings.append(f"{file_path}:{node.lineno}:0 - Warning: Relative import from '{node.module}' may not resolve correctly")
        
        except Exception:
            pass  # Syntax errors will be caught by check_syntax_errors
        
        return errors + warnings
    
    def _is_valid_relative_import(self, module_name: str, file_path: str) -> bool:
        """Basic check if relative import might be valid"""
        # Very basic check - in a real implementation you'd check the actual file structure
        return True  # Skip complex validation for now
    
    def check_file(self, file_path: Path) -> List[str]:
        """Check a single Python file for all types of errors"""
        if not file_path.exists() or not file_path.suffix == '.py':
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return [f"{file_path}:1:0 - File Error: Cannot read file - {str(e)}"]
        
        all_errors = []
        
        # Check for different types of errors
        all_errors.extend(self.check_syntax_errors(content, str(file_path)))
        all_errors.extend(self.check_compilation_errors(content, str(file_path)))
        all_errors.extend(self.check_import_errors(content, str(file_path)))
        
        return all_errors
    
    def scan_backend_files(self) -> Dict[str, List[str]]:
        """Scan all Python files in the backend directory"""
        all_errors = {}
        
        if not self.backend_path.exists():
            return all_errors
        
        # Find all Python files
        python_files = list(self.backend_path.rglob("*.py"))
        
        for file_path in python_files:
            # Skip __pycache__ and other temporary files
            if '__pycache__' in str(file_path) or file_path.name.startswith('.'):
                continue
            
            # Check if file was modified since last check
            try:
                mtime = file_path.stat().st_mtime
                if str(file_path) in self.last_checked and self.last_checked[str(file_path)] >= mtime:
                    continue  # Skip unchanged files
                
                self.last_checked[str(file_path)] = mtime
            except Exception:
                pass
            
            errors = self.check_file(file_path)
            if errors:
                all_errors[str(file_path)] = errors
        
        return all_errors
    
    def format_error_report(self, errors: Dict[str, List[str]], target_file: str = None) -> str:
        """Format error report as a clean string for model feedback"""
        if not errors:
            return "No Python errors found"
        
        # If checking a specific file, only show errors for that file
        if target_file:
            file_errors = errors.get(target_file, [])
            if not file_errors:
                return ""
            
            report_lines = ["Python validation errors:"]
            for error in file_errors:
                # Extract just the error message part (after the file:line:col prefix)
                if " - " in error:
                    error_msg = error.split(" - ", 1)[1]
                    report_lines.append(f"- {error_msg}")
                else:
                    report_lines.append(f"- {error}")
        else:
            # Show all errors
            report_lines = ["Python validation errors:"]
            for file_path, file_errors in errors.items():
                for error in file_errors:
                    if " - " in error:
                        error_msg = error.split(" - ", 1)[1]
                        report_lines.append(f"- {error_msg}")
                    else:
                        report_lines.append(f"- {error}")
        
        return "\n".join(report_lines)
    
    def check_single_file_and_format(self, file_path: str) -> str:
        """Check a single file and return formatted error report"""
        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.suffix == '.py':
            return ""
        
        errors = self.check_file(path_obj)
        if not errors:
            return ""
        
        # Create errors dict for formatting
        errors_dict = {file_path: errors}
        return self.format_error_report(errors_dict, file_path)
    
    def write_error_report(self, errors: Dict[str, List[str]]):
        """Write error report to file"""
        if not errors:
            # No errors - write success message
            self.error_file.write_text("No Python errors found\n")
            return
        
        report_lines = []
        total_errors = sum(len(file_errors) for file_errors in errors.values())
        
        report_lines.append(f"Python Error Report - {total_errors} issues found")
        report_lines.append("=" * 50)
        
        for file_path, file_errors in errors.items():
            report_lines.append(f"\n📁 {file_path}")
            for error in file_errors:
                report_lines.append(f"  ❌ {error}")
        
        report_lines.append(f"\nTotal: {total_errors} issues in {len(errors)} files")
        
        # Write to error file
        self.error_file.write_text("\n".join(report_lines))
    
    def run_continuous_check(self, interval: int = 2):
        """Run continuous error checking"""
        print(f"🐍 Python Error Checker started for: {self.backend_path}")
        print(f"📝 Writing errors to: {self.error_file}")
        print(f"🔄 Checking every {interval} seconds...")
        
        while True:
            try:
                errors = self.scan_backend_files()
                self.write_error_report(errors)
                
                if errors:
                    total_errors = sum(len(file_errors) for file_errors in errors.values())
                    print(f"❌ Found {total_errors} Python issues in {len(errors)} files")
                else:
                    print("✅ No Python errors found")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Python error checker stopped")
                break
            except Exception as e:
                print(f"❌ Error in checker: {e}")
                time.sleep(interval)

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    checker = PythonErrorChecker(project_path)
    
    # Run one-time check or continuous
    if "--once" in sys.argv:
        errors = checker.scan_backend_files()
        checker.write_error_report(errors)
        
        if errors:
            # Output clean error list for model consumption
            formatted_errors = checker.format_error_report(errors)
            print(formatted_errors)
            sys.exit(1)
        else:
            # No output for success (empty string is better for API)
            sys.exit(0)
    else:
        checker.run_continuous_check()

if __name__ == "__main__":
    main()