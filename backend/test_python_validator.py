#!/usr/bin/env python3
"""
Test script to demonstrate Python validation capabilities
"""

from app.services.python_validator import PythonValidator

def test_syntax_errors():
    """Test detection of syntax errors"""
    print("🧪 Testing Syntax Error Detection\n")
    
    # Test 1: Missing colon
    code1 = """
def hello_world()
    print("Hello, World!")
"""
    
    # Test 2: Unmatched parentheses
    code2 = """
def calculate(a, b):
    result = (a + b * 2
    return result
"""
    
    # Test 3: Invalid indentation
    code3 = """
def process_data():
    x = 10
        y = 20  # Wrong indentation
    return x + y
"""
    
    test_cases = [
        ("missing_colon.py", code1),
        ("unmatched_parens.py", code2),
        ("bad_indent.py", code3)
    ]
    
    for filename, code in test_cases:
        errors = PythonValidator.validate_syntax(code, filename)
        if errors:
            print(f"❌ {filename}:")
            for error in errors:
                print(f"   Line {error.get('line', '?')}: {error['message']}")
        print()

def test_import_errors():
    """Test detection of import issues"""
    print("🧪 Testing Import Validation\n")
    
    # Test with various imports
    code = """
import os  # Standard library - OK
import numpy as np  # External library - Warning
from datetime import datetime  # Standard library - OK
from my_module import custom_function  # Custom module - Warning
from ..parent import something  # Relative import - Warning
import non_existent_module  # Unknown module - Warning
"""
    
    errors = PythonValidator.validate_imports(code, "imports_test.py")
    if errors:
        print("Import warnings:")
        for error in errors:
            print(f"   Line {error.get('line', '?')}: {error['message']}")
    print()

def test_pydantic_validation():
    """Test Pydantic model validation"""
    print("🧪 Testing Pydantic Model Validation\n")
    
    # Test 1: Mutable default
    code1 = """
from pydantic import BaseModel

class UserModel(BaseModel):
    name: str
    tags: list = []  # Mutable default - Error!
    scores: dict = {}  # Mutable default - Error!
"""
    
    # Test 2: Empty model
    code2 = """
from pydantic import BaseModel

class EmptyModel(BaseModel):
    pass  # No fields - Warning!
"""
    
    # Test 3: Correct model
    code3 = """
from pydantic import BaseModel, Field
from typing import List, Dict

class CorrectModel(BaseModel):
    name: str
    tags: List[str] = Field(default_factory=list)
    scores: Dict[str, int] = Field(default_factory=dict)
"""
    
    test_cases = [
        ("mutable_defaults.py", code1),
        ("empty_model.py", code2),
        ("correct_model.py", code3)
    ]
    
    for filename, code in test_cases:
        errors = PythonValidator.validate_pydantic_models(code, filename)
        if errors:
            print(f"📋 {filename}:")
            for error in errors:
                print(f"   Line {error.get('line', '?')}: {error['message']}")
        else:
            print(f"✅ {filename}: No issues found")
        print()

def test_comprehensive_validation():
    """Test comprehensive validation on a complete file"""
    print("🧪 Testing Comprehensive Validation\n")
    
    # A file with multiple issues
    code = """
from pydantic import BaseModel
import requests  # External dependency
from ..utils import helper  # Relative import

class APIConfig(BaseModel):
    endpoint: str
    headers: dict = {}  # Mutable default
    
def fetch_data(config: APIConfig)  # Missing colon
    try:
        response = requests.get(config.endpoint)
        return response.json()
    except Exception as e
        print(f"Error: {e}")  # Missing colon
        
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, items):
        for item in items:
            if item.valid:  # Attribute might not exist
                self.data.append(item
        return self.data  # Missing closing parenthesis
"""
    
    errors = PythonValidator.validate_python_file(code, "complex_file.py")
    
    # Format and print report
    report = PythonValidator.format_validation_report({"complex_file.py": errors})
    print(report)

def test_valid_code():
    """Test validation on valid code"""
    print("🧪 Testing Valid Code\n")
    
    code = """
import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Configuration:
    name: str
    value: int
    enabled: bool = True

def load_config(path: str) -> Optional[Configuration]:
    \"\"\"Load configuration from file\"\"\"
    if not os.path.exists(path):
        return None
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return Configuration(**data)

def process_items(items: List[Dict[str, any]]) -> int:
    \"\"\"Process a list of items\"\"\"
    count = 0
    for item in items:
        if item.get('active', False):
            count += 1
    return count
"""
    
    errors = PythonValidator.validate_python_file(code, "valid_code.py")
    report = PythonValidator.format_validation_report({"valid_code.py": errors} if errors else {})
    print(report)

def main():
    """Run all tests"""
    print("=" * 60)
    print("Python Code Validator Demonstration")
    print("=" * 60)
    print()
    
    test_syntax_errors()
    test_import_errors()
    test_pydantic_validation()
    test_comprehensive_validation()
    test_valid_code()
    
    print("\n" + "=" * 60)
    print("Validation Methods Available:")
    print("=" * 60)
    print("1. ast.parse() - Fast syntax validation")
    print("2. py_compile - Bytecode compilation check")
    print("3. Import analysis - Detect missing dependencies")
    print("4. Pydantic validation - Model-specific checks")
    print("5. mypy integration - Optional type checking")
    print()
    print("Usage in code:")
    print("  errors = PythonValidator.validate_python_file(content, filename)")
    print("  report = PythonValidator.format_validation_report(all_errors)")

if __name__ == "__main__":
    main()