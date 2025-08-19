"""
Update file handler with diff-style search/replace functionality
Handles both legacy full-file updates and new diff-block updates
"""
import os
import sys
from typing import Tuple, Optional

class UpdateFileHandler:
    """Handles update_file actions with both diff and legacy formats"""
    
    def __init__(self, read_file_callback, update_file_callback):
        """
        Initialize with callbacks for file operations
        
        Args:
            read_file_callback: Function(file_path) -> content or None
            update_file_callback: Function(file_path, content) -> result dict
        """
        self.read_file = read_file_callback
        self.update_file = update_file_callback
        
        # Import diff parser from coder utils
        try:
            # Add coder utils to path
            coder_utils_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'coder', 'utils')
            if coder_utils_path not in sys.path:
                sys.path.insert(0, coder_utils_path)
            from diff_parser import DiffParser
            self.diff_parser = DiffParser
        except ImportError as e:
            print(f"Warning: Could not import DiffParser: {e}")
            self.diff_parser = None
    
    def handle_update_file(self, action: dict) -> str:
        """
        Main entry point for handling update_file actions
        
        Args:
            action: Dictionary containing 'path' and 'content' keys
            
        Returns:
            String message describing the result
        """
        file_path = action.get('path') or action.get('filePath')
        update_content = action.get('content', '')
        
        # Remove backticks if present
        update_content = self._remove_backticks(update_content)
        
        # Check if update content is empty
        if not update_content or update_content.strip() == '':
            print(f"⚠️ Empty update content detected for: {file_path}")
            return self._empty_content_warning(file_path)
        
        print(f"💾 Processing update for: {file_path}")
        
        # Determine update type and process
        if '<diff>' in update_content and self.diff_parser:
            print("🔍 Detected diff-style update with search/replace blocks")
            return self._handle_diff_style_update(file_path, update_content)
        else:
            if '<diff>' in update_content:
                print("⚠️ Diff blocks detected but DiffParser not available, falling back to legacy")
            else:
                print("📝 Detected legacy-style update (full file replacement)")
            return self._handle_legacy_style_update(file_path, update_content)
    
    def _handle_diff_style_update(self, file_path: str, update_content: str) -> str:
        """Handle update_file with diff-style search/replace blocks"""
        try:
            # Read current file content
            current_content = self.read_file(file_path)
            if current_content is None:
                return f"❌ Could not read current content of '{file_path}' for diff processing"
            
            print(f"📖 Read current file: {len(current_content)} characters")
            
            # Process the diff
            final_content, successes, failures = self.diff_parser.process_update_file(
                current_content, update_content
            )
            
            # Report results
            print(f"📝 Diff processing results:")
            print(f"   ✅ Successes: {len(successes)}")
            for success in successes:
                print(f"      • {success}")
            
            if failures:
                print(f"   ❌ Failures: {len(failures)}")
                for failure in failures:
                    print(f"      • {failure}")
            
            # If no successful replacements, return failure
            if not successes:
                failure_msg = f"❌ No successful replacements in '{file_path}'"
                if failures:
                    failure_msg += f"\n\nSearch blocks that failed to match:\n" + "\n".join(f"• {f}" for f in failures)
                failure_msg += f"\n\nTip: Ensure search text matches exactly (including whitespace and indentation)"
                return failure_msg
            
            # Apply the changes
            update_result = self.update_file(file_path, final_content)
            
            if update_result and update_result.get('status') == 'updated':
                print(f"✅ File updated successfully: {file_path}")
                return self._build_success_message(file_path, successes, failures, update_result, "diff blocks")
            else:
                error_msg = f"Failed to update file '{file_path}' after diff processing"
                if update_result:
                    error_msg += f": {update_result.get('error', 'Unknown error')}"
                print(f"❌ {error_msg}")
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Error during diff processing for '{file_path}': {str(e)}"
            print(error_msg)
            # Fall back to legacy update
            print("🔄 Falling back to legacy file replacement")
            return self._handle_legacy_style_update(file_path, update_content)
    
    def _handle_legacy_style_update(self, file_path: str, file_content: str) -> str:
        """Handle legacy-style update (full file replacement)"""
        print(f"📄 Content length: {len(file_content)} characters")
        
        # Update file via API
        update_result = self.update_file(file_path, file_content)
        
        if update_result and update_result.get('status') == 'updated':
            print(f"✅ File updated successfully: {file_path}")
            return self._build_success_message(file_path, ["Replaced entire file content"], [], update_result, "full replacement")
        else:
            error_msg = f"Failed to update file '{file_path}'"
            if update_result:
                error_msg += f": {update_result.get('error', 'Unknown error')}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def _build_success_message(self, file_path: str, successes: list, failures: list, 
                              update_result: dict, update_type: str) -> str:
        """Build a comprehensive success message"""
        success_msg = f"File '{file_path}' updated successfully using {update_type}.\n\n"
        
        if successes:
            success_msg += f"Applied {len(successes)} successful changes:\n"
            for success in successes:
                success_msg += f"• {success}\n"
        
        if failures:
            success_msg += f"\nSkipped {len(failures)} failed searches:\n"
            for failure in failures:
                success_msg += f"• {failure}\n"
        
        # Check for validation errors
        python_errors = update_result.get('python_errors', '')
        typescript_errors = update_result.get('typescript_errors', '')
        
        if python_errors:
            print(f"⚠️ Python validation errors found")
            success_msg += f"\nPython validation errors:\n{python_errors}"
            
        if typescript_errors:
            print(f"⚠️ TypeScript validation errors found")
            success_msg += f"\nTypeScript validation errors:\n{typescript_errors}"
        
        return success_msg
    
    def _remove_backticks(self, content: str) -> str:
        """Remove backticks from content if present"""
        # Remove common code block patterns
        patterns = [
            ('```python\n', ''),
            ('```javascript\n', ''),
            ('```typescript\n', ''),
            ('```jsx\n', ''),
            ('```tsx\n', ''),
            ('```\n', ''),
            ('```', ''),
        ]
        
        for pattern, replacement in patterns:
            content = content.replace(pattern, replacement)
        
        # Remove trailing backticks
        if content.endswith('```'):
            content = content[:-3]
            
        return content.strip()
    
    def _empty_content_warning(self, file_path: str) -> str:
        """Generate warning message for empty content"""
        return f"""❌ File update blocked: Empty content detected for '{file_path}'

Are you sure you want to update this file with empty content? If not, please add the actual content inside the action tag.

Example of proper usage with diff blocks:
<action type="update_file" path="{file_path}">
<diff>
------- SEARCH
old_content_to_find
=======
new_content_to_replace_with
+++++++ REPLACE
</diff>
</action>

Example of legacy format:
<action type="update_file" path="{file_path}">
# Your actual file content goes here
print("Updated content!")
def updated_function():
    return "This is the new content"
</action>

If you really want to update the file to be empty, please confirm by responding with the action again and explicitly stating it should be empty."""