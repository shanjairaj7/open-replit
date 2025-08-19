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
        Parse content with diff blocks into search/replace pairs
        
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
        
        for diff_block in diff_blocks:
            # Parse each diff block for SEARCH and REPLACE sections
            search_pattern = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n\+\+\+\+\+\+\+\s*REPLACE'
            matches = re.findall(search_pattern, diff_block, re.DOTALL)
            
            for search_text, replace_text in matches:
                # Clean up the text (remove leading/trailing whitespace from block markers)
                # But preserve internal whitespace and indentation
                search_text = search_text.rstrip('\n')
                replace_text = replace_text.rstrip('\n')
                search_replace_pairs.append((search_text, replace_text))
        
        # If no valid diff blocks found, treat as legacy format
        if not search_replace_pairs:
            # Remove the failed diff tags and use content as-is
            clean_content = re.sub(r'<diff>.*?</diff>', '', content, flags=re.DOTALL).strip()
            return [(None, clean_content)]
        
        return search_replace_pairs
    
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
            - failures: List of failed replacements
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
                    successes.append(f"Replaced block {i+1}: '{display_search}'")
                else:
                    # Truncate long search text for display
                    display_search = search_text[:100] + "..." if len(search_text) > 100 else search_text
                    failures.append(f"Block {i+1} not found: '{display_search}'")
        
        return current_content, successes, failures
    
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