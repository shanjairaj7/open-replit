import re
import json
from typing import Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CodeValidator:
    """Service to validate code before preview"""
    
    # Common Tailwind classes that are valid
    VALID_TAILWIND_PATTERNS = [
        r'^(m|p|w|h|text|bg|border|rounded|flex|grid|gap|space|absolute|relative|fixed|z|opacity|shadow|transition|transform|scale|rotate|translate|skew|origin|animate|cursor|select|resize|scroll|overflow|object|align|justify|items|content|self|place|font|leading|tracking|break|whitespace|list|decoration|outline|ring|divide|placeholder|sr|not-sr|disabled|group|peer|focus|hover|active|visited|target|first|last|odd|even|first-of-type|last-of-type|only|only-of-type|empty|enabled|checked|indeterminate|default|required|valid|invalid|in-range|out-of-range|placeholder-shown|autofill|read-only|lg|md|sm|xl|2xl|min|max|dark|motion-safe|motion-reduce|print|rtl|ltr|open)[-:]',
        r'^(container|prose|aspect|columns|break-after|break-before|break-inside|box|clear|float|isolate|mix-blend|backdrop)[-:]?',
        r'^(blur|brightness|contrast|drop-shadow|grayscale|hue-rotate|invert|saturate|sepia)[-:]?',
    ]
    
    # Common TypeScript/React errors to check
    TS_ERROR_PATTERNS = [
        (r'useState\s*\(\s*\)', "useState requires an initial value or undefined"),
        (r'useEffect\s*\(\s*\)', "useEffect requires at least one argument"),
        (r'import\s+{[^}]*}\s+from\s+[\'"][^\'"]+[\'"](?!;)', "Missing semicolon after import"),
        (r'export\s+default\s+function\s+\w+\s*\(\s*\)\s*{', "Consider adding return type for function"),
    ]
    
    @classmethod
    def validate_typescript(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Validate TypeScript/JSX/TSX files"""
        errors = []
        
        # Check for common TypeScript errors
        for pattern, message in cls.TS_ERROR_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append({
                    'type': 'warning',
                    'file': file_path,
                    'line': line_num,
                    'message': message
                })
        
        # Check for unmatched brackets
        bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
        for open_b, close_b in bracket_pairs:
            open_count = content.count(open_b)
            close_count = content.count(close_b)
            if open_count != close_count:
                errors.append({
                    'type': 'error',
                    'file': file_path,
                    'message': f'Unmatched {open_b}{close_b} brackets: {open_count} opening, {close_count} closing'
                })
        
        # Check for unterminated strings
        string_pattern = r'(?<!\\)["\']'
        strings = re.findall(string_pattern, content)
        if len(strings) % 2 != 0:
            errors.append({
                'type': 'error',
                'file': file_path,
                'message': 'Possible unterminated string literal'
            })
        
        return errors
    
    @classmethod
    def validate_tailwind_classes(cls, content: str, file_path: str) -> List[Dict[str, any]]:
        """Validate Tailwind CSS classes in JSX/TSX files"""
        errors = []
        
        # Extract className attributes
        class_pattern = r'className\s*=\s*["\']([^"\']+)["\']'
        matches = re.finditer(class_pattern, content)
        
        for match in matches:
            classes = match.group(1).split()
            line_num = content[:match.start()].count('\n') + 1
            
            for css_class in classes:
                # Skip dynamic classes (with template literals)
                if '${' in css_class or '{' in css_class:
                    continue
                
                # Check if class matches any valid pattern
                is_valid = any(re.match(pattern, css_class) for pattern in cls.VALID_TAILWIND_PATTERNS)
                
                # Also check for numeric values (like p-4, m-2, etc.)
                if not is_valid and re.match(r'^[a-z]+-\d+$', css_class):
                    is_valid = True
                
                # Check for color classes (like bg-red-500)
                if not is_valid and re.match(r'^[a-z]+-[a-z]+-\d+$', css_class):
                    is_valid = True
                
                if not is_valid and not css_class.startswith('!'):
                    errors.append({
                        'type': 'warning',
                        'file': file_path,
                        'line': line_num,
                        'message': f'Potentially invalid Tailwind class: "{css_class}"'
                    })
        
        return errors
    
    @classmethod
    def validate_package_json(cls, content: str) -> List[Dict[str, any]]:
        """Validate package.json structure"""
        errors = []
        
        try:
            data = json.loads(content)
            
            # Check required fields
            if 'name' not in data:
                errors.append({
                    'type': 'error',
                    'file': 'package.json',
                    'message': 'Missing required field: name'
                })
            
            # Check scripts
            if 'scripts' in data:
                required_scripts = ['dev', 'build']
                for script in required_scripts:
                    if script not in data['scripts']:
                        errors.append({
                            'type': 'warning',
                            'file': 'package.json',
                            'message': f'Missing recommended script: {script}'
                        })
            
            # Validate dependency versions
            for dep_type in ['dependencies', 'devDependencies']:
                if dep_type in data:
                    for pkg, version in data[dep_type].items():
                        if not re.match(r'^[\^~]?\d+\.\d+\.\d+$', version) and version != '*' and version != 'latest':
                            errors.append({
                                'type': 'warning',
                                'file': 'package.json',
                                'message': f'Unusual version format for {pkg}: {version}'
                            })
            
        except json.JSONDecodeError as e:
            errors.append({
                'type': 'error',
                'file': 'package.json',
                'message': f'Invalid JSON: {str(e)}'
            })
        
        return errors
    
    @classmethod
    def validate_imports(cls, content: str, file_path: str, all_files: Dict[str, str]) -> List[Dict[str, any]]:
        """Validate that imports reference existing files"""
        errors = []
        
        # Extract import statements
        import_pattern = r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'
        matches = re.finditer(import_pattern, content)
        
        for match in matches:
            import_path = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            # Skip node_modules imports
            if not import_path.startswith('.') and not import_path.startswith('@/'):
                continue
            
            # Convert import path to file path
            if import_path.startswith('@/'):
                import_path = import_path.replace('@/', 'src/')
            elif import_path.startswith('./'):
                # Relative to current file
                current_dir = str(Path(file_path).parent)
                import_path = str(Path(current_dir) / import_path[2:])
            
            # Check if file exists (try common extensions)
            extensions = ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx']
            found = False
            
            for ext in extensions:
                potential_file = import_path + ext
                if potential_file in all_files:
                    found = True
                    break
            
            if not found:
                errors.append({
                    'type': 'error',
                    'file': file_path,
                    'line': line_num,
                    'message': f'Cannot resolve import: {import_path}'
                })
        
        return errors
    
    @classmethod
    def validate_all_files(cls, files: Dict[str, str]) -> Dict[str, List[Dict[str, any]]]:
        """Validate all files and return errors by file"""
        all_errors = {}
        
        for file_path, content in files.items():
            errors = []
            
            # Validate based on file type
            if file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                errors.extend(cls.validate_typescript(content, file_path))
                
                if file_path.endswith(('.tsx', '.jsx')):
                    errors.extend(cls.validate_tailwind_classes(content, file_path))
                
                errors.extend(cls.validate_imports(content, file_path, files))
            
            elif file_path == 'package.json':
                errors.extend(cls.validate_package_json(content))
            
            if errors:
                all_errors[file_path] = errors
        
        return all_errors
    
    @classmethod
    def format_validation_report(cls, errors: Dict[str, List[Dict[str, any]]]) -> str:
        """Format validation errors into a readable report"""
        if not errors:
            return "✅ No validation errors found!"
        
        report = "⚠️ Validation Report:\n\n"
        
        for file_path, file_errors in errors.items():
            report += f"📄 {file_path}:\n"
            for error in file_errors:
                icon = "❌" if error['type'] == 'error' else "⚠️"
                line_info = f" (line {error['line']})" if 'line' in error else ""
                report += f"  {icon} {error['message']}{line_info}\n"
            report += "\n"
        
        return report