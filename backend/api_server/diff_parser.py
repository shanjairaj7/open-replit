"""
Diff parser for the new update_file format with SEARCH/REPLACE blocks
"""
import re
from typing import List, Tuple, Optional

class DiffParser:
    """Parse and apply diff-style search/replace operations"""
    
    @staticmethod
    def parse_diff_content(content: str) -> List[Tuple[str, str]]:
        """
        Parse content with diff blocks into search/replace pairs.
        Supports multiple diff formats the model might use.
        
        Returns:
            List of (search_text, replace_text) tuples
        """
        # Check if content contains diff blocks
        if '<diff>' not in content:
            # Legacy format - treat entire content as replacement
            return [(None, content)]
        
        search_replace_pairs = []
        
        # Find all diff blocks
        diff_pattern = r'<diff>(.*?)</diff>'
        diff_blocks = re.findall(diff_pattern, content, re.DOTALL)
        
        for block_index, diff_block in enumerate(diff_blocks):
            # Try multiple diff formats the model might use
            
            # Format 1: ------- SEARCH\ncontent\n=======\nreplacement
            search_pattern_1 = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)(?=\n</diff>|\Z)'
            matches = re.findall(search_pattern_1, diff_block, re.DOTALL)
            
            if matches:
                for search_text, replace_text in matches:
                    search_text = search_text.rstrip('\n')
                    replace_text = replace_text.rstrip('\n')
                    search_replace_pairs.append((search_text, replace_text))
                continue
            
            # Format 2: <<<<<<< SEARCH\ncontent\n=======\nreplacement\n>>>>>>> REPLACE
            search_pattern_2 = r'<{7}\s*SEARCH\s*\n(.*?)\n={7}\s*\n(.*?)\n>{7}\s*REPLACE'
            matches = re.findall(search_pattern_2, diff_block, re.DOTALL)
            
            if matches:
                for search_text, replace_text in matches:
                    search_text = search_text.rstrip('\n')
                    replace_text = replace_text.rstrip('\n')
                    search_replace_pairs.append((search_text, replace_text))
                continue
            
            # Format 3: @@@ SEARCH\ncontent\n@@@\nreplacement\n@@@
            search_pattern_3 = r'@{3}\s*SEARCH\s*\n(.*?)\n@{3}\s*\n(.*?)\n@{3}'
            matches = re.findall(search_pattern_3, diff_block, re.DOTALL)
            
            if matches:
                for search_text, replace_text in matches:
                    search_text = search_text.rstrip('\n')
                    replace_text = replace_text.rstrip('\n')
                    search_replace_pairs.append((search_text, replace_text))
                continue
            
            # Format 4: Standard unified diff format (- and + lines)
            # This is more complex but handles standard diff output
            if diff_block.strip().startswith('@@') or '-' in diff_block or '+' in diff_block:
                # Try to parse unified diff format
                unified_pairs = DiffParser._parse_unified_diff(diff_block)
                if unified_pairs:
                    search_replace_pairs.extend(unified_pairs)
                    continue
            
            # Format 5: Simple SEARCH/REPLACE without markers
            search_replace_match = re.search(r'SEARCH\s*:?\s*\n(.*?)\n\s*REPLACE\s*:?\s*\n(.*?)(?=\n|$)', diff_block, re.DOTALL)
            if search_replace_match:
                search_text = search_replace_match.group(1).rstrip('\n')
                replace_text = search_replace_match.group(2).rstrip('\n')
                search_replace_pairs.append((search_text, replace_text))
                continue
            
            # If no format matched, this is likely malformed
            print(f"⚠️  Warning: Could not parse diff block {block_index + 1}. Unsupported format.")
        
        # If no valid diff blocks found, treat as legacy format
        if not search_replace_pairs:
            # Remove the failed diff tags and use content as-is
            clean_content = re.sub(r'<diff>.*?</diff>', '', content, flags=re.DOTALL).strip()
            return [(None, clean_content)]
        
        return search_replace_pairs
    
    @staticmethod
    def _parse_unified_diff(diff_block: str) -> List[Tuple[str, str]]:
        """
        Parse unified diff format (e.g., from git diff)
        Returns list of (search_text, replace_text) tuples
        """
        # This is a simplified unified diff parser
        # Real implementation would be more complex
        lines = diff_block.split('\n')
        search_lines = []
        replace_lines = []
        
        for line in lines:
            if line.startswith('-') and not line.startswith('---'):
                search_lines.append(line[1:])  # Remove the '-' prefix
            elif line.startswith('+') and not line.startswith('+++'):
                replace_lines.append(line[1:])  # Remove the '+' prefix
        
        if search_lines or replace_lines:
            search_text = '\n'.join(search_lines) if search_lines else ''
            replace_text = '\n'.join(replace_lines) if replace_lines else ''
            return [(search_text, replace_text)]
        
        return []
    
    @staticmethod
    def apply_search_replace(file_content: str, search_text: str, replace_text: str) -> Tuple[str, bool]:
        """
        Apply a single search/replace operation to file content
        
        Args:
            file_content: The current file content
            search_text: Text to search for (exact match)
            replace_text: Text to replace with
            
        Returns:
            Tuple of (modified_content, success_flag)
        """
        if search_text is None:
            # Legacy format - replace entire file
            return replace_text, True
        
        # Check if search text exists in file
        if search_text not in file_content:
            return file_content, False
        
        # Replace only the first occurrence
        modified_content = file_content.replace(search_text, replace_text, 1)
        return modified_content, True
    
    @staticmethod
    def process_update_file(file_content: str, update_content: str) -> Tuple[str, List[str], List[str]]:
        """
        Process an update_file action with potential diff blocks
        
        Args:
            file_content: Current content of the file
            update_content: Content from the update_file action (may contain diff blocks)
            
        Returns:
            Tuple of (final_content, successes, failures)
            - final_content: The updated file content
            - successes: List of successful replacements  
            - failures: List of detailed failure messages with fix instructions
        """
        # Parse the update content for search/replace pairs
        search_replace_pairs = DiffParser.parse_diff_content(update_content)
        
        successes = []
        failures = []
        current_content = file_content
        
        for i, (search_text, replace_text) in enumerate(search_replace_pairs):
            if search_text is None:
                # Legacy format - replace entire file
                current_content = replace_text
                successes.append("Replaced entire file content")
            else:
                # Apply search/replace
                new_content, success = DiffParser.apply_search_replace(
                    current_content, search_text, replace_text
                )
                
                if success:
                    current_content = new_content
                    # Truncate long search text for display
                    display_search = search_text[:50] + "..." if len(search_text) > 50 else search_text
                    successes.append(f"✅ Block {i+1}: Successfully replaced '{display_search}'")
                else:
                    # Generate detailed error message with fix instructions
                    detailed_error = DiffParser._generate_detailed_search_failure_message(
                        search_text, file_content, i+1
                    )
                    failures.append(detailed_error)
        
        return current_content, successes, failures
    
    @staticmethod
    def _generate_detailed_search_failure_message(search_text: str, file_content: str, block_number: int) -> str:
        """
        Generate detailed error message with specific instructions for fixing search failures
        """
        # Truncate search text for display but show enough context
        display_search = search_text[:200] + "..." if len(search_text) > 200 else search_text
        
        # Find the closest match in the file content
        file_lines = file_content.split('\n')
        search_lines = search_text.split('\n')
        
        # Look for partial matches to give helpful hints
        best_match_info = DiffParser._find_closest_match(search_text, file_content)
        
        error_message = f"❌ Block {block_number} SEARCH content not found in file.\n"
        error_message += f"   Searched for: '{display_search}'\n"
        
        if best_match_info:
            error_message += f"   💡 CLOSEST MATCH found: {best_match_info}\n"
        
        error_message += f"\n   🔧 TO FIX THIS:\n"
        error_message += f"   1. Use 'read_file' action to see the current file content\n"
        error_message += f"   2. Copy the EXACT text you want to replace (including indentation)\n"
        error_message += f"   3. Make sure line breaks and spacing match exactly\n"
        error_message += f"   4. Consider updating smaller sections instead of large blocks\n"
        
        # Add specific hints based on common issues
        if search_text.count('\n') > 20:
            error_message += f"   ⚠️  Large search block detected - consider breaking into smaller parts\n"
        
        if '  ' in search_text and '\t' in file_content:
            error_message += f"   ⚠️  Possible indentation mismatch (spaces vs tabs)\n"
        elif '\t' in search_text and '  ' in file_content:
            error_message += f"   ⚠️  Possible indentation mismatch (tabs vs spaces)\n"
            
        # Check for import differences
        if 'import ' in search_text:
            file_imports = [line for line in file_lines if line.strip().startswith('import ')]
            search_imports = [line for line in search_lines if line.strip().startswith('import ')]
            if len(file_imports) != len(search_imports):
                error_message += f"   ⚠️  Import mismatch: File has {len(file_imports)} imports, search expects {len(search_imports)}\n"
        
        return error_message
    
    @staticmethod
    def _find_closest_match(search_text: str, file_content: str) -> str:
        """
        Find the closest matching content in the file to help with debugging
        """
        search_lines = [line.strip() for line in search_text.split('\n') if line.strip()]
        file_lines = [line.strip() for line in file_content.split('\n') if line.strip()]
        
        if not search_lines:
            return None
            
        # Look for the first line of search text in the file
        first_search_line = search_lines[0]
        
        for i, file_line in enumerate(file_lines):
            if first_search_line in file_line or file_line in first_search_line:
                # Found a potential starting point
                context_start = max(0, i - 2)
                context_end = min(len(file_lines), i + 5)
                context_lines = file_lines[context_start:context_end]
                
                return f"Line {i+1}, context: '{' | '.join(context_lines)}'"
        
        # Look for any matching lines
        matches = []
        for search_line in search_lines:
            for i, file_line in enumerate(file_lines):
                if search_line == file_line:
                    matches.append(f"Line {i+1}: '{file_line}'")
                    break
                    
        if matches:
            return f"Partial matches found: {'; '.join(matches[:3])}"
            
        return "No similar content found in file"
    
    @staticmethod
    def find_file_with_content(project_path: str, search_text: str, file_patterns: List[str] = None) -> Optional[str]:
        """
        Search for a file containing specific text content
        
        Args:
            project_path: Root path of the project
            search_text: Text to search for in files
            file_patterns: Optional list of file patterns to search (e.g., ['*.py', '*.js'])
            
        Returns:
            Path to the first file containing the text, or None if not found
        """
        import os
        import glob
        
        # Default file patterns if none provided
        if file_patterns is None:
            file_patterns = [
                '**/*.py', '**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx',
                '**/*.java', '**/*.cpp', '**/*.c', '**/*.h', '**/*.hpp',
                '**/*.cs', '**/*.go', '**/*.rs', '**/*.php', '**/*.rb',
                '**/*.swift', '**/*.kt', '**/*.scala', '**/*.r', '**/*.m'
            ]
        
        for pattern in file_patterns:
            pattern_path = os.path.join(project_path, pattern)
            for file_path in glob.glob(pattern_path, recursive=True):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if search_text in content:
                            return file_path
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue
        
        return None