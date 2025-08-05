# Python Validation Guide

This guide covers various methods to detect Python syntax and import errors in real-time, including validation before runtime.

## Available Validation Methods

### 1. **ast.parse() - Abstract Syntax Tree Parsing**
- **Speed**: Very fast
- **What it catches**: Syntax errors, invalid Python constructs
- **Usage**:
```python
import ast

try:
    ast.parse(code_content, filename='example.py')
    print("✅ Syntax is valid")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")
```

### 2. **py_compile - Python Bytecode Compilation**
- **Speed**: Fast
- **What it catches**: Syntax errors, some semantic errors
- **Usage**:
```python
import py_compile
import tempfile

with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as tmp:
    tmp.write(code_content)
    tmp.flush()
    try:
        py_compile.compile(tmp.name, doraise=True)
        print("✅ Code compiles successfully")
    except py_compile.PyCompileError as e:
        print(f"❌ Compilation error: {e}")
```

### 3. **Static Analysis Tools**

#### **pylint**
- **Installation**: `pip install pylint`
- **What it catches**: Code style, errors, warnings, refactoring suggestions
- **Usage**:
```bash
pylint myfile.py
```

#### **flake8**
- **Installation**: `pip install flake8`
- **What it catches**: PEP8 violations, syntax errors, undefined names
- **Usage**:
```bash
flake8 myfile.py
```

#### **mypy**
- **Installation**: `pip install mypy`
- **What it catches**: Type errors, missing imports, incorrect function calls
- **Usage**:
```bash
mypy myfile.py
```

### 4. **Pydantic Model Validation**
For projects using Pydantic, you can validate model definitions:

```python
from pydantic import BaseModel, ValidationError

# Check for common issues:
# - Mutable defaults (lists, dicts as default values)
# - Missing required fields
# - Invalid type annotations
```

## Integration Examples

### File Watcher
Monitor Python files for changes and validate automatically:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PythonValidator(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Validate the file
            validate_python_file(event.src_path)
```

### Pre-commit Hook
Validate Python files before git commits:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Get staged Python files
files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

# Validate each file
for file in $files; do
    python -m py_compile "$file" || exit 1
    pylint "$file" || exit 1
done
```

### Editor Integration
Most editors support Language Server Protocol (LSP) for real-time validation:

- **VS Code**: Python extension with Pylance
- **Vim**: Use ALE or coc.nvim with Python language servers
- **Emacs**: Use lsp-mode or flycheck

### CI/CD Integration
Add validation to your continuous integration pipeline:

```yaml
# GitHub Actions example
- name: Validate Python syntax
  run: |
    python -m py_compile **/*.py
    flake8 . --count --exit-zero --max-complexity=10
    mypy . --ignore-missing-imports
```

## Using the PythonValidator Class

The `PythonValidator` class in `app/services/python_validator.py` provides comprehensive validation:

```python
from app.services.python_validator import PythonValidator

# Validate a single file
content = open('myfile.py').read()
errors = PythonValidator.validate_python_file(content, 'myfile.py')

# Validate all Python files in a project
files = {'file1.py': content1, 'file2.py': content2}
all_errors = PythonValidator.validate_all_python_files(files)

# Generate a report
report = PythonValidator.format_validation_report(all_errors)
print(report)
```

## Common Python Errors Detected

1. **Syntax Errors**
   - Missing colons after function/class definitions
   - Incorrect indentation
   - Unmatched parentheses/brackets
   - Invalid Python keywords

2. **Import Errors**
   - Missing modules
   - Circular imports
   - Invalid relative imports
   - Typos in module names

3. **Type Errors** (with mypy)
   - Incorrect argument types
   - Missing return statements
   - Undefined variables
   - Incompatible assignments

4. **Pydantic Specific**
   - Mutable default values
   - Missing type annotations
   - Invalid field definitions
   - Circular model dependencies

## Best Practices

1. **Layer Your Validation**
   - Use `ast.parse()` for quick syntax checks during editing
   - Run `py_compile` before saving files
   - Use static analyzers in pre-commit hooks
   - Run comprehensive checks in CI/CD

2. **Configure Tools Appropriately**
   - Create `.pylintrc` for project-specific rules
   - Use `.flake8` to ignore specific warnings
   - Configure `mypy.ini` for type checking settings

3. **Automate Where Possible**
   - Set up file watchers for immediate feedback
   - Use editor integrations for real-time validation
   - Add pre-commit hooks to catch errors before commits
   - Include validation in your build process

4. **Handle Errors Gracefully**
   - Distinguish between errors and warnings
   - Provide clear, actionable error messages
   - Allow commits with warnings but block on errors
   - Log validation results for debugging

## Example Output

```
🐍 Python Validation Report:

📄 src/models/user.py:
  ❌ Syntax Error: invalid syntax (line 45:12)
  ⚠️ Import "requests" may not be available in runtime environment (line 3)
  ❌ Mutable default value in Pydantic model "User". Use Field(default_factory=...) (line 23)

📄 src/utils/helpers.py:
  ⚠️ Type Error: Incompatible return value type (line 67)

Summary: 2 errors, 2 warnings
```