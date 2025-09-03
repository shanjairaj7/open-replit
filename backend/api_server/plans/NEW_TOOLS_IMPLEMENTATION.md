# New Tools Implementation Plan: list_files and docs Actions

## Overview
Adding two new tools to tools.py while keeping ALL existing tool handlers in base_test_azure_hybrid.py unchanged.

## Phase 1: Setup tools.py Infrastructure ✅ COMPLETED
### Tasks:
- [x] Create ToolsManager class in tools.py
- [x] Add __init__ with cloud_storage, project_id, read_files tracking dependencies  
- [x] Add debug prints for initialization
- [x] Test basic instantiation

### Dependencies Analyzed:
- cloud_storage: AzureBlobStorage instance
- project_id: string
- read_files_tracker: set (current session)
- read_files_persistent: set (across sessions)

## Phase 2: Implement list_files Action ✅ COMPLETED  
### Tasks:
- [x] Add handle_list_files method to ToolsManager
- [x] Extend cloud_storage.py list_files method for path filtering
- [x] Add list_files action definition to prompts/simpler_prompt.py
- [x] Add _handle_list_files_interrupt delegation method in base_test_azure_hybrid.py
- [x] Add ToolsManager instantiation in base_test_azure_hybrid.py __init__
- [x] Add list_files routing in index_fixed_azure_hybrid.py coder function
- [x] Test list_files functionality

### Action Syntax:
```xml
<action type="list_files" path="frontend/src/components"/>
<action type="list_files"/>  <!-- lists all files -->
```

### Implementation Details:
- Uses existing cloud_storage.list_files() as base
- Adds path filtering capability
- Returns formatted file list with relative paths
- Simple error handling with prints

## Phase 3: Setup docs Infrastructure ✅ COMPLETED 
### Tasks:
- [x] Create 'codebase-docs' container in Azure Storage
- [x] Add sample documentation files to container:
  - [x] api_reference.md
  - [x] authentication_guide.md  
  - [x] deployment_guide.md
  - [x] troubleshooting.md
- [x] Test docs container accessibility

### Sample Docs Content:
- API reference with endpoints
- Authentication and security guidelines  
- Deployment procedures
- Common troubleshooting steps

## Phase 4: Implement docs Action System ✅ COMPLETED
### Tasks:
- [x] Add docs methods to cloud_storage.py:
  - [x] list_docs() - list all available docs
  - [x] search_docs(query) - search docs by content/title
  - [x] download_doc(doc_name) - get specific doc content
- [x] Add handle_docs method to ToolsManager with operation switching
- [x] Add docs action definitions to prompts/simpler_prompt.py
- [x] Add _handle_docs_interrupt delegation method in base_test_azure_hybrid.py  
- [x] Add docs routing in index_fixed_azure_hybrid.py coder function
- [x] Test all docs operations

### Action Syntax:
```xml
<action type="docs" operation="list"/>
<action type="docs" operation="search" query="authentication api"/>
<action type="docs" operation="read" doc_name="api_reference.md"/>
```

### Implementation Details:
- Simple text search for search operation
- Returns doc names, content length for list
- Full content for read operation
- Basic error handling with prints

## Phase 5: Integration and Testing ✅ COMPLETED
### Tasks:
- [x] Test list_files with various paths
- [x] Test docs list/search/read operations  
- [x] Verify existing tools still work unchanged
- [x] Test error scenarios
- [x] Document usage examples

## Files Modified:
1. **tools.py** (CREATE) - ToolsManager with new methods
2. **cloud_storage.py** (EXTEND) - Add docs container support  
3. **prompts/simpler_prompt.py** (ADD) - New action definitions
4. **base_test_azure_hybrid.py** (ADD) - Delegation methods only
5. **index_fixed_azure_hybrid.py** (ADD) - New action routing

## Files Unchanged:
- All existing _handle_*_interrupt methods in base_test_azure_hybrid.py
- All existing action routing in index_fixed_azure_hybrid.py  
- All existing action definitions in prompts/simpler_prompt.py

## Success Criteria: ✅ ALL COMPLETED
- [x] list_files action works with/without path parameter
- [x] docs actions work for list/search/read operations
- [x] All existing tools continue working unchanged  
- [x] Clean separation between old tools (base_test) and new tools (tools.py)
- [x] Pattern established for future tools

## IMPLEMENTATION COMPLETED SUCCESSFULLY! 🎉

### What was implemented:
1. **ToolsManager** class in tools.py with proper dependency injection
2. **list_files action** that lists project files with optional path filtering
3. **docs actions** (list, search, read) that work with a separate docs container
4. **Integration** with existing codebase without changing any existing tools
5. **Sample documentation** in Azure Storage (4 files)
6. **Complete routing** in coder function and prompts

### Testing results:
- ✅ Docs container created with 4 sample files
- ✅ list_docs() returns: ['api_reference.md', 'authentication_guide.md', 'deployment_guide.md', 'troubleshooting.md']  
- ✅ search_docs('authentication') finds 3 matching docs
- ✅ download_doc('api_reference.md') returns 812 characters of content
- ✅ All tools properly integrated with existing infrastructure

## Implementation Notes:
- Keep code simple and functional
- Add prints for debugging  
- Clear property names for LLM understanding
- No over-engineering or complex abstractions
- Maintain backward compatibility