#!/usr/bin/env python3
"""
F-String Backslash Fixer
Automatically finds and fixes f-strings that contain backslashes in expressions.
"""

import re
import os
import ast
from pathlib import Path
from typing import List, Tuple, Dict

class FStringFixer:
    def __init__(self):
        self.fixes_made = 0
        self.files_processed = 0
        
    def find_fstring_issues(self, content: str) -> List[Tuple[int, str, str]]:
        """Find f-strings with backslash issues and return (line_num, original, suggested_fix)"""
        issues = []
        lines = content.split('\n')
        
        # Common patterns that cause issues
        problematic_patterns = [
            # Pattern 1: '\n'.join() or similar
            (r'f["\']([^"\']*)\{([^}]*[\\][^}]*\.join\([^)]*\))[^}]*\}([^"\']*)["\']', 
             r"Extract join operation: var = {}\nf'{}{{var}}{}'"),
            
            # Pattern 2: Any expression with backslashes
            (r'f["\']([^"\']*)\{([^}]*\\[^}]*)\}([^"\']*)["\']',
             r"Extract expression: var = {}\nf'{}{{var}}{}'"),
        ]
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip if line is a comment or docstring
            if line_stripped.startswith('#') or line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                continue
                
            # Check for f-strings with backslashes in expressions
            for pattern, fix_template in problematic_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    if '\\' in match.group(2):  # Backslash in the expression
                        issues.append((line_num, line, match.group(2)))
                        break
                        
        return issues
    
    def fix_join_expressions(self, content: str) -> str:
        """Fix specific join() expressions in f-strings"""
        
        def replace_join_fstring(match):
            before = match.group(1)
            expression = match.group(2)
            after = match.group(3)
            quote = match.group(0)[1]  # Get the quote type (' or ")
            
            # Extract the join operation
            if '.join(' in expression:
                # Generate a variable name
                var_name = 'joined_text'
                indent = '    '  # Default indent
                
                return f'{indent}{var_name} = {expression.strip()}\n{indent}f{quote}{before}{{{var_name}}}{after}{quote}'
            
            return match.group(0)
        
        # Pattern for f-strings with join operations containing backslashes
        pattern = r'f(["\'])([^"\']*)\{([^}]*\.join\([^}]*\\[^}]*\)[^}]*)\}([^"\']*)\1'
        
        return re.sub(pattern, replace_join_fstring, content, flags=re.MULTILINE)
    
    def fix_generic_backslash_expressions(self, content: str) -> str:
        """Fix generic expressions with backslashes in f-strings"""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Check if line contains f-string with backslash in expression
            fstring_pattern = r'f(["\'])([^"\']*)\{([^}]*\\[^}]*)\}([^"\']*)\1'
            match = re.search(fstring_pattern, line)
            
            if match and not '.join(' in match.group(3):  # Skip join patterns (handled separately)
                quote = match.group(1)
                before = match.group(2)
                expression = match.group(3)
                after = match.group(4)
                
                # Get indentation
                indent = re.match(r'(\s*)', line).group(1)
                
                # Generate variable name
                var_name = f'expr_var_{i}'
                
                # Create fixed version
                fixed_lines.append(f'{indent}{var_name} = {expression.strip()}')
                fixed_lines.append(f'{indent}f{quote}{before}{{{var_name}}}{after}{quote}')
                self.fixes_made += 1
            else:
                fixed_lines.append(line)
                
        return '\n'.join(fixed_lines)
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single Python file and fix f-string issues"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Check if file has syntax issues first
            try:
                ast.parse(original_content)
            except SyntaxError as e:
                if "f-string expression part cannot include a backslash" in str(e):
                    print(f"🔧 Fixing f-string issues in {file_path}")
                    
                    # Apply fixes
                    fixed_content = original_content
                    fixed_content = self.fix_join_expressions(fixed_content)
                    fixed_content = self.fix_generic_backslash_expressions(fixed_content)
                    
                    # Verify the fix worked
                    try:
                        ast.parse(fixed_content)
                        
                        # Write back the fixed content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        print(f"✅ Fixed {file_path}")
                        self.fixes_made += 1
                        return True
                        
                    except SyntaxError as fix_error:
                        print(f"❌ Fix attempt failed for {file_path}: {fix_error}")
                        return False
                else:
                    print(f"⚠️  Other syntax error in {file_path}: {e}")
                    return False
            
            self.files_processed += 1
            return True
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False
    
    def fix_directory(self, directory: Path) -> Dict[str, int]:
        """Fix all Python files in a directory"""
        print(f"🔍 Scanning directory: {directory}")
        
        python_files = list(directory.glob("*.py"))
        print(f"📁 Found {len(python_files)} Python files")
        
        results = {"processed": 0, "fixed": 0, "errors": 0}
        
        for file_path in python_files:
            print(f"🔍 Checking {file_path.name}...")
            
            if self.process_file(file_path):
                results["processed"] += 1
            else:
                results["errors"] += 1
        
        return results

def main():
    """Main function to run the f-string fixer"""
    fixer = FStringFixer()
    
    # Get current directory
    current_dir = Path(".")
    
    print("🚀 F-String Backslash Fixer")
    print("=" * 50)
    
    # Fix files in current directory
    results = fixer.fix_directory(current_dir)
    
    print("\n📊 Results:")
    print(f"Files processed: {results['processed']}")
    print(f"Files fixed: {results['fixed']}")
    print(f"Errors: {results['errors']}")
    
    if results['fixed'] > 0:
        print(f"\n✅ Successfully fixed {results['fixed']} files!")
        print("You can now redeploy to Modal.com")
    else:
        print("\n✅ No f-string issues found!")

if __name__ == "__main__":
    main()