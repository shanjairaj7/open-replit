# Next Phase: Multi-Step AI Project Generation System

## Current Status
- ✅ Streaming XML parser implemented and working
- ✅ Intelligent port allocation system working (3002/8002 ports)
- ✅ Dual container architecture (frontend + backend) operational
- ✅ Smart project naming based on user requests
- ✅ Real-time file creation during streaming
- ⚠️ Current issue: Model responses getting cut off before completion

## Problem Analysis
The current single-LLM-call approach has limitations:
1. **Token Limits**: Complex requests exceed model context/response limits
2. **Planning vs Implementation**: Model attempts both planning and coding in one go
3. **Context Loss**: Later files don't have sufficient context about earlier decisions
4. **Route Management**: Routes are created ad-hoc without overall architecture planning

## Proposed Solution: Multi-Step Generation Architecture

### Phase 1: Planning Stage
**Goal**: Get comprehensive implementation plan from LLM without any code generation

**Implementation**:
```python
def get_implementation_plan(user_request: str) -> dict:
    planning_prompt = f"""
    PLANNING ONLY - DO NOT GENERATE CODE
    
    User Request: {user_request}
    
    Create a comprehensive implementation plan with:
    
    1. **Feature Breakdown**: List all major features and sub-features
    2. **File Structure**: Complete list of files to be created
    3. **Route Architecture**: All frontend routes with components
    4. **Backend API Endpoints**: All API endpoints needed
    5. **Data Models**: Database/state structure
    6. **Implementation Order**: Step-by-step creation sequence
    
    Return as structured JSON:
    {{
        "features": [...],
        "files": {{
            "frontend": ["path/to/file.tsx", ...],
            "backend": ["path/to/file.py", ...]
        }},
        "routes": [
            {{"path": "/dashboard", "component": "Dashboard", "icon": "BarChart3", "label": "Dashboard"}},
            ...
        ],
        "api_endpoints": [
            {{"method": "GET", "path": "/api/tasks", "description": "List all tasks"}},
            ...
        ],
        "implementation_order": [
            {{"step": 1, "type": "model", "files": ["backend/models/task.py"]}},
            {{"step": 2, "type": "service", "files": ["backend/services/task_service.py"]}},
            {{"step": 3, "type": "component", "files": ["frontend/src/components/TaskCard.tsx"]}},
            ...
        ]
    }}
    """
```

### Phase 2: File Generation Stage
**Goal**: Generate each file individually with full context

**Implementation**:
```python
def generate_file_with_context(file_path: str, plan: dict, existing_files: dict) -> str:
    context_prompt = f"""
    Generate ONLY the file: {file_path}
    
    IMPLEMENTATION PLAN:
    {json.dumps(plan, indent=2)}
    
    EXISTING FILES CONTEXT:
    {format_existing_files_context(existing_files)}
    
    REQUIREMENTS:
    - Follow the implementation plan exactly
    - Use existing file patterns and imports
    - Ensure compatibility with already created files
    - Include proper TypeScript types and error handling
    - Use environment variables for API calls (VITE_API_URL)
    
    Generate the complete file content for: {file_path}
    """
```

### Phase 3: Route Registration
**Goal**: Register all routes from the plan automatically

**Implementation**:
```python
def register_routes_from_plan(plan: dict):
    for route in plan['routes']:
        # Use existing route registration system
        add_route_to_app(
            path=route['path'],
            component=route['component'], 
            icon=route['icon'],
            label=route['label'],
            group=route.get('group', 'Overview')
        )
```

## Detailed Implementation Strategy

### Step 1: Enhanced Planning System
```python
class MultiStepProjectGenerator:
    def __init__(self, api_key: str, project_name: str):
        self.client = Groq(api_key=api_key)
        self.project_name = project_name
        self.plan = None
        self.generated_files = {}
        
    async def generate_project(self, user_request: str):
        # Step 1: Get comprehensive plan
        self.plan = await self.get_implementation_plan(user_request)
        
        # Step 2: Register routes from plan
        await self.register_routes_from_plan()
        
        # Step 3: Generate files in planned order
        for step in self.plan['implementation_order']:
            for file_path in step['files']:
                content = await self.generate_file_with_context(file_path)
                await self.apply_file(file_path, content)
                self.generated_files[file_path] = content
                
        # Step 4: Start preview
        return await self.start_preview()
```

### Step 2: Context-Aware File Generation
Each file generation call will include:
- **Full implementation plan** as context
- **All previously generated files** for reference
- **Specific file requirements** and patterns
- **Import/export dependencies** from other files

### Step 3: Smart Implementation Ordering
Order files by dependency:
1. **Models/Types** → Define data structures first
2. **Backend Services** → API logic and validation  
3. **Frontend Hooks** → Data fetching and state management
4. **UI Components** → Individual components
5. **Pages** → Complete page assemblies
6. **Routes** → Navigation structure

### Step 4: Progress Tracking & Error Recovery
```python
class ProgressTracker:
    def __init__(self):
        self.completed_steps = []
        self.failed_steps = []
        self.current_step = None
        
    def can_retry_failed_step(self, step):
        # Retry logic with context from successful steps
        pass
        
    def get_completion_percentage(self):
        return len(self.completed_steps) / len(self.total_steps) * 100
```

## Benefits of Multi-Step Approach

### 1. **No Token Limits**
- Each file generation is a separate, focused LLM call
- No risk of response cutoff
- Can handle arbitrarily complex projects

### 2. **Better Context Management**  
- Each file knows about all previously created files
- Consistent imports, exports, and patterns
- Proper TypeScript type sharing

### 3. **Improved Quality**
- Focused generation = higher quality per file
- Better error handling and edge cases
- More comprehensive implementations

### 4. **Debugging & Recovery**
- Can retry individual failed files
- Clear progress tracking
- Easier to identify and fix issues

### 5. **Scalability**
- Can handle enterprise-level project complexity
- Parallel file generation possible
- Incremental updates and modifications

## Implementation Timeline

### Phase A: Planning System (1-2 days)
- Implement comprehensive planning prompt
- JSON parsing and validation
- Plan storage and retrieval

### Phase B: Multi-Step Generation (2-3 days)
- File-by-file generation system
- Context building and management
- Implementation ordering logic

### Phase C: Enhanced UX (1 day)
- Progress indicators
- Real-time file creation display
- Error handling and retry logic

### Phase D: Testing & Optimization (1 day)
- Test with complex projects
- Performance optimization
- Error recovery testing

## Expected Outcomes

With this multi-step approach, we should be able to generate:
- **Complete enterprise applications** with 50+ files
- **Consistent architecture** across all components
- **Production-ready code** with proper error handling
- **Complex features** like authentication, real-time updates, charts
- **Scalable project structures** that can grow over time

## Next Actions

1. **Implement planning prompt** and test with complex requests
2. **Build file generation queue** system
3. **Test with the current task management request** to validate approach
4. **Iterate based on results** and user feedback

This approach transforms the system from a single-shot code generator to a comprehensive development assistant that can handle any level of complexity.