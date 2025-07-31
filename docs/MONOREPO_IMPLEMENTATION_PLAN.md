# MONOREPO IMPLEMENTATION PLAN

## ITERATIVE DEVELOPMENT PHASES

### **Phase 1: Backend Boilerplate Creation**
**Goal**: Create FastAPI backend template structure
**Duration**: 1-2 iterations

**Tasks**:
1. Create `/opt/codebase-platform/boilerplate/backend-boilerplate/` directory
2. Generate basic FastAPI files:
   - `app.py` (main FastAPI app with basic routes)
   - `requirements.txt` (FastAPI, uvicorn, etc.)
   - `services/` directory with example service
   - `models/` directory with Pydantic models
   - `routes/` directory for API endpoints

**Deliverable**: Backend boilerplate template ready

---

### **Phase 2: Project Structure Modification**
**Goal**: Change project creation to use monorepo structure
**Duration**: 2-3 iterations

**Tasks**:
1. Modify `VPSProjectManager.create_project()` method
2. Create `frontend/` and `backend/` subdirectories
3. Copy existing boilerplate to `frontend/`
4. Copy new backend boilerplate to `backend/`
5. Update metadata structure for dual containers

**Deliverable**: New projects created with monorepo structure

---

### **Phase 3: File Operations Update**
**Goal**: Handle file paths for both frontend and backend
**Duration**: 2-3 iterations

**Tasks**:
1. Update `update_file()` to handle `frontend/src/App.tsx` paths
2. Update `read_file()` for monorepo paths
3. Update `list_files()` to show both frontend and backend
4. Modify file validation and path handling

**Deliverable**: File CRUD operations work with monorepo structure

---

### **Phase 4: Dual Container Management**
**Goal**: Run both frontend and backend containers per project
**Duration**: 3-4 iterations

**Tasks**:
1. Modify `start_dev_server()` to start two containers
2. Implement backend container startup (Python + FastAPI)
3. Update port allocation (frontend: 3xxx, backend: 4xxx)
4. Handle container lifecycle for both services
5. Update container status tracking

**Deliverable**: Both frontend and backend running in containers

---

### **Phase 5: Backend API Integration**
**Goal**: Backend FastAPI accessible to frontend
**Duration**: 2-3 iterations

**Tasks**:
1. Configure backend FastAPI with CORS for frontend
2. Set up frontend proxy configuration for backend calls
3. Test API communication between containers
4. Update preview URLs to include backend info

**Deliverable**: Full-stack communication working

---

### **Phase 6: Testing & Validation**
**Goal**: Ensure everything works end-to-end
**Duration**: 2-3 iterations

**Tasks**:
1. Test project creation with monorepo structure
2. Test file updates in both frontend and backend
3. Test preview functionality for both services
4. Test HMR for frontend changes
5. Test backend API restart on file changes

**Deliverable**: Complete monorepo system working

---

## CODEBASE CHANGES ANALYSIS

### **Files That Will Change:**

#### **1. `/opt/codebase-platform/vps-app.py`** (MAJOR CHANGES)

**Current Functions → Changes Needed:**

```python
# CURRENT
async def create_project(self, project_id: str, files: Dict[str, str]):
    project_path = VPS_PROJECTS_PATH / project_id
    shutil.copytree(VPS_BOILERPLATE_PATH, project_path)  # Single copy
    
# NEW
async def create_project(self, project_id: str, files: Dict[str, str]):
    project_path = VPS_PROJECTS_PATH / project_id
    frontend_path = project_path / "frontend"
    backend_path = project_path / "backend"
    
    # Copy both boilerplates
    shutil.copytree(FRONTEND_BOILERPLATE_PATH, frontend_path)
    shutil.copytree(BACKEND_BOILERPLATE_PATH, backend_path)
```

