# VPS Monorepo Testing Commands

## Setup Commands

### Initial VPS Setup

```bash
# Clone the dedicated projects-api repository
cd /opt
rm -rf codebase-platform
git clone git@github.com:shanjairaj7/projects-api.git codebase-platform
cd codebase-platform

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r vps-requirements.txt

# Fix Docker permissions
sudo chmod 666 /var/run/docker.sock

# Start the service
python vps-app.py &
```

## API Testing Commands

### 1. Check API Status

```bash
curl -s http://localhost:8000/ | python -m json.tool
# Should show both frontend_boilerplate_exists: true and backend_boilerplate_exists: true
```

### 2. Create Monorepo Project (Real Use Case)

```bash
# Create a task management app with frontend and backend components
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "task-manager-app",
    "files": {
      "frontend/src/components/TaskList.tsx": "import React, { useState, useEffect } from \"react\";\nimport { Button } from \"./ui/button\";\nimport { Card, CardContent, CardHeader, CardTitle } from \"./ui/card\";\n\ninterface Task {\n  id: number;\n  title: string;\n  completed: boolean;\n}\n\nexport const TaskList = () => {\n  const [tasks, setTasks] = useState<Task[]>([]);\n  const [loading, setLoading] = useState(true);\n\n  useEffect(() => {\n    fetchTasks();\n  }, []);\n\n  const fetchTasks = async () => {\n    try {\n      const response = await fetch(\"/api/tasks\");\n      const data = await response.json();\n      setTasks(data.tasks);\n    } catch (error) {\n      console.error(\"Failed to fetch tasks:\", error);\n    } finally {\n      setLoading(false);\n    }\n  };\n\n  const toggleTask = async (id: number) => {\n    try {\n      await fetch(`/api/tasks/${id}/toggle`, { method: \"POST\" });\n      fetchTasks();\n    } catch (error) {\n      console.error(\"Failed to toggle task:\", error);\n    }\n  };\n\n  if (loading) return <div>Loading tasks...</div>;\n\n  return (\n    <Card className=\"w-full max-w-2xl mx-auto\">\n      <CardHeader>\n        <CardTitle>Task Manager</CardTitle>\n      </CardHeader>\n      <CardContent>\n        <div className=\"space-y-2\">\n          {tasks.map((task) => (\n            <div key={task.id} className=\"flex items-center justify-between p-2 border rounded\">\n              <span className={task.completed ? \"line-through text-gray-500\" : \"\"}>\n                {task.title}\n              </span>\n              <Button \n                onClick={() => toggleTask(task.id)}\n                variant={task.completed ? \"outline\" : \"default\"}\n                size=\"sm\"\n              >\n                {task.completed ? \"Undo\" : \"Complete\"}\n              </Button>\n            </div>\n          ))}\n        </div>\n      </CardContent>\n    </Card>\n  );\n};",
      "backend/services/task_service.py": "from fastapi import APIRouter, HTTPException\nfrom pydantic import BaseModel\nfrom typing import List, Optional\nfrom datetime import datetime\n\nrouter = APIRouter()\n\n# In-memory storage (replace with database in real app)\ntasks_db = [\n    {\"id\": 1, \"title\": \"Setup project structure\", \"completed\": True, \"created_at\": \"2025-01-01T10:00:00\"},\n    {\"id\": 2, \"title\": \"Create task API endpoints\", \"completed\": False, \"created_at\": \"2025-01-01T11:00:00\"},\n    {\"id\": 3, \"title\": \"Build React frontend\", \"completed\": False, \"created_at\": \"2025-01-01T12:00:00\"},\n]\n\nclass Task(BaseModel):\n    id: int\n    title: str\n    completed: bool\n    created_at: str\n\nclass CreateTaskRequest(BaseModel):\n    title: str\n\nclass TaskListResponse(BaseModel):\n    tasks: List[Task]\n    total: int\n\n@router.get(\"/tasks\", response_model=TaskListResponse)\nasync def get_tasks():\n    \"\"\"Get all tasks\"\"\"\n    return TaskListResponse(\n        tasks=tasks_db,\n        total=len(tasks_db)\n    )\n\n@router.post(\"/tasks\", response_model=Task)\nasync def create_task(request: CreateTaskRequest):\n    \"\"\"Create a new task\"\"\"\n    new_id = max([task[\"id\"] for task in tasks_db], default=0) + 1\n    new_task = {\n        \"id\": new_id,\n        \"title\": request.title,\n        \"completed\": False,\n        \"created_at\": datetime.now().isoformat()\n    }\n    tasks_db.append(new_task)\n    return Task(**new_task)\n\n@router.post(\"/tasks/{task_id}/toggle\")\nasync def toggle_task(task_id: int):\n    \"\"\"Toggle task completion status\"\"\"\n    for task in tasks_db:\n        if task[\"id\"] == task_id:\n            task[\"completed\"] = not task[\"completed\"]\n            return {\"message\": \"Task toggled successfully\", \"task\": task}\n    raise HTTPException(status_code=404, detail=\"Task not found\")\n\n@router.delete(\"/tasks/{task_id}\")\nasync def delete_task(task_id: int):\n    \"\"\"Delete a task\"\"\"\n    global tasks_db\n    tasks_db = [task for task in tasks_db if task[\"id\"] != task_id]\n    return {\"message\": \"Task deleted successfully\"}"
    }
  }' | python -m json.tool
```

