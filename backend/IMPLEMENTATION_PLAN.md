# VPS DEPLOYMENT IMPLEMENTATION PLAN

## CLEAR REQUIREMENTS
1. **projects-api** (existing FastAPI code) deployed on VPS
2. **boilerplate** (shadcn-boilerplate) included for project cloning
3. **Persistent storage** for all created projects
4. **Direct IP access** to individual project previews
5. **Docker isolation** for each project

## DEPLOYMENT STRUCTURE
```
DigitalOcean VPS (IP: XXX.XXX.XXX.XXX)
├── API Service: http://XXX.XXX.XXX.XXX:8000
├── Project 1: http://XXX.XXX.XXX.XXX:3001
├── Project 2: http://XXX.XXX.XXX.XXX:3002
└── Project N: http://XXX.XXX.XXX.XXX:300N
```

## STEP-BY-STEP IMPLEMENTATION

### Step 1: Package Existing Code for VPS
- [x] Copy projects-api/ directory
- [x] Copy boilerplate/shadcn-boilerplate/
- [ ] Modify app.py for persistent storage paths
- [ ] Add Docker container management
- [ ] Create VPS-specific docker-compose.yml

### Step 2: Modify Core Functions
```python
# Current project creation flow:
def create_project(project_id, files):
    # 1. Create files in /tmp/projects/
    # 2. Run npm commands
    # 3. Start proxy server

# New VPS project creation flow:  
def create_project(project_id, files):
    # 1. Copy boilerplate to /opt/projects/{project_id}/
    # 2. Modify files based on input
    # 3. Start Docker container with npm run dev
    # 4. Return direct port access URL
```

### Step 3: Docker Container Management
- Each project runs in isolated Node.js container
- Persistent volume mounting for file changes
- Port allocation from pool (3001-3999)
- Container lifecycle management

### Step 4: Direct Port Access
- No reverse proxy needed initially
- Direct access: http://IP:PORT
- Nginx for static file serving (optional)

### Step 5: Persistence Strategy
```
/opt/codebase-platform/projects/
├── project-abc123/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   └── ...
│   └── .docker-info  # Container metadata
```

## MIGRATION FROM RAILWAY CODE

### Key Changes Needed:
1. **Storage paths**: `/tmp/projects/` → `/opt/codebase-platform/projects/`
2. **Preview URLs**: Proxy → Direct port access
3. **Process management**: PM2/subprocess → Docker containers
4. **Boilerplate access**: Include in deployment package

### Files to Modify:
- `app.py`: Main API logic
- `project_service.py`: Project operations  
- `docker-compose.yml`: New orchestration
- `requirements.txt`: Add docker client

### Files to Copy As-Is:
- `models/`: All model definitions
- `boilerplate/`: Complete shadcn template
- `runtime.txt`, `requirements.txt`: Dependencies

## TESTING STRATEGY
1. Deploy on VPS with single test project
2. Verify persistent storage survives restarts
3. Test file CRUD operations
4. Confirm direct port access works
5. Scale test with multiple projects

## SUCCESS CRITERIA
- ✅ API accessible at http://IP:8000
- ✅ Projects persist across server restarts  
- ✅ Direct preview access: http://IP:3001, http://IP:3002
- ✅ Real-time file updates trigger HMR
- ✅ Boilerplate properly cloned for new projects