```python
# CURRENT
async def start_dev_server(self, project_id: str):
    # Start single Node.js container
    container = docker_client.containers.run("node:20-alpine", ...)
    
# NEW  
async def start_dev_server(self, project_id: str):
    # Start TWO containers
    frontend_container = docker_client.containers.run("node:20-alpine", ...)
    backend_container = docker_client.containers.run("python:3.11-slim", ...)
    
    # Track both containers
    self.containers[project_id] = {
        'frontend': {'container': frontend_container, 'port': 3001},
        'backend': {'container': backend_container, 'port': 4001}
    }
```

```python
# CURRENT
async def update_file(self, project_id: str, file_path: str, content: str):
    full_path = project_path / file_path  # Direct path
    
# NEW
async def update_file(self, project_id: str, file_path: str, content: str):
    # Handle monorepo paths
    if file_path.startswith('frontend/'):
        full_path = project_path / file_path
        # Trigger frontend HMR
    elif file_path.startswith('backend/'):
        full_path = project_path / file_path  
        # Trigger backend restart
```

#### **2. Port Management Changes**

```python
# CURRENT
self.port_pool = list(range(3001, 3999))  # Single port per project

# NEW
self.frontend_port_pool = list(range(3001, 3500))  # Frontend ports
self.backend_port_pool = list(range(4001, 4500))   # Backend ports
```

#### **3. Container Tracking Changes**

```python
# CURRENT
self.containers: Dict[str, Dict] = {
    'project-123': {
        'container': <container_obj>,
        'port': 3001,
        'status': 'running'
    }
}

# NEW
self.containers: Dict[str, Dict] = {
    'project-123': {
        'frontend': {
            'container': <frontend_container>,
            'port': 3001,
            'status': 'running'
        },
        'backend': {
            'container': <backend_container>, 
            'port': 4001,
            'status': 'running'
        }
    }
}
```

### **New Files Required:**

#### **1. Backend Boilerplate Structure**
```
/opt/codebase-platform/boilerplate/backend-boilerplate/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── routes/
│   ├── __init__.py
│   └── api.py            # API endpoints
├── services/
│   ├── __init__.py
│   └── example_service.py # Business logic
├── models/
│   ├── __init__.py
│   └── schemas.py        # Pydantic models
└── config.py             # Configuration
```

#### **2. Updated API Endpoints**

```python
# NEW ENDPOINTS NEEDED
@app.get("/api/projects/{project_id}/preview/frontend")  # Frontend preview
@app.get("/api/projects/{project_id}/preview/backend")   # Backend preview
@app.post("/api/projects/{project_id}/start-frontend")   # Start frontend only
@app.post("/api/projects/{project_id}/start-backend")    # Start backend only
@app.get("/api/projects/{project_id}/logs/frontend")     # Frontend logs
@app.get("/api/projects/{project_id}/logs/backend")      # Backend logs
```

### **Configuration Changes:**

#### **1. Directory Structure**
```
/opt/codebase-platform/
├── boilerplate/
│   ├── shadcn-boilerplate/     # Existing frontend
│   └── backend-boilerplate/    # NEW: Backend template
├── projects/
│   └── project-123/
│       ├── frontend/           # NEW: Frontend code
│       ├── backend/            # NEW: Backend code
│       └── .project_metadata.json
```

#### **2. Metadata Structure**
```json
{
  "id": "project-123",
  "path": "/opt/codebase-platform/projects/project-123",
  "created_at": "2025-07-31T...",
  "status": "created",
  "structure": "monorepo",
  "containers": {
    "frontend": {"port": 3001, "status": "running"},
    "backend": {"port": 4001, "status": "running"}
  }
}
```

## BACKWARD COMPATIBILITY

**Strategy**: Support both structures
- Check if project has `frontend/` folder → monorepo
- No `frontend/` folder → legacy single frontend
- API remains the same, internal logic adapts

## RISK MITIGATION

1. **Test with new projects first** - don't break existing ones
2. **Incremental rollout** - phase by phase
3. **Rollback plan** - keep current `vps-app.py` as backup
4. **Validation** - extensive testing at each phase

Ready to start Phase 1: Backend Boilerplate Creation?