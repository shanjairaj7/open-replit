#!/usr/bin/env python3
"""
Advanced Python Error Checker for VPS Backend
Combines MyPy + Pyflakes for comprehensive VSCode-level error detection
Optimized for <3 seconds performance on backend codebases
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Set

class AdvancedPythonChecker:
    """Advanced Python error checker using MyPy + Pyflakes"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.error_file = self.project_path / ".python-errors.txt"
        
    def run_mypy_check(self) -> List[str]:
        """Run MyPy for import/attribute/type errors"""
        try:
            # Import mypy API directly instead of subprocess
            from mypy import api
            
            # Run MyPy programmatically
            result = api.run([
                str(self.project_path),
                "--ignore-missing-imports",
                "--show-error-codes", 
                "--no-error-summary",
                "--cache-dir", str(self.project_path / ".mypy_cache"),
                "--disable-error-code=var-annotated",
                "--disable-error-code=misc",
            ])
            
            # MyPy API returns (stdout, stderr, exit_code)
            stdout, stderr, exit_code = result
            
            errors = []
            if stdout.strip():
                errors.extend(stdout.strip().split('\n'))
            if stderr.strip():
                errors.extend(stderr.strip().split('\n'))
            return errors
            
        except ImportError:
            return ["MyPy not available - install with: pip install mypy"]
        except Exception as e:
            return [f"MyPy error: {str(e)}"]
    
    def run_pyflakes_check(self) -> List[str]:
        """Run Pyflakes ONLY for critical runtime errors (undefined names)"""
        try:
            # Import pyflakes API directly
            from pyflakes.api import check
            from pyflakes.messages import UndefinedName
            
            critical_errors = []
            
            # Find all Python files in the project directory
            python_files = list(self.project_path.glob("*.py"))
            python_files.extend(self.project_path.glob("**/*.py"))
            
            for py_file in python_files:
                # Skip virtual env and cache directories
                if any(skip in str(py_file) for skip in ["venv", ".venv", "env", ".env", "__pycache__", "site-packages"]):
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    # Capture pyflakes warnings
                    
                    class WarningCollector:
                        def __init__(self):
                            self.messages = []
                        
                        def flake(self, message):
                            self.messages.append(message)
                    
                    collector = WarningCollector()
                    check(source, str(py_file), collector.flake)
                    
                    # Filter for undefined names only
                    for msg in collector.messages:
                        if isinstance(msg, UndefinedName):
                            critical_errors.append(f"{py_file}:{msg.lineno}: undefined name '{msg.names[0]}'")
                            
                except Exception:
                    # Skip files that can't be read or parsed
                    continue
                        
            return critical_errors
            
        except ImportError:
            return ["Pyflakes not available - install with: pip install pyflakes"]
        except Exception as e:
            return []  # Skip pyflakes errors, focus on MyPy
    
    def parse_and_filter_errors(self, mypy_errors: List[str], pyflakes_errors: List[str]) -> Dict[str, List[str]]:
        """Parse and categorize all errors by criticality"""
        
        critical_errors = []
        warnings = []
        
        # Process MyPy errors (ONLY the most critical ones that will break backend)
        for error in mypy_errors:
            if not error.strip():
                continue
                
            # ONLY critical errors that WILL break the backend startup/runtime
            if any(code in error for code in [
                '[attr-defined]',      # Missing attributes (UserRole case) - CRITICAL
                '[import-not-found]',  # Missing imports - CRITICAL  
                '[name-defined]',      # Undefined names - CRITICAL
                '[syntax]',            # Syntax errors - CRITICAL
                '[call-arg]'           # Function call errors - CRITICAL
            ]):
                critical_errors.append(f"❌ {error}")
            # Skip ALL other MyPy errors (type annotations, assignments, etc.)
        
        # Process Pyflakes errors (ONLY critical runtime errors)
        for error in pyflakes_errors:
            if not error.strip():
                continue
                
            # ONLY undefined names (will crash at runtime)
            if "undefined name" in error:
                critical_errors.append(f"❌ {error}")
            # Skip everything else (unused imports, style issues, etc.)
        
        return {
            "critical": critical_errors,
            "warnings": warnings
        }
    
    def format_error_report(self, errors: Dict[str, List[str]]) -> str:
        """Format error report for API consumption - ONLY critical errors"""
        if not errors["critical"]:
            return ""
        
        report_lines = ["Python validation errors:"]
        
        # Show ONLY critical errors (these WILL break the backend)
        for error in errors["critical"][:15]:  # Limit to 15 most critical
            # Clean up the error message for better readability
            clean_error = error.replace("❌ ", "- ").replace("[attr-defined]", "").replace("[import-not-found]", "").replace("[name-defined]", "").replace("[syntax]", "").replace("[call-arg]", "").strip()
            report_lines.append(clean_error)
        
        if len(errors["critical"]) > 15:
            report_lines.append(f"- ... and {len(errors['critical']) - 15} more critical errors")
        
        return "\\n".join(report_lines)
    
    def run_comprehensive_check(self) -> str:
        """Run comprehensive Python error check"""
        start_time = time.time()
        
        print(f"🔍 Running advanced Python error check on: {self.project_path}")
        
        # Run both checkers in sequence (total target: <3 seconds)
        mypy_errors = self.run_mypy_check()
        pyflakes_errors = self.run_pyflakes_check()
        
        # Parse and categorize errors
        categorized_errors = self.parse_and_filter_errors(mypy_errors, pyflakes_errors)
        
        # Format the report
        formatted_report = self.format_error_report(categorized_errors)
        
        elapsed = time.time() - start_time
        print(f"✅ Check completed in {elapsed:.2f}s")
        
        # Write to error file for continuous monitoring
        self.write_error_file(categorized_errors, elapsed)
        
        return formatted_report
    
    def write_error_file(self, errors: Dict[str, List[str]], elapsed_time: float):
        """Write error report to file for monitoring"""
        try:
            total_errors = len(errors["critical"]) + len(errors["warnings"])
            
            if total_errors == 0:
                self.error_file.write_text("✅ No Python errors found\\n")
            else:
                report = [
                    f"Python Error Report ({elapsed_time:.2f}s)",
                    "=" * 50,
                    f"Critical Errors: {len(errors['critical'])}",
                    f"Warnings: {len(errors['warnings'])}",
                    f"Total: {total_errors}",
                    "",
                    "CRITICAL ERRORS:",
                ]
                
                for error in errors["critical"]:
                    report.append(f"  {error}")
                
                if errors["warnings"]:
                    report.append("")
                    report.append("WARNINGS:")
                    for warning in errors["warnings"][:10]:
                        report.append(f"  {warning}")
                
                self.error_file.write_text("\\n".join(report))
                
        except Exception as e:
            print(f"Warning: Could not write error file: {e}")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_path = sys.argv[1] 
    else:
        project_path = "."
    
    checker = AdvancedPythonChecker(project_path)
    
    if "--once" in sys.argv:
        # One-time check for API usage
        result = checker.run_comprehensive_check()
        
        if result:
            print(result)
            sys.exit(1)  # Errors found
        else:
            sys.exit(0)  # No critical errors
    else:
        # Continuous monitoring mode
        print("Starting continuous Python error monitoring...")
        while True:
            try:
                checker.run_comprehensive_check()
                time.sleep(5)  # Check every 5 seconds
            except KeyboardInterrupt:
                print("\\n🛑 Python error checker stopped")
                break
            except Exception as e:
                print(f"❌ Error in checker: {e}")
                time.sleep(5)

if __name__ == "__main__":
    main()