#!/usr/bin/env python3

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path
import importlib.util

# Import the real error checker
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/projects-api')
spec = importlib.util.spec_from_file_location("local_api", "/Users/shanjairaj/Documents/forks/bolt.diy/projects-api/local-api.py")
local_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_api)

class IntensiveErrorTester:
    def __init__(self):
        self.project_id = "want-crm-web-application-0808-152839"
        self.backend_path = Path(f"/Users/shanjairaj/local-projects/projects/{self.project_id}/backend")
        self.project_manager = local_api.LocalProjectManager()
        self.test_results = []
        
    def run_error_check(self):
        """Run the actual error checker"""
        try:
            result = self.project_manager._run_python_error_check(self.project_id)
            return result['status']['success'], result['errors']
        except Exception as e:
            return False, f"Error checker crashed: {str(e)}"
    
    def create_test_file(self, filename, content):
        """Create a test file"""
        filepath = self.backend_path / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath
    
    def remove_test_file(self, filepath):
        """Remove test file"""
        try:
            filepath.unlink()
        except:
            pass
    
    def test_case(self, name, test_func):
        """Run a test case"""
        print(f"\n🧪 TEST CASE: {name}")
        print("-" * 60)
        
        success, errors = test_func()
        
        self.test_results.append({
            'name': name,
            'success': success,
            'errors': errors
        })
        
        print(f"✅ Success: {success}")
        print(f"📋 Errors: {errors[:200]}..." if len(str(errors)) > 200 else f"📋 Errors: {errors}")
        
        return success, errors
    
    def test_1_syntax_error(self):
        """Test: Syntax Error Detection"""
        test_file = self.create_test_file("test_syntax_error.py", """
# This file has a syntax error
def broken_function(
    # Missing closing parenthesis and colon
    print("This should cause a syntax error")
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def test_2_missing_import(self):
        """Test: Missing Import Detection"""
        test_file = self.create_test_file("test_missing_import.py", """
# This imports a non-existent module
import nonexistent_module_12345
from completely_fake_package import something

def test_function():
    return nonexistent_module_12345.do_something()
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def test_3_missing_dependency(self):
        """Test: Missing Dependency Detection"""
        # First, let's break a real dependency by removing it
        venv_python = self.backend_path / "venv" / "bin" / "python"
        if venv_python.exists():
            # Uninstall fastapi temporarily
            subprocess.run([str(venv_python), "-m", "pip", "uninstall", "-y", "fastapi"], capture_output=True)
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            # Reinstall fastapi
            if venv_python.exists():
                subprocess.run([str(venv_python), "-m", "pip", "install", "fastapi>=0.115.0"], capture_output=True)
    
    def test_4_circular_import(self):
        """Test: Circular Import Detection"""
        test_file1 = self.create_test_file("test_circular_a.py", """
# Circular import A -> B -> A
from test_circular_b import function_b

def function_a():
    return function_b()
""")
        
        test_file2 = self.create_test_file("test_circular_b.py", """
# Circular import B -> A -> B
from test_circular_a import function_a

def function_b():
    return function_a()
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file1)
            self.remove_test_file(test_file2)
    
    def test_5_runtime_error(self):
        """Test: Runtime Error Detection"""
        test_file = self.create_test_file("test_runtime_error.py", """
# This will cause a runtime error during import
print("Starting import...")

# Division by zero at module level
result = 1 / 0

print("This should not be reached")
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def test_6_missing_file_import(self):
        """Test: Import from Missing File"""
        test_file = self.create_test_file("test_missing_file.py", """
# Try to import from a file that doesn't exist
from missing_file_12345 import some_function
from models.nonexistent_model import SomeClass

def test():
    return some_function()
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def test_7_indentation_error(self):
        """Test: Indentation Error Detection"""
        test_file = self.create_test_file("test_indentation.py", """
# This has indentation errors
def my_function():
print("This line is not indented properly")
    if True:
print("This is also wrong")
        return False
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def test_8_app_py_corruption(self):
        """Test: Main app.py Import Failure"""
        # Backup original app.py
        app_py = self.backend_path / "app.py"
        backup_content = ""
        if app_py.exists():
            with open(app_py, 'r') as f:
                backup_content = f.read()
        
        # Create corrupted app.py
        corrupted_content = """
# Corrupted app.py that will fail to load
from nonexistent_framework import NonExistentClass
import missing_module

# Create app with missing dependencies
app = NonExistentClass()
"""
        
        with open(app_py, 'w') as f:
            f.write(corrupted_content)
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            # Restore original app.py
            with open(app_py, 'w') as f:
                f.write(backup_content)
    
    def test_9_valid_code(self):
        """Test: Valid Code Should Pass"""
        test_file = self.create_test_file("test_valid_code.py", """
# This is valid Python code
import json
import os
from datetime import datetime

def valid_function():
    data = {
        "timestamp": datetime.now().isoformat(),
        "status": "working"
    }
    return json.dumps(data)

class ValidClass:
    def __init__(self):
        self.value = os.getcwd()
    
    def get_value(self):
        return self.value
""")
        
        try:
            success, errors = self.run_error_check()
            return success, errors
        finally:
            self.remove_test_file(test_file)
    
    def run_all_tests(self):
        """Run all intensive tests"""
        print("🚀 INTENSIVE ERROR CHECKER TESTING")
        print("=" * 80)
        print(f"Testing project: {self.project_id}")
        print(f"Backend path: {self.backend_path}")
        
        # Test cases that SHOULD FAIL (detect errors)
        failing_tests = [
            ("Syntax Error Detection", self.test_1_syntax_error),
            ("Missing Import Detection", self.test_2_missing_import),
            ("Missing Dependency Detection", self.test_3_missing_dependency),
            ("Circular Import Detection", self.test_4_circular_import),
            ("Runtime Error Detection", self.test_5_runtime_error),
            ("Missing File Import Detection", self.test_6_missing_file_import),
            ("Indentation Error Detection", self.test_7_indentation_error),
            ("App.py Corruption Detection", self.test_8_app_py_corruption),
        ]
        
        # Test cases that SHOULD PASS (no errors)
        passing_tests = [
            ("Valid Code Should Pass", self.test_9_valid_code),
        ]
        
        print("\n📋 TESTING ERROR DETECTION (These should FAIL with errors found):")
        for name, test_func in failing_tests:
            success, errors = self.test_case(name, test_func)
            if success:  # If no errors found, that's bad for error detection tests
                print(f"⚠️  WARNING: {name} should have found errors but didn't!")
            else:
                print(f"✅ GOOD: {name} correctly found errors")
        
        print("\n📋 TESTING VALID CODE (These should PASS with no errors):")
        for name, test_func in passing_tests:
            success, errors = self.test_case(name, test_func)
            if not success:  # If errors found in valid code, that's bad
                print(f"⚠️  WARNING: {name} found errors in valid code!")
            else:
                print(f"✅ GOOD: {name} correctly passed valid code")
        
        # Summary
        print("\n📊 SUMMARY")
        print("=" * 80)
        total_tests = len(self.test_results)
        error_detection_tests = len(failing_tests)
        valid_code_tests = len(passing_tests)
        
        correct_error_detections = sum(1 for r in self.test_results[:error_detection_tests] if not r['success'])
        correct_passes = sum(1 for r in self.test_results[error_detection_tests:] if r['success'])
        
        print(f"Total tests run: {total_tests}")
        print(f"Error detection tests: {error_detection_tests} (should fail)")
        print(f"Valid code tests: {valid_code_tests} (should pass)")
        print(f"Correct error detections: {correct_error_detections}/{error_detection_tests}")
        print(f"Correct passes: {correct_passes}/{valid_code_tests}")
        
        overall_success = (correct_error_detections == error_detection_tests) and (correct_passes == valid_code_tests)
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED! Error checker is working correctly!")
        else:
            print("\n❌ SOME TESTS FAILED! Error checker needs fixes!")
        
        return overall_success

if __name__ == "__main__":
    tester = IntensiveErrorTester()
    tester.run_all_tests()