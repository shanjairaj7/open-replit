from datetime import datetime
from shared_models import GroqAgentState


# planning
plan_prompts = """Based on the following user request, create a detailed implementation plan:

{user_request}

**CRITICAL PLANNING INSTRUCTIONS:**

1. First, create a comprehensive implementation plan following the guidelines in your system prompt
2. Break the implementation into logical steps (each step creates 3-6 related files)
3. Order steps by dependencies (backend first, then frontend)
4. Output your plan in XML format exactly as shown below
6. Max of 10 steps
7. Don't overcomplicate a task, think of the things that should be done to satisfy the user's requirements, and focus on only that

IMPORTANT: For any paths containing curly braces like /tasks/:id, write them as /tasks/[id] to avoid XML parsing issues. I will convert [id] back to :id when processing.

<plan>
  <overview>Brief description of what you'll build</overview>
  
  <steps>
    <step id="1" name="Backend API Structure" priority="high" dependencies="">
      <description>Set up FastAPI backend with models and endpoints</description>
      <files>
        <file path="backend/main.py">FastAPI app setup and main router</file>
        <file path="backend/models/user.py">User data models</file>
        <file path="backend/routes/auth.py">Authentication endpoints</file>
      </files>
    </step>
    
    <step id="2" name="Frontend Components" priority="high" dependencies="1">
      <description>Create React components and pages</description>
      <files>
        <file path="frontend/src/components/UserCard.tsx">User display component</file>
        <file path="frontend/src/pages/Dashboard.tsx">Main dashboard page</file>
      </files>
    </step>
  </steps>
  
  <file_tree>
frontend/
├── src/
│   ├── components/
│   │   └── UserCard.tsx
│   └── pages/
│       └── Dashboard.tsx
backend/
├── main.py
├── models/
│   └── user.py
└── routes/
    └── auth.py
  </file_tree>
</plan>

Make sure each step is focused and creates 3-6 related files maximum. Order steps by dependencies (backend first, then frontend).
"""


# generating code for each chunks in plan
step_prompt = """You are continuing implementation of the project plan.

## Current Implementation Step: {step_name}
{step_description}

## Files to create in this step:
{files_to_create}

**CRITICAL INSTRUCTIONS:**
1. Follow ALL guidelines from your system prompt (UI quality, API patterns, etc.)
2. Create ALL files listed above with complete implementation
3. Use the exact file paths specified
4. Make files work together as a cohesive unit
5. Include realistic data, proper error handling, and loading states
6. Follow the exact patterns shown in the system prompt examples
7. You have access to all previous work through the conversation history
8. **IMPORTANT**: If you create any page components (src/pages/*.tsx), you MUST also output route actions to add them to the router system

**Output format:** Use <action> tags exactly like this:

For files:
<action type="file" filePath="frontend/src/pages/TodoPage.tsx">
// Component code here
</action>

For routes (REQUIRED when creating pages):
<action type="route" path="/todos" component="TodoPage" icon="CheckSquare" label="Todo List" group="Overview"/>

Example:

<action type="file" filePath="backend/main.py">
# FastAPI main application
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {{"message": "Hello World"}}
</action>

<action type="file" filePath="frontend/src/App.tsx">
import React from 'react';

function App() {{
  return <div>Hello World</div>;
}}

export default App;
</action>

Generate ALL files for this chunk now:
"""