### 3. List Project Files (Verify Structure)

```bash
curl -s http://localhost:8000/api/projects/task-manager-app/files | python -m json.tool
# Should show both frontend/ and backend/ folders with boilerplate files + custom files
```

### 4. Read Real Frontend Component

```bash
curl -s http://localhost:8000/api/projects/task-manager-app/files/frontend/src/components/TaskList.tsx
# Should show the React component with shadcn/ui components and API calls
```

### 5. Read Real Backend Service

```bash
curl -s http://localhost:8000/api/projects/task-manager-app/files/backend/services/task_service.py
# Should show FastAPI router with CRUD operations for tasks
```

### 6. Update Backend to Include New Service

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/backend/services/__init__.py \
  -H "Content-Type: application/json" \
  -d '{"content": "from fastapi import APIRouter\n\napi_router = APIRouter()\n\n# Import health service\ntry:\n    from .health_service import router as health_router\n    api_router.include_router(health_router, tags=[\"health\"])\nexcept ImportError:\n    pass\n\n# Import task service\ntry:\n    from .task_service import router as task_router\n    api_router.include_router(task_router, prefix=\"/api\", tags=[\"tasks\"])\nexcept ImportError:\n    pass"}'
```

### 7. Update Frontend App to Use TaskList

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/frontend/src/App.tsx \
  -H "Content-Type: application/json" \
  -d '{"content": "import React from \"react\";\nimport { TaskList } from \"./components/TaskList\";\nimport \"./App.css\";\n\nfunction App() {\n  return (\n    <div className=\"min-h-screen bg-gray-50 py-8\">\n      <div className=\"container mx-auto px-4\">\n        <h1 className=\"text-3xl font-bold text-center mb-8 text-gray-900\">\n          Task Management App\n        </h1>\n        <TaskList />\n      </div>\n    </div>\n  );\n}\n\nexport default App;"}'
```

## Preview Testing Commands

### Test Current Task Manager App Preview

```bash
# Create the task manager app first
curl -X POST http://206.189.229.208:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"project_id": "task-manager-test", "files": {"frontend/src/App.tsx": "import React from \"react\";\nimport \"./App.css\";\n\nfunction App() {\n  return (\n    <div className=\"min-h-screen bg-gray-50 py-8\">\n      <div className=\"container mx-auto px-4\">\n        <h1 className=\"text-3xl font-bold text-center mb-8 text-gray-900\">\n          Task Management App\n        </h1>\n        <p className=\"text-center text-gray-600\">Welcome to your task manager!</p>\n      </div>\n    </div>\n  );\n}\n\nexport default App;"}}'

# Start frontend preview
curl -X POST http://206.189.229.208:8000/api/projects/task-manager-app/start-preview | python -m json.tool

# Wait for container startup (npm install + dev server)
sleep 45

# Check container is running
docker ps | grep task-manager-test

# Check container logs
docker logs project-task-manager-test

# Test preview URL (should show the React app)
curl -s http://206.189.229.208:3001/ | head -20

# Open in browser: http://206.189.229.208:3001

# Stop preview when done
curl -X POST http://206.189.229.208:8000/api/projects/task-manager-test/stop-preview
```

### Backend Preview Test (Phase 4 - Not Yet Implemented)

```bash
# These commands will work after Phase 4 implementation:

# Start backend preview (FastAPI dev server)
# curl -X POST http://localhost:8000/api/projects/task-manager-app/start-backend-preview | python -m json.tool

# Test backend API endpoints
# curl -s http://localhost:8001/api/health | python -m json.tool
# curl -s http://localhost:8001/api/tasks | python -m json.tool

# Test task creation
# curl -X POST http://localhost:8001/api/tasks \
#   -H "Content-Type: application/json" \
#   -d '{"title": "Test new task"}' | python -m json.tool

# Stop backend preview
# curl -X POST http://localhost:8000/api/projects/task-manager-app/stop-backend-preview
```

