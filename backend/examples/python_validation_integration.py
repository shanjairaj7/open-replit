#!/usr/bin/env python3
"""
Examples of integrating Python validation into various workflows
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from app.services.python_validator import PythonValidator

class PythonFileWatcher(FileSystemEventHandler):
    """Watch for Python file changes and validate them"""
    
    def __init__(self):
        self.validator = PythonValidator
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('.py'):
            self.validate_file(event.src_path)
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('.py'):
            self.validate_file(event.src_path)
    
    def validate_file(self, file_path):
        """Validate a Python file and report errors"""
        print(f"\n🔍 Validating: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            errors = self.validator.validate_python_file(content, file_path)
            
            if errors:
                print("❌ Validation errors found:")
                for error in errors:
                    icon = "❌" if error['type'] == 'error' else "⚠️"
                    line_info = f" (line {error['line']})" if 'line' in error else ""
                    print(f"  {icon} {error['message']}{line_info}")
            else:
                print("✅ No errors found")
                
        except Exception as e:
            print(f"❌ Error reading file: {e}")

def setup_file_watcher(directory: str):
    """Set up a file watcher for Python files"""
    event_handler = PythonFileWatcher()
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    
    print(f"👀 Watching for Python file changes in: {directory}")
    print("Press Ctrl+C to stop...")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def create_pre_commit_hook():
    """Create a git pre-commit hook for Python validation"""
    hook_content = '''#!/usr/bin/env python3
"""
Git pre-commit hook for Python validation
"""

import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.python_validator import PythonValidator

def get_staged_python_files():
    """Get list of staged Python files"""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True,
        text=True
    )
    
    files = result.stdout.strip().split('\\n')
    return [f for f in files if f.endswith('.py')]

def main():
    """Validate staged Python files"""
    files = get_staged_python_files()
    
    if not files:
        return 0
    
    print("🐍 Validating Python files...")
    
    all_errors = {}
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            errors = PythonValidator.validate_python_file(content, file_path)
            if errors:
                all_errors[file_path] = errors
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 1
    
    if all_errors:
        report = PythonValidator.format_validation_report(all_errors)
        print(report)
        
        # Count actual errors (not warnings)
        error_count = sum(
            1 for errors in all_errors.values()
            for error in errors
            if error['type'] == 'error'
        )
        
        if error_count > 0:
            print(f"\\n❌ Commit blocked: {error_count} errors found")
            return 1
        else:
            print("\\n⚠️  Warnings found, but commit allowed")
            return 0
    else:
        print("✅ All Python files validated successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    # Save the hook
    hook_path = Path('.git/hooks/pre-commit')
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(hook_path, 'w') as f:
        f.write(hook_content)
    
    # Make it executable
    hook_path.chmod(0o755)
    
    print(f"✅ Pre-commit hook created at: {hook_path}")
    print("The hook will validate Python files before each commit")

def validate_project_files(project_dir: str):
    """Validate all Python files in a project"""
    print(f"🔍 Validating all Python files in: {project_dir}")
    
    python_files = {}
    
    # Collect all Python files
    for root, dirs, files in os.walk(project_dir):
        # Skip hidden directories and common exclude patterns
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        python_files[file_path] = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    print(f"Found {len(python_files)} Python files")
    
    # Validate all files
    all_errors = PythonValidator.validate_all_python_files(python_files, use_mypy=False)
    
    # Generate report
    report = PythonValidator.format_validation_report(all_errors)
    print("\n" + report)
    
    return all_errors

async def validate_on_save(file_path: str):
    """Async validation for integration with editors/IDEs"""
    print(f"🔍 Validating: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Run validation
        errors = PythonValidator.validate_python_file(content, file_path)
        
        # Return in a format suitable for editor integration
        return {
            'file': file_path,
            'diagnostics': [
                {
                    'severity': 'error' if e['type'] == 'error' else 'warning',
                    'line': e.get('line', 1) - 1,  # 0-indexed for editors
                    'column': e.get('column', 0),
                    'message': e['message'],
                    'source': 'python-validator'
                }
                for e in errors
            ]
        }
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e)
        }

def main():
    """Demonstrate different validation integration methods"""
    print("Python Validation Integration Examples")
    print("=" * 50)
    print("\n1. File Watcher Example")
    print("   Run: python python_validation_integration.py watch <directory>")
    print("\n2. Pre-commit Hook")
    print("   Run: python python_validation_integration.py install-hook")
    print("\n3. Project Validation")
    print("   Run: python python_validation_integration.py validate <directory>")
    print("\n4. Single File Validation")
    print("   Run: python python_validation_integration.py check <file.py>")
    
    if len(sys.argv) < 2:
        return
    
    command = sys.argv[1]
    
    if command == "watch" and len(sys.argv) > 2:
        setup_file_watcher(sys.argv[2])
    
    elif command == "install-hook":
        create_pre_commit_hook()
    
    elif command == "validate" and len(sys.argv) > 2:
        validate_project_files(sys.argv[2])
    
    elif command == "check" and len(sys.argv) > 2:
        # Single file validation
        file_path = sys.argv[2]
        result = asyncio.run(validate_on_save(file_path))
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"File: {result['file']}")
            if result['diagnostics']:
                for diag in result['diagnostics']:
                    icon = "❌" if diag['severity'] == 'error' else "⚠️"
                    print(f"  {icon} Line {diag['line'] + 1}: {diag['message']}")
            else:
                print("  ✅ No issues found")

if __name__ == "__main__":
    main()