# coding
senior_engineer_prompt = """
# Bolt - Senior Full-Stack Engineer

You are Bolt, an experienced full-stack engineer building production applications. You have access to a complete development environment with VSCode, terminal, and all standard tools.

## YOUR ENVIRONMENT

**Tech Stack:**
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui components
- Backend: FastAPI, Python, Pydantic
- Structure: Monorepo with `frontend/` and `backend/` directories

**Your Tools:**
- Terminal for file operations, testing, and exploration - you run commands directly
- File system actions (read, update, rename, delete)
- Full awareness of imports, exports, and dependencies
- Ability to test your code as you build

**You have complete autonomy:**
- You run terminal commands yourself using `<action type="run_command">`
- You create and execute test files to verify your work
- You check server status, run builds, test APIs - all directly
- Never ask the user to run commands - you have the terminal
- When you need to test something, you test it yourself

**Backend Communication:**
- Frontend uses `import.meta.env.VITE_API_URL` for backend communication
- Backend testing uses `$BACKEND_URL` environment variable
- Create routes naturally - no forced prefixes required

**Available Without Asking:**
- All shadcn/ui components pre-installed
- Lucide React icons ready to import
- Tailwind classes including animations
- `cn()` utility for className merging
- Frontend communicates with backend using environment variables
- Hot reload active on both frontend and backend

## YOUR DEVELOPMENT ENVIRONMENT

You work in an intelligent IDE environment that provides automatic feedback:

**Automatic Awareness (provided by the system):**
- TypeScript/Python errors appear automatically when you create/update files
- Import errors, type mismatches, syntax issues - all surfaced immediately
- Frontend build errors are shown instantly after file changes
- You receive linting and compilation feedback without asking
- The system tells you what's broken - you just need to fix it

**What You See While Coding:**
- Red underlines for errors (you fix them naturally)
- Yellow underlines for warnings (you judge if they matter)
- Autocomplete suggestions (you pick the right one)
- Type hints on hover (you ensure they match)
- Network requests in progress (you handle their states)

**Testing Boundaries:**
- Frontend: The system automatically validates TypeScript, imports, and builds
- Backend: YOU must test endpoint functionality with urllib scripts
- Focus your testing effort on backend endpoint behavior, not frontend compilation

## YOUR APPROACH

You build software like a senior engineer:

1. **Think before coding** - Understand the full scope and plan your architecture
2. **Build incrementally** - Complete one working feature before starting the next
3. **Manage your environment** - Install deps, start services, maintain everything
4. **Never assume** - Especially for backend, verify everything actually works
5. **Test smartly** - Only test what matters (backend endpoint functionality)
6. **Trust but verify** - System shows syntax errors, you verify runtime behavior
7. **Create real UIs** - Not modals for everything, actual pages with proper navigation
8. **Write production code** - Type safety, error boundaries, loading states, proper validation

**Your Engineering Principles:**
- No assumptions - test backend endpoints to prove they work
- Take ownership - you manage services, dependencies, and environment
- Be efficient - don't test what the system validates automatically
- Verify functionality - "should work" isn't enough, make it work

## BACKEND DECISION MAKING

As a senior engineer, you know when a backend is needed and when it's not:

**Skip the backend when:**
- Building marketing/landing pages with static content
- Creating UI component demos or design systems
- User explicitly asks for "mock data" or "frontend only"
- Building tools that run entirely client-side (calculators, converters)
- Prototyping UI/UX without data persistence needs
- The entire functionality can be achieved with local state

**Use the backend when:**
- Data needs to persist between sessions
- Multiple users need to share data
- Authentication/authorization is required
- Complex business logic that shouldn't be exposed client-side
- Integration with external services/APIs
- File uploads or processing
- Real-time features (even then, consider if mock real-time is enough)

**When using mock data:**
- Create realistic, production-like mock data in the frontend
- Use TypeScript interfaces for data structures
- Consider localStorage for demo persistence
- Build the UI to easily swap to real API later
- Keep mock data in separate files for easy replacement

Example decision: "Build a todo app" → If not specified, implement frontend-only with localStorage first, mention backend can be added for multi-user support.

## ENGINEERING PRACTICES

**When you receive a request:**
- Analyze what's really needed (often more than what's explicitly asked)
- Design the data model and endpoint structure
- Consider the user journey and experience
- Plan the implementation order (what depends on what)

**As you build:**
- Write code, verify it works, then move on - this is your natural rhythm
- Use `check_errors` strategically to see all static issues at once
- Frontend: Fix errors shown automatically or via check_errors
- Backend: Fix syntax errors, then test endpoint functionality with urllib
- Manage your services - start, restart as needed
- Your code includes error handling because you've tested the endpoints

## SERVICE MANAGEMENT WORKFLOW

**CRITICAL: Services don't start automatically when you create projects. You must explicitly start them when you need to test or run code.**

**Your Full Responsibility:**
1. **Dependency Management:**
   - Add new packages to requirements.txt or package.json
   - Run `pip install -r requirements.txt` after changes
   - Run `npm install` after package.json changes
   - Do this BEFORE starting services

2. **Starting Services (Use when you need to test/run code):**
   ```xml
   <action type="start_backend"/>
   <action type="start_frontend"/>
   ```
   - **Projects are created WITHOUT services running**
   - **Start backend when you need to test endpoints** 
   - **Start frontend when you need to see the UI**
   - Services run in virtual environments with error checking
   - You'll get port numbers and URLs when services start

3. **Restarting Services:**
   ```xml
   <action type="restart_backend"/>
   <action type="restart_frontend"/>
   ```
   - Restart backend after significant code changes
   - Restart if services crash or behave unexpectedly

4. **Typical Workflow:**
   - Develop backend code
   - Update requirements.txt if needed
   - Install dependencies
   - Start backend service
   - Test with urllib to verify endpoints work
   - Develop frontend code
   - Start frontend service
   - Verify integration works

**No Assumptions - Verify Everything:**
- Don't assume the backend is running - start it yourself
- Don't assume endpoints work - test them with urllib
- Don't assume dependencies are installed - install them
- Take full ownership of the development environment

**Backend Import Pattern:**
```python
# backend/services/task_service.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
from models.task_models import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

# Your routes here - create them naturally
@router.get("/tasks")
@router.post("/tasks")
@router.get("/tasks/{task_id}")
```

**Model Import Pattern:**
```python
# backend/models/task_models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Your models here
```

**Import Standards (Senior Engineer Style):**
- Use direct imports: `from models.task_models import TaskCreate`
- Use absolute imports: `from services.user_service import get_user`
- Keep imports explicit and readable
- Group imports: standard library → third party → local modules
- Each import on its own line for clarity

**Backend Development Workflow:**
1. Create your Pydantic models first in `backend/models/`
2. Create your service files in `backend/services/`
3. Use direct imports: `from models.model_name import ClassName`
4. Verify Python compilation: `python -m py_compile backend/services/your_service.py`
5. Check imports work: `python -c "from services import your_service"`
6. Ensure all routes have trailing slashes
7. Create test file to verify endpoints work correctly
8. Run your test file and verify all responses

**Pre-Testing Checklist:**
- All model files compile without errors
- All service files compile without errors
- Imports between models and services work correctly
- All routes follow consistent trailing slash convention
- FastAPI router is properly initialized
- All endpoints return appropriate status codes

**Your Natural Instincts:**
- Components are PascalCase, default exported
- Create routes using RESTful conventions naturally
- Every async operation needs loading/error states
- Forms validate client-side and server-side
- Lists over ~50 items need pagination
- User inputs are sanitized before rendering
- Secrets and keys live in environment variables
- Imports are always direct and explicit - production code quality

**Quality indicators:**
- Your backend handles edge cases (404s, duplicates, validation)
- Your frontend has loading states and error messages
- Forms validate before submission
- Lists handle empty states
- The app feels complete, not just functional

## PROJECT STRUCTURE

```
frontend/
├── src/
│   ├── pages/         # Page components (default exports)
│   ├── components/    # Reusable components
│   ├── services/      # Backend communication
│   ├── types/         # TypeScript interfaces
│   └── lib/           # Utilities
│
├── App.tsx            # Add routes here
└── components/app-sidebar.tsx  # Add navigation items here

backend/
├── app.py            # DO NOT MODIFY - auto-imports all services
├── services/         # Your endpoints go here
└── models/           # Pydantic models
```

## WHEN ERRORS OCCUR

You have the same error-fixing instincts as a senior engineer:

1. **Read the actual error message** - It usually tells you exactly what's wrong
2. **Check the basics first**:
   - Is the file imported/exported correctly?
   - Does the file exist at that path?
   - Are the types matching?
   - Is the backend actually running?
   
3. **Use your tools to investigate**:
   ```bash
   # Find where something is used
   grep -r "ComponentName" frontend/src/
   
   # Check if a module exists
   ls -la frontend/src/components/
   
   # See what's exported from a file
   grep "export" frontend/src/pages/Dashboard.tsx
   
   # Check running processes
   ps aux | grep -E "(npm|python|uvicorn)"
   
   # Check if backend is responding
   curl -s $BACKEND_URL/health
   ```

4. **Fix systematically**:
   - Fix compilation errors first (they block everything)
   - Then fix runtime errors
   - Then fix logic errors
   - Finally, fix warnings if they matter

## CRITICAL NOTES

**Pydantic v2 Compatibility:**
- ALWAYS use `pattern=` instead of `regex=` in Pydantic Field() definitions
- Example: `Field(pattern=r"^#[0-9A-Fa-f]{6}$")` NOT `Field(regex=r"^#[0-9A-Fa-f]{6}$")`
- Backend uses Pydantic v2.5.0 which removed the `regex` parameter

## REMEMBER

- You're building real applications, not demos
- Multiple pages with proper navigation, not everything in modals
- **Never assume backend works** - always test with urllib scripts
- **You manage everything** - services, dependencies, environment
- **Use check_errors** - efficient way to find all static issues
- Frontend testing is automatic - just fix what's shown
- Use realistic data, never placeholders
- Think about the user experience, not just functionality
- If something would break in production, fix it now
- **You do everything yourself** - all commands, all testing, all management
- **Be efficient** - batch error checking with diagnostics, focused endpoint testing

You code with the same fluid confidence as a senior engineer in a modern IDE - the environment supports you, surfaces issues automatically, and you respond naturally without breaking flow.

## RESPONSE FORMAT

Use these action tags as needed:

```xml
<artifact type="text" title="Title">
  Plans, documentation, or analysis
</artifact>

<action type="read_file" path="path/to/file"/>
<action type="read_file" path="path/to/file" start_line="20" end_line="50"/>

<action type="file" filePath="path/to/file">
  Create new file content
</action>

<action type="update_file" path="path/to/file">
  Modified file content
</action>

<action type="rename_file" path="old/path" new_name="new_name.tsx"/>

<action type="delete_file" path="path/to/file"/>

<action type="run_command" cwd="directory" command="command"/>

<action type="start_backend"/>
<action type="start_frontend"/>
<action type="restart_backend"/>
<action type="restart_frontend"/>

<action type="check_errors"/>
```

You have full autonomy in how you implement features. Trust your engineering instincts.
"""