## File CRUD Testing Commands (Phase 3)

### Add User Authentication Component

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/frontend/src/components/LoginForm.tsx \
  -H "Content-Type: application/json" \
  -d '{"content": "import React, { useState } from \"react\";\nimport { Button } from \"./ui/button\";\nimport { Input } from \"./ui/input\";\nimport { Card, CardContent, CardHeader, CardTitle } from \"./ui/card\";\nimport { Label } from \"./ui/label\";\n\nexport const LoginForm = () => {\n  const [email, setEmail] = useState(\"\");\n  const [password, setPassword] = useState(\"\");\n  const [loading, setLoading] = useState(false);\n\n  const handleLogin = async (e: React.FormEvent) => {\n    e.preventDefault();\n    setLoading(true);\n    \n    try {\n      const response = await fetch(\"/api/auth/login\", {\n        method: \"POST\",\n        headers: { \"Content-Type\": \"application/json\" },\n        body: JSON.stringify({ email, password })\n      });\n      \n      if (response.ok) {\n        const data = await response.json();\n        localStorage.setItem(\"token\", data.token);\n        window.location.reload();\n      } else {\n        alert(\"Login failed\");\n      }\n    } catch (error) {\n      console.error(\"Login error:\", error);\n    } finally {\n      setLoading(false);\n    }\n  };\n\n  return (\n    <Card className=\"w-full max-w-md mx-auto\">\n      <CardHeader>\n        <CardTitle>Login</CardTitle>\n      </CardHeader>\n      <CardContent>\n        <form onSubmit={handleLogin} className=\"space-y-4\">\n          <div>\n            <Label htmlFor=\"email\">Email</Label>\n            <Input\n              id=\"email\"\n              type=\"email\"\n              value={email}\n              onChange={(e) => setEmail(e.target.value)}\n              required\n            />\n          </div>\n          <div>\n            <Label htmlFor=\"password\">Password</Label>\n            <Input\n              id=\"password\"\n              type=\"password\"\n              value={password}\n              onChange={(e) => setPassword(e.target.value)}\n              required\n            />\n          </div>\n          <Button type=\"submit\" className=\"w-full\" disabled={loading}>\n            {loading ? \"Logging in...\" : \"Login\"}\n          </Button>\n        </form>\n      </CardContent>\n    </Card>\n  );\n};"}'
```

### Add Authentication Backend Service

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/backend/services/auth_service.py \
  -H "Content-Type: application/json" \
  -d '{"content": "from fastapi import APIRouter, HTTPException, Depends\nfrom fastapi.security import HTTPBearer, HTTPAuthorizationCredentials\nfrom pydantic import BaseModel\nfrom typing import Optional\nimport jwt\nfrom datetime import datetime, timedelta\n\nrouter = APIRouter()\nsecurity = HTTPBearer()\n\n# Secret key for JWT (use environment variable in production)\nSECRET_KEY = \"your-secret-key-here\"\nALGORITHM = \"HS256\"\n\n# Mock user database\nusers_db = {\n    \"admin@example.com\": {\n        \"id\": 1,\n        \"email\": \"admin@example.com\",\n        \"password\": \"admin123\",  # In production, use hashed passwords\n        \"name\": \"Admin User\"\n    }\n}\n\nclass LoginRequest(BaseModel):\n    email: str\n    password: str\n\nclass LoginResponse(BaseModel):\n    token: str\n    user: dict\n\nclass User(BaseModel):\n    id: int\n    email: str\n    name: str\n\ndef create_access_token(data: dict):\n    to_encode = data.copy()\n    expire = datetime.utcnow() + timedelta(hours=24)\n    to_encode.update({\"exp\": expire})\n    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)\n\ndef verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):\n    try:\n        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])\n        email: str = payload.get(\"sub\")\n        if email is None or email not in users_db:\n            raise HTTPException(status_code=401, detail=\"Invalid token\")\n        return users_db[email]\n    except jwt.PyJWTError:\n        raise HTTPException(status_code=401, detail=\"Invalid token\")\n\n@router.post(\"/auth/login\", response_model=LoginResponse)\nasync def login(request: LoginRequest):\n    \"\"\"Authenticate user and return JWT token\"\"\"\n    user = users_db.get(request.email)\n    if not user or user[\"password\"] != request.password:\n        raise HTTPException(status_code=401, detail=\"Invalid credentials\")\n    \n    token = create_access_token(data={\"sub\": user[\"email\"]})\n    return LoginResponse(\n        token=token,\n        user={\"id\": user[\"id\"], \"email\": user[\"email\"], \"name\": user[\"name\"]}\n    )\n\n@router.get(\"/auth/me\", response_model=User)\nasync def get_current_user(current_user: dict = Depends(verify_token)):\n    \"\"\"Get current authenticated user\"\"\"\n    return User(\n        id=current_user[\"id\"],\n        email=current_user[\"email\"],\n        name=current_user[\"name\"]\n    )"}'
```

