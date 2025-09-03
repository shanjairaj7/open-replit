# Claude Code Workflow Instructions

## Significant Feature Implementation Workflow

**CRITICAL**: For significant features or complex implementations, always follow this structured approach:

### 1. **Research & Understanding Phase**
Before starting any significant feature implementation:

- **Read existing files**: Study the current implementation, dependencies, parent files, and related functions
- **Understand the codebase**: Analyze how similar features are already implemented
- **Identify patterns**: Look for existing architectural patterns, naming conventions, and code organization
- **Map dependencies**: Understand how different components interact and depend on each other

### 2. **Planning Phase**
Create a comprehensive plan before coding:

- **Create plan document**: Write a detailed plan in the `/plans/` folder as a Markdown file
- **Include task tracking**: Break down the implementation into specific, trackable tasks
- **Define interfaces**: Specify API endpoints, data structures, and integration points
- **Consider edge cases**: Plan error handling, validation, and failure scenarios

### 3. **Iterative Implementation**
Implement the feature systematically:

- **Follow the plan**: Implement tasks in the planned order
- **Update task tracking**: Mark tasks as completed and update progress
- **Test iteratively**: Verify each component works before moving to the next
- **Maintain consistency**: Follow existing code patterns and conventions

### 4. **Continuous Learning**
Always expand knowledge of the codebase:

- **Learn from user instructions**: Pay attention to specific requirements and preferences
- **Study architectural decisions**: Understand why certain patterns are used
- **Document discoveries**: Note important findings about how the system works
- **Build context**: Continuously improve understanding of the overall system design

## Boilerplate Update Workflow

**IMPORTANT**: Whenever making changes to boilerplate code, always follow this sequence:

### After modifying `backend-boilerplate-clone/` or `frontend-boilerplate-clone/`:

1. **Git commit and push changes**:
   ```bash
   git add .
   git commit -m "Update boilerplate: [describe changes]"
   git push
   ```

2. **Clear the project pool** to ensure fresh boilerplates are used:
   ```bash
   python3 backend/api_server/clear_project_pool.py
   ```

This ensures that:
- All boilerplate changes are persisted to the repository
- The system project pool is cleared from Azure storage
- Cached boilerplates are removed from `/tmp/boilerplate_cache`
- Next project allocation will use the updated boilerplate code

### Why This Matters
The project pool manager caches boilerplates for performance. Without clearing the pool after changes, new projects would continue using the old cached versions instead of your updated code.

## Key Codebase Learnings

### Meta Architecture Understanding

**CRITICAL - MEMORIZE THIS**: This is a meta-development system - a platform that generates platforms.

#### The System Overview
This is **NOT** a single application. This is a **meta-development platform** where:
- **A coding LLM** creates custom full-stack applications for end users
- **Each generated application** becomes an independent, deployed system
- **We are building the infrastructure** that enables this automated app generation

#### The Complete Meta-Development Flow
1. **Template Phase**: `frontend-boilerplate-clone/` + `backend-boilerplate-clone/` are template folders
2. **Generation Phase**: Coding LLM customizes these templates to create user-specific applications
3. **Deployment Phase**: Each generated application gets deployed as independent backend on Modal.com
4. **Management Phase**: Central streaming API manages all deployed applications remotely
5. **Operation Phase**: End users interact with their individual generated applications

#### System Architecture Layers

**Layer 1: Templates** (What we modify)
- `backend-boilerplate-clone/app.py` = Template backend code
- `frontend-boilerplate-clone/` = Template frontend code
- Changes here affect ALL future generated applications

**Layer 2: Generated Applications** (What gets created)
- Each user request → New customized application
- Each application = Unique Modal deployment with own URL
- Each deployment = Independent database, API endpoints, resources

**Layer 3: Management System** (How we control everything)
- `streaming_api.py` = Central command center
- Manages hundreds/thousands of deployed applications
- Routes requests to specific deployed backend URLs
- Provides unified interface for multi-application management

#### Critical Data Flow Understanding
```
Developer modifies boilerplate →
Clear project pool →
Next user request →
LLM generates new app using updated boilerplate →
App gets deployed to Modal with unique URL →
Streaming API discovers URL via /backend/info →
Streaming API calls deployed app's /_internal/ endpoints →
User manages their specific app's data
```

#### Why Internal Endpoints Matter
- **Every deployed backend** contains `/_internal/` endpoints (from boilerplate template)
- **These are stealth APIs** built into each generated application
- **Streaming API** uses these to remotely manage each deployed application
- **Database editor** works by calling `/_internal/db/` on specific deployed backends
- **Each application** has completely isolated data and functionality