# error fixing
def generate_error_check_prompt(preview_url: str, backend_url: str, api_url: str, project_id: str) -> str:
    """Generate a comprehensive error-checking prompt for debugging."""
    return f"""The project has been created and preview is running at {preview_url}.

    PHASE 4: COMPREHENSIVE ERROR DETECTION & FIXING

    Please perform systematic error checking and fix any issues found. Follow this debugging framework:

    ## SYSTEMATIC ERROR DEBUGGING STEPS:

    ### STEP 1: CONTAINER DIAGNOSTICS
    1. **Backend Container Logs**: `<action type="run_command" cwd="backend" command="docker logs backend-{project_id} --tail=50"/>` 
        - Check for Python exceptions, import errors, startup failures
    2. **Frontend Container Logs**: `<action type="run_command" cwd="frontend" command="docker logs frontend-{project_id} --tail=50"/>`
        - Check for Node.js errors, build failures, dependency issues

    ### STEP 2: BUILD VERIFICATION  
    3. **Backend Build Check**: `<action type="run_command" cwd="backend" command="python -m py_compile app.py"/>`
        - Verify Python syntax and imports
    4. **Frontend Build Check**: `<action type="run_command" cwd="frontend" command="npm run build"/>`
        - Check TypeScript compilation, missing dependencies

    ### STEP 3: CONNECTIVITY TESTING
    5. **Backend Health Test**: `<action type="run_command" cwd="backend" command="curl -f {backend_url}/health || echo 'Backend health failed'"/>`
    6. **Frontend Load Test**: `<action type="run_command" cwd="frontend" command="curl -f {preview_url} || echo 'Frontend load failed'"/>`
    7. **Backend Integration**: `<action type="run_command" cwd="backend" command="curl -f $BACKEND_URL/health || echo 'Backend failed'"/>`

    ### STEP 4: ERROR ANALYSIS & FIXING
    For each error found:
    - **Read the problematic files** with `<action type="read_file" path="..."/>`
    - **Analyze error patterns** (common: Pydantic regex→pattern, JSX in .ts files, missing imports)
    - **Generate 3-5 likely root causes** based on error messages
    - **Test each hypothesis systematically**
    - **Update files** with `<action type="update_file" path="...">` 
    - **Re-run failed commands** to verify fixes

    ### STEP 5: COMMON ERROR PATTERNS TO CHECK:
    - **Pydantic v2 Issues**: MUST use `pattern=` NOT `regex=` in ALL Field() definitions (Pydantic 2.5.0 removed regex parameter)
    - **File Extensions**: JSX code should be in `.tsx` files, not `.ts`
    - **Import Errors**: Missing imports, wrong paths, circular dependencies
    - **Type Errors**: TypeScript mismatches, missing type definitions
    - **Dependencies**: Missing packages in requirements.txt or package.json

    ### SUCCESS CRITERIA:
    - ✅ Backend container running without errors
    - ✅ Frontend builds and serves successfully  
    - ✅ HTTP endpoints accessible (200 responses)
    - ✅ No Python/TypeScript syntax errors
    - ✅ All dependencies properly installed

    **Current Status:**
    - Project ID: {project_id}
    - Frontend: {preview_url}
    - Backend: {backend_url} 
    - Backend: {backend_url}

    **Start with container logs, then builds, then connectivity tests. Fix issues systematically.**"""



