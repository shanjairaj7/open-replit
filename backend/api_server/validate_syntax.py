#!/usr/bin/env python3
"""
Comprehensive Python Syntax Validator
Checks all Python files for syntax errors and provides detailed error reports.
"""

import ast
import sys
from pathlib import Path

def validate_file(file_path: Path) -> tuple[bool, str]:
    """Validate a single Python file for syntax errors"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        ast.parse(content, filename=str(file_path))
        return True, "✅ OK"
        
    except SyntaxError as e:
        error_msg = f"❌ SyntaxError: {e.msg}"
        if hasattr(e, 'lineno'):
            error_msg += f" (line {e.lineno})"
        return False, error_msg
    except Exception as e:
        return False, f"❌ Error: {e}"

def main():
    """Main validation function"""
    print("🔍 Python Syntax Validator")
    print("=" * 50)
    
    current_dir = Path(".")
    python_files = list(current_dir.glob("*.py"))
    
    print(f"📁 Found {len(python_files)} Python files\n")
    
    valid_files = 0
    invalid_files = 0
    
    for file_path in sorted(python_files):
        is_valid, message = validate_file(file_path)
        print(f"{file_path.name:25} {message}")
        
        if is_valid:
            valid_files += 1
        else:
            invalid_files += 1
    
    print("\n📊 Summary:")
    print(f"Valid files:   {valid_files}")
    print(f"Invalid files: {invalid_files}")
    print(f"Total files:   {len(python_files)}")
    
    if invalid_files > 0:
        print(f"\n⚠️  {invalid_files} files have syntax errors!")
        sys.exit(1)
    else:
        print(f"\n✅ All files are syntactically valid!")
        sys.exit(0)

if __name__ == "__main__":
    main()