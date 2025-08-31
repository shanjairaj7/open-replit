# Search/Replace Format Implementation

## Overview
Successfully replaced the V4A diff format with a more reliable search/replace block format for better accuracy when file content contains dashes or other special characters.

## Changes Made

### 1. Updated Prompt System (`simpler_prompt.py`)
- Replaced all V4A diff format examples with search/replace format
- Updated format instructions from `*** Begin Patch` to `------- SEARCH` / `+++++++ REPLACE`
- Added comprehensive rules for exact matching and block structure
- Updated all examples in todo app, CRM analytics, and other sections

### 2. Enhanced DiffParser (`diff_parser.py`)
- Added support for direct search/replace format without `<diff>` tags
- Implemented `_parse_direct_search_replace()` method
- Added pattern matching for both `+++++++ REPLACE` and simple `=======` formats
- Support for multiple search/replace blocks in single content

### 3. Integrated UpdateFileHandler (`update_file_handler.py`)
- Added DiffParser import and initialization
- Implemented search/replace format detection logic
- Created `_handle_search_replace_update()` method
- Added comprehensive error handling with detailed instructions
- Maintained backward compatibility with V4A and legacy formats

## New Format Structure

```
------- SEARCH
[exact content to find]
=======
[new content to replace with]
+++++++ REPLACE
```

### Format Rules
1. **Exact Matching**: SEARCH content must match file content character-for-character
2. **Single Occurrence**: Each block replaces only the first match found
3. **Multiple Changes**: Use multiple SEARCH/REPLACE blocks for multiple changes
4. **Concise Blocks**: Keep SEARCH sections small and unique
5. **Complete Lines**: Never truncate lines mid-way
6. **Order Matters**: Process blocks in file order (top to bottom)

## Format Detection Priority

1. **Search/Replace Format** (NEW - Preferred)
   - Detected by presence of `------- SEARCH` markers
   - Processed by DiffParser with exact string matching

2. **V4A Diff Format** (Legacy)
   - Detected by `*** Begin Patch` or `*** Update File:` markers
   - Processed by apply_patch.py with context-based matching

3. **Legacy Diff Format** (Deprecated)
   - Detected by `<diff>` tags
   - Processed by DiffParser with legacy patterns

4. **Full File Replacement** (Fallback)
   - No special markers detected
   - Replaces entire file content

## Error Handling

### Search Failures
- Detailed error messages with closest match analysis
- Step-by-step fix instructions
- Common mistake warnings (indentation, whitespace, etc.)
- Line number and context information

### Format Issues
- Automatic fallback to legacy formats if search/replace fails
- Import error handling for missing modules
- Graceful degradation to full file replacement

## Testing Results

✅ **Basic Search/Replace**: Single block replacement works correctly  
✅ **Multiple Blocks**: Multiple search/replace pairs in single action  
✅ **Error Handling**: Failed searches provide helpful error messages  
✅ **Format Detection**: Correctly identifies search/replace format  
✅ **Edge Cases**: Various format variations handled properly  
✅ **Backward Compatibility**: V4A and legacy formats still work  

## Benefits

1. **Better Accuracy**: Exact string matching vs fuzzy context matching
2. **Clearer Format**: More intuitive than V4A diff syntax
3. **Detailed Errors**: Specific guidance when searches fail
4. **Multiple Formats**: Support for various search/replace patterns
5. **Maintained Compatibility**: Existing V4A patches still work

## Usage Examples

### Simple Replacement
```
<action type="update_file" path="example.py">
------- SEARCH
def old_function():
    return "old"
=======
def old_function():
    return "new"
+++++++ REPLACE
</action>
```

### Multiple Changes
```
<action type="update_file" path="config.py">
------- SEARCH
DEBUG = True
=======
DEBUG = False
+++++++ REPLACE

------- SEARCH
VERSION = "1.0"
=======
VERSION = "1.1"
+++++++ REPLACE
</action>
```

## Implementation Status
🎉 **COMPLETE** - All planned features implemented and tested successfully!