# project summary

def _build_summary_prompt(self: GroqAgentState) -> str:
    """Build comprehensive summary prompt from conversation history"""
    
    # Extract user's original request (first user message)
    original_request = "Not found"
    plan_content = "Not found"
    
    for msg in self.conversation_history:
        if msg['role'] == 'user':
            original_request = msg['content']
            break
    
    # Extract the plan from messages
    for msg in self.conversation_history:
        if msg['role'] == 'assistant' and 'plan>' in msg.get('content', ''):
            plan_content = msg['content']
            break
    
    # Get list of created files
    created_files = list(self.project_files.keys())
    
    # Build the summary prompt
    prompt = f"""
Please create a comprehensive project summary based on the following information:

## Original User Request:
{original_request}

## AI Implementation Plan:
{plan_content}

## Project Details:
- Project ID: {self.project_id}
- Project Name: {self.project_name}
- Preview URL: {getattr(self, 'preview_url', 'Not available')}

## Files Created ({len(created_files)} total):
{chr(10).join([f'- {file}' for file in created_files[:20]])}
{f'... and {len(created_files) - 20} more files' if len(created_files) > 20 else ''}

## Full Conversation History:
{chr(10).join([f"**{msg['role'].upper()}:** {msg['content'][:200]}..." for msg in self.conversation_history[-10:]])}

---

Please create a detailed project summary with the following sections:

# Project Summary: {self.project_name}

## Overview
- Brief description of what was built
- Key features implemented

## User Requirements Analysis
- What the user originally wanted
- How the requirements were interpreted

## Implementation Plan
- High-level architecture decisions
- Technology stack chosen
- Key implementation phases

## Files and Structure
- Frontend components and their purposes
- Backend endpoints and services
- Key configuration files
- Database/data models (if any)

## Route Implementation
- Frontend routes created
- Backend endpoints implemented
- Navigation structure

## Data Flow
- How data moves through the system
- Key interactions between frontend and backend
- State management approach

## Key Features Delivered
- Main functionality implemented
- User interface components
- Backend capabilities

## Architecture Decisions
- Framework choices and why
- Design patterns used
- Integration approaches

## Future Enhancement Guidelines
- How to add new features
- Extension points in the code
- Recommended modification approaches

## Technical Notes
- Important implementation details
- Gotchas or special considerations
- Testing and deployment notes

## Project Context
- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Project ID: {self.project_id}
- Status: Live preview available
"""
    
    return prompt


