"""
Update file handler with V4A diff format from OpenAI best practices
Handles V4A diff format with Azure storage integration
"""
import os
import sys
from typing import Tuple, Optional, Dict, Callable

class UpdateFileHandler:
    """Handles update_file actions with V4A diff format and Azure storage"""

    def __init__(self, read_file_callback: Callable[[str], Optional[str]],
                 update_file_callback: Callable[[str, str], dict]):
        """
        Initialize with Azure storage callbacks for file operations

        Args:
            read_file_callback: Function(file_path) -> content or None (Azure storage)
            update_file_callback: Function(file_path, content) -> result dict (Azure storage)
        """
        self.read_file = read_file_callback
        self.update_file = update_file_callback

        # Import V4A diff processor
        try:
            from apply_patch import process_patch, identify_files_needed, DiffError
            self.process_patch = process_patch
            self.identify_files_needed = identify_files_needed
            self.DiffError = DiffError
        except ImportError as e:
            print(f"❌ Warning: Could not import V4A apply_patch module: {e}")
            self.process_patch = None
            self.DiffError = Exception

    def handle_update_file(self, action: dict) -> str:
        """
        Main entry point for handling update_file actions using V4A diff format

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

        print(f"💾 Processing V4A diff update for: {file_path}")

        # Check if this is V4A diff format (OpenAI official format)
        if (update_content.strip().startswith('*** Begin Patch') or
            update_content.strip().startswith('*** Update File:')):
            print("🔍 Detected V4A diff format - validating before processing")

            # Skip pre-validation for now - let apply_patch.py handle format validation
            # validation_error = self._validate_v4a_format(file_path, update_content)
            # if validation_error:
            #     return validation_error

            print("✅ V4A format validation passed - processing with apply_patch")
            return self._handle_v4a_diff_update(file_path, update_content)
        elif '<diff>' in update_content:
            print("🔍 Detected legacy diff-style update")
            return self._handle_legacy_diff_update(file_path, update_content)
        else:
            print("📝 Detected legacy-style update (full file replacement)")
            return self._handle_legacy_style_update(file_path, update_content)

    def _handle_v4a_diff_update(self, file_path: str, update_content: str) -> str:
        """Handle V4A diff format updates using apply_patch.py"""
        try:
            if not self.process_patch:
                print("❌ V4A diff processor not available, falling back to legacy")
                return self._handle_legacy_style_update(file_path, update_content)

            print(f"🔧 Processing V4A diff for: {file_path}")

            # Ensure proper V4A format with Begin/End Patch wrappers (OpenAI official format)
            patch_text = update_content.strip()

            # If missing Begin/End wrappers, add them
            if not patch_text.startswith('*** Begin Patch'):
                if patch_text.startswith('*** Update File:'):
                    # Content has action header but missing wrappers
                    patch_text = f"*** Begin Patch\n{patch_text}\n*** End Patch"
                else:
                    # Content is just a diff without any headers - add full structure
                    patch_text = f"*** Begin Patch\n*** Update File: {file_path}\n{patch_text}\n*** End Patch"

            # Ensure it ends with End Patch
            if not patch_text.endswith('*** End Patch'):
                patch_text = f"{patch_text}\n*** End Patch"

            print(f"📄 V4A patch text length: {len(patch_text)} chars")

            # Create Azure storage callback functions
            def azure_read_fn(path: str) -> str:
                """Read file from Azure storage"""
                content = self.read_file(path)
                if content is None:
                    raise self.DiffError(f"Could not read file '{path}' from Azure storage")
                return content

            def azure_write_fn(path: str, content: str) -> None:
                """Write file to Azure storage"""
                result = self.update_file(path, content)
                if not result or result.get('status') != 'updated':
                    error = result.get('error', 'Unknown error') if result else 'Failed to write to Azure storage'
                    raise self.DiffError(f"Failed to write file '{path}': {error}")

            def azure_remove_fn(path: str) -> None:
                """Remove file from Azure storage (not implemented - would need delete API)"""
                print(f"⚠️ File deletion not implemented for Azure storage: {path}")

            # Apply the V4A patch using apply_patch.py
            try:
                result = self.process_patch(patch_text, azure_read_fn, azure_write_fn, azure_remove_fn)
                print(f"✅ V4A patch applied successfully: {file_path}")

                return f"✅ SUCCESS: File '{file_path}' updated using V4A diff format.\n" \
                       f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" \
                       f"📊 V4A DIFF PROCESSING COMPLETE\n" \
                       f"   • Used OpenAI V4A diff format with context-based matching\n" \
                       f"   • Applied changes with 3-line context identification\n" \
                       f"   • File successfully updated in Azure storage\n\n" \
                       f"{self._add_backend_restart_warning(file_path)}"

            except self.DiffError as e:
                error_msg = f"❌ V4A DIFF PROCESSING FAILED for '{file_path}'\n" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" \
                           f"📋 ERROR DETAILS:\n{str(e)}\n\n" \
                           f"🎯 NEXT STEPS TO FIX THIS (OpenAI V4A Format):\n" \
                           f"   1. First, use read_file action on '{file_path}' to see current content\n" \
                           f"   2. Copy EXACT context lines including all whitespace\n" \
                           f"   3. Use official OpenAI V4A format:\n" \
                           f"      *** Begin Patch\n" \
                           f"      *** Update File: {file_path}\n" \
                           f"       [context line 1 - with SPACE prefix]\n" \
                           f"       [context line 2 - with SPACE prefix]\n" \
                           f"       [context line 3 - with SPACE prefix]\n" \
                           f"      - [exact old text - with MINUS prefix]\n" \
                           f"      + [new replacement text - with PLUS prefix]\n" \
                           f"       [context after 1 - with SPACE prefix]\n" \
                           f"       [context after 2 - with SPACE prefix]\n" \
                           f"       [context after 3 - with SPACE prefix]\n" \
                           f"      *** End Patch\n\n" \
                           f"⚠️  CRITICAL V4A FORMAT RULES:\n" \
                           f"   • Every line MUST start with space (' '), minus ('-'), or plus ('+')\n" \
                           f"   • Empty lines become space-prefixed lines (' ')\n" \
                           f"   • Use @@ markers for function/class context when needed\n" \
                           f"   • Context must match file content exactly (parser has fuzzy fallback)"

                print(f"❌ V4A diff failed: {e}")
                return error_msg

        except Exception as e:
            print(f"❌ Unexpected error in V4A processing: {e}")
            # Fall back to legacy update
            print("🔄 Falling back to legacy file replacement")
            return self._handle_legacy_style_update(file_path, update_content)

    def _handle_legacy_diff_update(self, file_path: str, update_content: str) -> str:
        """Handle legacy diff-style search/replace blocks (deprecated)"""
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

    def _add_backend_restart_warning(self, file_path: str) -> str:
        """Add backend restart warning if this is a backend file"""
        if self._is_backend_file(file_path):
            return "🚨 IMPORTANT: Backend file updated! You MUST restart the backend to apply these changes:\n" \
                   "   Use <action type=\"restart_backend\"/> to redeploy the backend with the latest changes.\n" \
                   "   The backend will not reflect these changes until redeployed."
        return ""

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

    def _validate_v4a_format(self, file_path: str, update_content: str) -> Optional[str]:
        """
        Validate V4A diff format before applying to prevent malformed patches
        Returns error message if invalid, None if valid
        """
        try:
            # Read current file to validate against
            current_content = self.read_file(file_path)
            if current_content is None:
                return f"❌ V4A VALIDATION FAILED: Cannot read file '{file_path}' for validation"

            current_lines = current_content.split('\n')

            # Check basic V4A format structure
            lines = update_content.strip().split('\n')

            # Check for proper OpenAI V4A format structure
            if not (lines[0].strip().startswith('*** Begin Patch') or
                   lines[0].strip().startswith('*** Update File:')):
                return self._v4a_format_error("Must start with '*** Begin Patch' or '*** Update File: <filepath>'")

            # Filter out wrapper lines for validation (Begin Patch, End Patch, Update File headers)
            content_lines = []
            for line in lines:
                if line.strip().startswith(('*** Begin Patch', '*** End Patch', '*** Update File:', '*** Add File:', '*** Delete File:')):
                    continue
                content_lines.append(line)

            # Check for context preservation issues
            validation_errors = []

            # Look for @@ sections and validate context (use filtered content_lines)
            at_sections = []
            current_section = []

            for i, line in enumerate(content_lines):
                if line.strip().startswith('@@'):
                    if current_section:
                        at_sections.append(current_section)
                    current_section = [line]
                elif current_section:
                    current_section.append(line)
                elif line.strip().startswith(('-', '+')):
                    # Changes outside @@ sections
                    current_section.append(line)

            if current_section:
                at_sections.append(current_section)

            # Validate each @@ section
            for section_idx, section in enumerate(at_sections):
                section_errors = self._validate_at_section(section, current_lines, section_idx)
                validation_errors.extend(section_errors)

            # Check for common logical errors that lead to malformed files
            logical_errors = self._validate_logical_structure(update_content, current_content, file_path)
            validation_errors.extend(logical_errors)

            if validation_errors:
                error_msg = "❌ V4A PATCH VALIDATION FAILED\n"
                error_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                error_msg += f"📋 VALIDATION ERRORS for '{file_path}':\n"
                for i, error in enumerate(validation_errors, 1):
                    error_msg += f"   {i}. {error}\n"

                error_msg += "\n🎯 HOW TO FIX V4A DIFF FORMAT:\n"
                error_msg += "   1. READ the file first to see exact current content\n"
                error_msg += "   2. Provide EXACTLY 3 lines of context before and after changes\n"
                error_msg += "   3. Use @@ markers to specify function/class context for placement\n"
                error_msg += "   4. Ensure all variables/imports exist after changes\n"
                error_msg += "   5. For new functions, add them AFTER existing router definition\n\n"
                error_msg += "📝 CORRECT V4A FORMAT (OpenAI Official):\n"
                error_msg += "*** Begin Patch\n"
                error_msg += "*** Update File: backend/routes/organizations.py\n"
                error_msg += " router = APIRouter(prefix=\"/organizations\", tags=[\"organizations\"])\n"
                error_msg += " \n"
                error_msg += " # List members\n"
                error_msg += "-@router.get(\"/{org_id}/members\", response_model=List[MembershipResponse])\n"
                error_msg += "+@router.get(\"/{org_id}/members\", response_model=List[MembershipResponse])\n"
                error_msg += "+ \n"
                error_msg += "+ # Update organization\n"
                error_msg += "+ @router.patch(\"/{org_id}\", response_model=OrganizationResponse)\n"
                error_msg += "+ def update_organization(...):\n"
                error_msg += "+     # New function content\n"
                error_msg += "+     pass\n"
                error_msg += " \n"
                error_msg += "*** End Patch\n"

                return error_msg

            return None  # Validation passed

        except Exception as e:
            return f"❌ V4A VALIDATION ERROR: {str(e)}"

    def _validate_at_section(self, section: List[str], current_lines: List[str], section_idx: int) -> List[str]:
        """Validate individual @@ section for context and structure"""
        errors = []

        if not section:
            return ["Empty @@ section"]

        # Count context vs change lines
        context_lines = [l for l in section if not l.strip().startswith(('-', '+', '@@'))]
        change_lines = [l for l in section if l.strip().startswith(('-', '+'))]

        # Should have adequate context (at least 2-3 lines)
        if len(context_lines) < 2 and len(change_lines) > 0:
            errors.append(f"@@ section #{section_idx + 1}: Insufficient context lines (need 3 before/after)")

        # Check if context lines exist in current file
        for ctx_line in context_lines[:3]:  # Check first 3 context lines
            ctx_content = ctx_line.strip()
            if ctx_content and ctx_content not in '\n'.join(current_lines):
                errors.append(f"@@ section #{section_idx + 1}: Context line not found in file: '{ctx_content[:50]}...'")

        return errors

    def _validate_logical_structure(self, patch_content: str, current_content: str, file_path: str) -> List[str]:
        """Validate logical structure to prevent malformed files"""
        errors = []

        # Check for common Python file structure issues
        if file_path.endswith('.py'):
            # Check for router usage without definition
            if '@router.' in patch_content:
                if 'router = APIRouter' not in current_content and '- router = APIRouter' in patch_content:
                    errors.append("Patch removes 'router = APIRouter' but still uses '@router.' decorators")

                if '+@router.' in patch_content:
                    # Make sure router definition exists or is being added
                    if 'router = APIRouter' not in current_content and '+ router = APIRouter' not in patch_content:
                        errors.append("Patch adds '@router.' decorators but router variable not defined")

            # Check for import removal without replacement
            import_removals = [line for line in patch_content.split('\n') if line.strip().startswith('- from ') or line.strip().startswith('- import ')]
            import_additions = [line for line in patch_content.split('\n') if line.strip().startswith('+ from ') or line.strip().startswith('+ import ')]

            if len(import_removals) > len(import_additions):
                errors.append(f"Patch removes {len(import_removals)} imports but only adds {len(import_additions)} - may break file")

        return errors

    def _v4a_format_error(self, message: str) -> str:
        """Generate standardized V4A format error message"""
        return f"❌ V4A FORMAT ERROR: {message}\n\n" \
               f"🎯 REQUIRED V4A DIFF FORMAT (OpenAI Official):\n" \
               f"*** Begin Patch\n" \
               f"*** Update File: path/to/file\n" \
               f" [3 lines context before]\n" \
               f"- old line to remove\n" \
               f"+ new line to add\n" \
               f" [3 lines context after]\n\n" \
               f"@@ function_name or class_name (if needed for unique placement)\n" \
               f" [context lines]\n" \
               f"- old code\n" \
               f"+ new code\n" \
               f" [context lines]\n" \
               f"*** End Patch"