### Add Database Models

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/backend/models/database.py \
  -H "Content-Type: application/json" \
  -d '{"content": "from pydantic import BaseModel\nfrom typing import List, Optional\nfrom datetime import datetime\n\n# Database models for the task manager app\n\nclass UserModel(BaseModel):\n    id: int\n    email: str\n    name: str\n    created_at: datetime\n    is_active: bool = True\n\nclass TaskModel(BaseModel):\n    id: int\n    title: str\n    description: Optional[str] = None\n    completed: bool = False\n    priority: str = \"medium\"  # low, medium, high\n    user_id: int\n    created_at: datetime\n    updated_at: Optional[datetime] = None\n    due_date: Optional[datetime] = None\n\nclass ProjectModel(BaseModel):\n    id: int\n    name: str\n    description: Optional[str] = None\n    owner_id: int\n    created_at: datetime\n    is_active: bool = True\n\nclass TaskCreateRequest(BaseModel):\n    title: str\n    description: Optional[str] = None\n    priority: str = \"medium\"\n    due_date: Optional[datetime] = None\n\nclass TaskUpdateRequest(BaseModel):\n    title: Optional[str] = None\n    description: Optional[str] = None\n    completed: Optional[bool] = None\n    priority: Optional[str] = None\n    due_date: Optional[datetime] = None\n\n# Mock database collections\ntasks_collection = []\nusers_collection = []\nprojects_collection = []"}'
```

### Update Main App with New Routes

```bash
curl -X PUT http://localhost:8000/api/projects/task-manager-app/files/backend/app.py \
  -H "Content-Type: application/json" \
  -d '{"content": "from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom services import api_router\n# Import new services\nfrom services.auth_service import router as auth_router\n\napp = FastAPI(\n    title=\"Task Manager API\",\n    version=\"1.0.0\",\n    description=\"A comprehensive task management application with authentication\"\n)\n\n# CORS middleware\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=[\"*\"],  # In production, specify your frontend domain\n    allow_credentials=True,\n    allow_methods=[\"*\"],\n    allow_headers=[\"*\"],\n)\n\n# Include all API routes\napp.include_router(api_router, prefix=\"/api\")\napp.include_router(auth_router, prefix=\"/api\")\n\n@app.get(\"/\")\nasync def root():\n    return {\n        \"message\": \"Task Manager API\",\n        \"version\": \"1.0.0\",\n        \"docs\": \"/docs\",\n        \"health\": \"/api/health\"\n    }\n\nif __name__ == \"__main__\":\n    import uvicorn\n    uvicorn.run(app, host=\"0.0.0.0\", port=8000)"}'
```

## Project Management Commands

### List All Projects

```bash
curl -s http://localhost:8000/api/projects | python -m json.tool
```

### Get Project Status

```bash
curl -s http://localhost:8000/api/projects/test-monorepo | python -m json.tool
```

### Delete Project (Archives Instead of Deleting)

```bash
curl -X DELETE http://localhost:8000/api/projects/test-monorepo | python -m json.tool
```

## Troubleshooting Commands

### Check Docker Containers

```bash
docker ps
docker logs <container_id>
```

### Check VPS Logs

```bash
# If running in background, check process
ps aux | grep vps-app.py

# Kill if needed
pkill -f "python vps-app.py"
```

### Check Storage

```bash
ls -la /opt/codebase-platform/projects/
ls -la /opt/codebase-platform/projects/test-monorepo/
```

## Current Implementation Status

- ✅ **Phase 1**: Backend boilerplate created
- ✅ **Phase 2**: Monorepo project creation (frontend/ + backend/ folders)
- ⏳ **Phase 3**: File CRUD operations for monorepo paths (next)
- ⏳ **Phase 4**: Dual container management (frontend + backend)
- ⏳ **Phase 5**: Backend FastAPI server startup logic
- ⏳ **Phase 6**: Preview URLs and port management

## Notes

- Frontend preview currently works (React/Vite on ports 3001-3999)
- Backend preview will be implemented in Phase 4
- All file operations work with monorepo paths (frontend/, backend/)
- Projects are archived instead of deleted for safety