#### The Meta Implication
When we add features to boilerplate:
- **NOT** adding to one application
- **Adding to the template** that generates thousands of applications
- **Every future generated app** will have this feature
- **Existing deployed apps** keep their current version (no automatic updates)

### Architecture Patterns
- **Stealth APIs**: Internal endpoints use `include_in_schema=False` to hide from OpenAPI docs (e.g., `/_internal/db/inspect`)
- **Azure Client Separation**: Use `get_general_azure_client()` vs `get_streaming_azure_client()` to prevent resource contention
- **Caching Strategy**: Short-term caching (10-25s) with strategic cache invalidation for performance
- **Error Handling**: Always include actionable suggestions and "redeploy backend" messages for user guidance

### Code Organization in Meta-Development Context

**Template Layer** (boilerplate-clone folders):
- **Backend Boilerplate**: Template with `/_internal/` endpoints that get embedded in every generated application
- **Frontend Boilerplate**: Template UI code that gets customized for each generated application
- **Modifications here**: Affect every future generated application (template inheritance)

**Generated Application Layer** (deployed instances):
- **Each Generated Backend**: Independent Modal deployment with unique URL and database
- **JSON Database**: Isolated per application (tables as JSON arrays, auto-generated fields)
- **Internal Endpoints**: Copy of template's `/_internal/` endpoints for remote management
- **Complete Isolation**: No shared resources between generated applications

**Management Layer** (streaming API):
- **Central Command Center**: `streaming_api.py` manages all generated applications
- **Multi-Application Router**: Discovers deployed URLs and routes requests appropriately
- **Unified Interface**: Single API to manage hundreds of independent deployed applications
- **Cross-Application Features**: Database editor, deployment management, monitoring

### Integration Patterns
- **HTTP Client**: Use `aiohttp.ClientSession` with timeouts for backend-to-backend communication
- **Request/Response**: Standardized response format with `status`, `data`, `call_info`, and error details
- **Validation**: Comprehensive input validation with specific error messages
- **Documentation**: Always update endpoint documentation in the `if __name__ == "__main__"` section

### Integration Patterns in Meta-Development Context
- **Template-to-Template**: Modifications in boilerplate affect template inheritance
- **Management-to-Deployed**: Streaming API calls deployed backends via discovered URLs
- **Cross-Application Communication**: Unified patterns for managing distributed applications
- **Request/Response**: Standardized format works across all generated applications

### Development Impact Understanding
- **Boilerplate Changes**: Template modifications propagate to all future generated apps
- **Streaming API Changes**: Affect management capabilities across existing deployed apps
- **Database Schema**: Each generated app has independent schema and data
- **Feature Rollout**: New features added to template, existing apps keep current version
- **Scale Implications**: Changes affect potentially thousands of deployed applications

### User Preferences
- **Concise Responses**: Keep explanations brief, focus on direct answers
- **Task Tracking**: Use TodoWrite tool for complex implementations
- **Plan First**: Always create detailed plans in `backend/api_server/plans/` folder for significant features
- **Test Iteratively**: Syntax checks and incremental testing throughout development
- **Meta-Awareness**: Always consider template vs deployed vs management layer impacts
- > remember that whenever you make changes in the backend or frnotend boilerplate folders, you must git add and push them

## Documentation Management Workflow

When creating or updating technical documentation for the codebase platform:

### 1. **Create Documentation Locally**
- Write documentation in `/backend/llm_docs/` directory
- Use clear, concise markdown with practical examples
- Follow naming convention: `{topic}_{implementation}.md`
- Example: `llm_integration_openai.md`

### 2. **Upload to Azure Storage**
Documentation is stored in Azure Blob Storage for LLM access:
```bash
cd backend/api_server
python3 upload_docs.py
```

### 3. **How the System Works**
- **Storage**: Docs stored in Azure container `codebase-docs`
- **Access**: LLM can read docs via `tools.py` methods:
  - `list_docs()` - List all available docs
  - `search_docs(query)` - Search docs by name/content  
  - `download_doc(name)` - Read specific doc content
- **Integration**: Cloud storage methods in `cloud_storage.py`:
  - `upload_doc()` - Upload new documentation
  - `delete_all_docs()` - Clear existing docs
  - `delete_doc()` - Remove specific doc

### 4. **Benefits**
- **LLM Accessibility**: Documentation accessible to coding LLMs via tools
- **Centralized Storage**: All docs in one Azure location
- **Version Control**: Local files tracked in git, Azure contains current version
- **Searchable**: LLMs can search docs by content for relevant information

### 5. **Workflow Example**
1. Create `backend/llm_docs/new_feature_guide.md`
2. Run `python3 backend/api_server/upload_docs.py` 
3. LLM can now access via "docs" tool: `{"operation": "read", "doc_name": "new_feature_guide.md"}`
4. Commit local files to git for version control