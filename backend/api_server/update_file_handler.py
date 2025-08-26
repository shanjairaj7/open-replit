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
        
        # Import diff parser (local copy)
        try:
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
            
            # If no successful replacements, provide detailed error feedback
            if not successes:
                failure_msg = f"❌ DIFF UPDATE FAILED: No search patterns matched in '{file_path}'\n"
                failure_msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                
                if failures:
                    failure_msg += f"\n📋 DETAILED ERROR ANALYSIS:\n"
                    for i, failure in enumerate(failures, 1):
                        failure_msg += f"\n{i}. {failure}\n"
                        
                failure_msg += f"\n🎯 NEXT STEPS TO FIX THIS:\n"
                failure_msg += f"   1. First, use read_file action on '{file_path}' to see current content\n"
                failure_msg += f"   2. Identify the exact text section you want to modify\n"
                failure_msg += f"   3. Copy the EXACT text including all whitespace and indentation\n" 
                failure_msg += f"   4. Use that exact text in your SEARCH block\n"
                failure_msg += f"   5. Make sure your diff uses the correct format:\n"
                failure_msg += f"      <diff>\n"
                failure_msg += f"      ------- SEARCH\n"
                failure_msg += f"      [exact text to find]\n"
                failure_msg += f"      =======\n"
                failure_msg += f"      [replacement text]\n" 
                failure_msg += f"      </diff>\n"
                failure_msg += f"\n⚠️  COMMON MISTAKES TO AVOID:\n"
                failure_msg += f"   • Mixing spaces and tabs for indentation\n"
                failure_msg += f"   • Missing or extra line breaks\n"
                failure_msg += f"   • Assuming file content without reading it first\n"
                failure_msg += f"   • Using content from different files or old versions\n"
                failure_msg += f"   • Making search blocks too large (try smaller sections)\n"
                
                return failure_msg
            
            # Apply the changes
            update_result = self.update_file(file_path, final_content)
            
            if update_result and update_result.get('status') == 'updated':
                print(f"✅ File updated successfully: {file_path}")
                return self._build_detailed_success_message(file_path, successes, failures, update_result, "diff blocks")
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
        
        # Add backend restart instruction if this is a backend file
        if self._is_backend_file(file_path):
            success_msg += f"\n\n🚨 IMPORTANT: Backend file updated! You MUST restart the backend to apply these changes:"
            success_msg += f"\n   Use <action type=\"restart_backend\"/> to redeploy the backend with the latest changes."
            success_msg += f"\n   The backend will not reflect these changes until redeployed."
        
        return success_msg
    
    def _build_detailed_success_message(self, file_path: str, successes: list, failures: list, update_result: dict, method: str) -> str:
        """Build a detailed success message with partial failure guidance"""
        if not failures:
            # Complete success
            message = f"✅ SUCCESS: File '{file_path}' updated completely using {method}.\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"📊 CHANGES APPLIED ({len(successes)} total):\n"
            for i, success in enumerate(successes, 1):
                message += f"   {i}. {success}\n"
            message += f"\n🎉 All diff blocks were successfully applied!"
            
            # Add backend restart instruction if this is a backend file
            if self._is_backend_file(file_path):
                message += f"\n\n🚨 IMPORTANT: Backend file updated! You MUST restart the backend to apply these changes:"
                message += f"\n   Use <action type=\"restart_backend\"/> to redeploy the backend with the latest changes."
                message += f"\n   The backend will not reflect these changes until redeployed."
            
            return message
        else:
            # Partial success
            message = f"⚠️  PARTIAL SUCCESS: File '{file_path}' updated with {len(successes)} of {len(successes) + len(failures)} changes.\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if successes:
                message += f"✅ SUCCESSFUL CHANGES ({len(successes)}):\n"
                for i, success in enumerate(successes, 1):
                    message += f"   {i}. {success}\n"
                message += f"\n"
            
            message += f"❌ FAILED CHANGES ({len(failures)}) - Need your attention:\n"
            for i, failure in enumerate(failures, 1):
                message += f"   {i}. {failure}\n"
            
            message += f"\n🔧 TO COMPLETE THE REMAINING UPDATES:\n"
            message += f"   1. Read the file again to see current state after partial update\n"
            message += f"   2. Create new update_file actions for the failed changes\n"
            message += f"   3. Use exact text matching for the SEARCH blocks\n"
            message += f"   4. Consider smaller, more targeted diff blocks\n"
            
            return message
    
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
    
    def _is_backend_file(self, file_path: str) -> bool:
        """Check if the updated file is a backend file that requires restart"""
        if not file_path:
            return False
        
        # Normalize path
        normalized_path = file_path.lower()
        
        # Check if file is in backend directory or has backend-related patterns
        backend_indicators = [
            '/backend/',
            'backend/',
            'app.py',
            'routes/',
            'api_',
            'server.py',
            'main.py',
            '.py'  # Any Python file could be backend code
        ]
        
        # Check for backend indicators
        for indicator in backend_indicators:
            if indicator in normalized_path:
                # Additional check: exclude frontend files that might be in backend folder
                if not any(frontend_pattern in normalized_path for frontend_pattern in [
                    'frontend/', 'src/', 'components/', '.tsx', '.jsx', '.js', '.ts', '.vue', '.html', '.css'
                ]):
                    return True
        
        return False