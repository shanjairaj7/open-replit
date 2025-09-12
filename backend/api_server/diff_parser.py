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
        # Check if content contains diff blocks or direct search/replace format
        if '<diff>' not in content and '------- SEARCH' not in content:
            # Legacy format - treat entire content as replacement
            return [(None, content)]
        
        search_replace_pairs = []
        
        # Handle direct search/replace format (without <diff> tags)
        if '<diff>' not in content and '------- SEARCH' in content:
            return DiffParser._parse_direct_search_replace(content)
        
        # Find all diff blocks (legacy format)
        diff_pattern = r'<diff>(.*?)</diff>'
        diff_blocks = re.findall(diff_pattern, content, re.DOTALL)
        
        for block_index, diff_block in enumerate(diff_blocks):
            # Try multiple diff formats the model might use
            
            # Format 1: ------- SEARCH\ncontent\n=======\nreplacement
            # Fixed: Use exactly 7 equals to avoid capturing additional ======= lines in requirements.txt
            # This prevents confusion with package version specifiers like package===1.0.0
            search_pattern_1 = r'-------\s*SEARCH\s*\n(.*?)\n={7}\s*\n(.*?)(?=\n={7}\s*(?:\n|$)|\n-------\s*SEARCH|\n</diff>|\Z)'
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
        # CRITICAL: Validate input content for obvious corruption first
        validation_error = DiffParser._validate_search_replace_content(update_content)
        if validation_error:
            return file_content, [], [f"❌ MALFORMED SEARCH/REPLACE CONTENT DETECTED: {validation_error}"]
        
        # Parse the update content for search/replace pairs
        search_replace_pairs = DiffParser.parse_diff_content(update_content)
        
        successes = []
        failures = []
        current_content = file_content
        
        for i, (search_text, replace_text) in enumerate(search_replace_pairs):
            if search_text is None:
                # Legacy format - replace entire file
                # CRITICAL: Sanitize replacement content to ensure no search/replace markers
                sanitized_replace_text = DiffParser._sanitize_content(replace_text)
                current_content = sanitized_replace_text
                successes.append("Replaced entire file content")
            else:
                # CRITICAL: Sanitize replacement text before applying
                sanitized_replace_text = DiffParser._sanitize_content(replace_text)
                
                # Apply search/replace
                new_content, success = DiffParser.apply_search_replace(
                    current_content, search_text, sanitized_replace_text
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
        
        # CRITICAL: Final sanitization check - ensure no search/replace markers in final content
        final_content = DiffParser._sanitize_content(current_content)
        
        # Verify final content integrity
        if DiffParser._has_search_replace_markers(final_content):
            print("🚨 CRITICAL ERROR: Final content still contains search/replace markers!")
            return file_content, [], ["❌ CRITICAL SAFETY CHECK FAILED: Processed content contains search/replace markers. File update blocked to prevent corruption."]
        
        return final_content, successes, failures
    
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

    @staticmethod 
    def _parse_direct_search_replace(content: str) -> List[Tuple[str, str]]:
        """
        Parse direct search/replace format without <diff> tags
        Handles multiple blocks with mixed formats in the same content
        
        Supported formats:
        1. ------- SEARCH ... ======= ... +++++++ REPLACE
        2. ------- SEARCH ... >>>>>>> REPLACE ... (with replacement after)
        3. ------- SEARCH ... ======= ... >>>>>>> REPLACE  
        4. ------- SEARCH ... ======= ... (implicit end)
        
        Returns:
            List of (search_text, replace_text) tuples
        """
        search_replace_pairs = []
        
        # Split content into potential blocks based on SEARCH markers
        blocks = re.split(r'(?=-------\s*SEARCH)', content)
        blocks = [b for b in blocks if b.strip()]  # Remove empty blocks
        
        for block in blocks:
            if not block.strip().startswith('-------'):
                print(f"⚠️ Skipping block that doesn't start with SEARCH marker: {block[:50]}...")
                continue
                
            # CRITICAL: Pre-validate block for obvious corruption
            if DiffParser._is_block_corrupted(block):
                print(f"⚠️ Skipping corrupted block: {block[:100]}...")
                continue
                
            # Try each pattern on the individual block
            block_processed = False
            
            # Pattern 1: ------- SEARCH ... >>>>>>> REPLACE ... (replacement after marker)
            if not block_processed:
                pattern = r'-------\s*SEARCH\s*\n(.*?)\n>{7}\s*REPLACE\s*\n(.*?)$'
                match = re.search(pattern, block, re.DOTALL)
                if match:
                    search_text = match.group(1).rstrip('\n')
                    replace_text = match.group(2).rstrip('\n')
                    
                    # CRITICAL: Validate extracted content
                    if DiffParser._validate_extracted_content(search_text, replace_text):
                        search_replace_pairs.append((search_text, replace_text))
                        block_processed = True
                        print(f"✅ Parsed block with >>>>>>> REPLACE format")
                    else:
                        print(f"⚠️ Skipping invalid extracted content from >>>>>>> REPLACE block")
            
            # Pattern 2: ------- SEARCH ... ======= ... >>>>>>> REPLACE
            if not block_processed:
                pattern = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n>{7}\s*REPLACE'
                match = re.search(pattern, block, re.DOTALL)
                if match:
                    search_text = match.group(1).rstrip('\n')
                    replace_text = match.group(2).rstrip('\n')
                    
                    # CRITICAL: Validate extracted content
                    if DiffParser._validate_extracted_content(search_text, replace_text):
                        search_replace_pairs.append((search_text, replace_text))
                        block_processed = True
                        print(f"✅ Parsed block with ======= / >>>>>>> REPLACE format")
                    else:
                        print(f"⚠️ Skipping invalid extracted content from ======= / >>>>>>> REPLACE block")
            
            # Pattern 3: ------- SEARCH ... ======= ... +++++++ REPLACE
            if not block_processed:
                pattern = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n\+{7}\s*REPLACE'
                match = re.search(pattern, block, re.DOTALL)
                if match:
                    search_text = match.group(1).rstrip('\n')
                    replace_text = match.group(2).rstrip('\n')
                    
                    # Clean replacement text of any separator artifacts
                    replace_lines = replace_text.split('\n')
                    clean_replace_lines = []
                    for line in replace_lines:
                        if line.strip() == "=======":
                            print(f"⚠️ Removing separator artifact from replacement content: '{line}'")
                            continue
                        clean_replace_lines.append(line)
                    
                    clean_replace_text = '\n'.join(clean_replace_lines)
                    
                    # CRITICAL: Validate extracted content
                    if DiffParser._validate_extracted_content(search_text, clean_replace_text):
                        search_replace_pairs.append((search_text, clean_replace_text))
                        block_processed = True
                        print(f"✅ Parsed block with ======= / +++++++ REPLACE format")
                    else:
                        print(f"⚠️ Skipping invalid extracted content from ======= / +++++++ REPLACE block")
            
            # Pattern 4: ------- SEARCH ... ======= ... (implicit end)
            if not block_processed:
                pattern = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)$'
                match = re.search(pattern, block, re.DOTALL)
                if match:
                    search_text = match.group(1).rstrip('\n')
                    replace_text = match.group(2).rstrip('\n')
                    
                    # Skip if replacement is just separator artifacts or empty
                    if replace_text.strip() not in ["=======", ""] and DiffParser._validate_extracted_content(search_text, replace_text):
                        search_replace_pairs.append((search_text, replace_text))
                        block_processed = True
                        print(f"✅ Parsed block with implicit end format")
                    else:
                        print(f"⚠️ Skipping malformed block with empty/separator replacement or invalid content")
            
            if not block_processed:
                print(f"⚠️ Could not parse search/replace block: {block[:100]}...")
        
        return search_replace_pairs
    
    @staticmethod
    def _validate_search_replace_content(content: str) -> Optional[str]:
        """
        Validate search/replace content for obvious corruption/malformation
        
        Returns:
            Error message if content is malformed, None if valid
        """
        # Check for obvious signs of corruption
        
        # Count various markers to detect malformation
        search_count = content.count('------- SEARCH')
        equals_count = content.count('=======')
        plus_replace_count = content.count('+++++++ REPLACE')
        arrow_replace_count = content.count('>>>>>>> REPLACE')
        
        # Detect duplicate markers (sign of malformation)
        if arrow_replace_count > search_count * 2:  # Too many arrow markers
            return f"Too many >>>>>>> REPLACE markers ({arrow_replace_count}) relative to SEARCH blocks ({search_count})"
        
        # Check for orphaned markers (markers without proper pairs)
        if equals_count > 0 and search_count == 0:
            return "Found ======= markers without corresponding ------- SEARCH markers"
        
        if (plus_replace_count > 0 or arrow_replace_count > 0) and search_count == 0:
            return "Found REPLACE markers without corresponding ------- SEARCH markers"
        
        # Check for obvious malformed patterns
        malformed_patterns = [
            r'>{7}\s*REPLACE\s*\n>{7}\s*REPLACE',  # Duplicate arrow replace markers
            r'={7}\s*\n={7}',  # Duplicate equals markers
            r'>{7}\s*REPLACE[^a-zA-Z0-9\s]*import',  # REPLACE marker immediately followed by import (corruption)
        ]
        
        for pattern in malformed_patterns:
            if re.search(pattern, content):
                return f"Detected malformed pattern: {pattern}"
        
        # Check for content that starts with markers (likely corruption)
        if content.strip().startswith(('=======', '>>>>>>> REPLACE', '+++++++ REPLACE')):
            return "Content starts with REPLACE marker (likely corrupted)"
        
        return None
    
    @staticmethod
    def _sanitize_content(content: str) -> str:
        """
        Remove any search/replace markers from content to prevent corruption
        
        Args:
            content: Content that may contain markers
            
        Returns:
            Sanitized content with all search/replace markers removed
        """
        if not content:
            return content
        
        # List of all possible search/replace markers to remove
        markers_to_remove = [
            r'-------\s*SEARCH\s*\n?',
            r'=======\s*\n?',
            r'\+{7}\s*REPLACE\s*\n?',
            r'>{7}\s*REPLACE\s*\n?',
            r'<{7}\s*SEARCH\s*\n?',
            r'@{3}\s*SEARCH\s*\n?',
            r'@{3}\s*\n?',
        ]
        
        sanitized = content
        for marker_pattern in markers_to_remove:
            sanitized = re.sub(marker_pattern, '', sanitized)
        
        # Remove any standalone marker lines
        lines = sanitized.split('\n')
        clean_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just markers
            if stripped in ['=======', '>>>>>>> REPLACE', '+++++++ REPLACE', '------- SEARCH']:
                print(f"🧹 Sanitized marker line: '{stripped}'")
                continue
            clean_lines.append(line)
        
        result = '\n'.join(clean_lines)
        
        # Log if we removed anything
        if result != content:
            print(f"🧹 Sanitized content: removed {len(content) - len(result)} characters of markers")
        
        return result
    
    @staticmethod
    def _has_search_replace_markers(content: str) -> bool:
        """
        Check if content contains search/replace markers
        
        Returns:
            True if markers are found, False otherwise
        """
        if not content:
            return False
        
        marker_patterns = [
            r'-------\s*SEARCH',
            r'={7}',
            r'\+{7}\s*REPLACE',
            r'>{7}\s*REPLACE',
            r'<{7}\s*SEARCH',
            r'@{3}\s*SEARCH',
        ]
        
        for pattern in marker_patterns:
            if re.search(pattern, content):
                return True
                
        return False
    
    @staticmethod
    def _is_block_corrupted(block: str) -> bool:
        """
        Check if a search/replace block is obviously corrupted
        
        Returns:
            True if block is corrupted, False otherwise
        """
        if not block:
            return True
        
        # Check for obvious corruption patterns
        corruption_patterns = [
            r'>{7}\s*REPLACE\s*[^\n]*>{7}\s*REPLACE',  # Duplicate consecutive REPLACE markers
            r'={7}\s*[^\n]*={7}',  # Duplicate consecutive equals markers (but not spaced)
            r'REPLACE[^a-zA-Z0-9\s]*import',  # REPLACE marker directly before import (corruption)
            r'\A>{7}\s*REPLACE',  # Block starts with REPLACE marker (use \A for start of string)
            r'\A={7}',  # Block starts with equals marker (use \A for start of string)
        ]
        
        for pattern in corruption_patterns:
            # Don't use MULTILINE for start-of-string patterns
            flags = 0 if pattern.startswith(r'\A') else re.MULTILINE
            if re.search(pattern, block, flags):
                return True
        
        # Check marker ratios (should be balanced)
        search_markers = block.count('------- SEARCH')
        replace_arrow = block.count('>>>>>>> REPLACE')
        replace_plus = block.count('+++++++ REPLACE')
        equals = block.count('=======')
        
        # A block should have exactly 1 SEARCH marker
        if search_markers != 1:
            return True
        
        # Should have reasonable marker balance - but allow either arrow or plus, not both excessively
        total_replace_markers = replace_arrow + replace_plus
        if total_replace_markers > 1:  # One block should have exactly 1 replace marker
            # But allow for some cases where there might be 1 arrow + 1 plus in complex patterns
            if replace_arrow > 1 or replace_plus > 1:  # Multiple of the same type is definitely corruption
                return True
        
        # Multiple equals are OK as long as they're properly spaced (not consecutive corruption)
        if equals > 2:  # Too many equals markers for one block
            return True
        
        return False
    
    @staticmethod
    def _validate_extracted_content(search_text: str, replace_text: str) -> bool:
        """
        Validate extracted search and replace text to ensure they're clean
        
        Returns:
            True if content is valid, False otherwise
        """
        if search_text is None or replace_text is None:
            return False
        
        # Check if extracted content still contains markers (sign of bad parsing)
        if DiffParser._has_search_replace_markers(search_text):
            print(f"⚠️ Search text contains markers - bad extraction: {search_text[:50]}...")
            return False
        
        if DiffParser._has_search_replace_markers(replace_text):
            print(f"⚠️ Replace text contains markers - bad extraction: {replace_text[:50]}...")
            return False
        
        # Search text should not be empty (replace text can be empty for deletion)
        if not search_text.strip():
            print(f"⚠️ Search text is empty - invalid block")
            return False
        
        # Check for obvious corruption indicators
        corruption_indicators = [
            'REPLACE',
            'SEARCH',
            '=======',
            '>>>>>>>',
            '+++++++',
            '-------',
        ]
        
        for indicator in corruption_indicators:
            if indicator in search_text and search_text.strip() == indicator:
                print(f"⚠️ Search text is just a marker: '{indicator}'")
                return False
            if indicator in replace_text and replace_text.strip() == indicator:
                print(f"⚠️ Replace text is just a marker: '{indicator}'")
                return False
        
        return True