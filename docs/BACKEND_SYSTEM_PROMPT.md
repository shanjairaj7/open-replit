# BACKEND SYSTEM PROMPT INSTRUCTIONS

## Backend Code Structure Guidelines

When working with backend code in the monorepo projects, follow these strict guidelines:

### **1. Core File Structure (DO NOT MODIFY app.py)**

The backend structure is:
```
backend/
├── app.py              # NEVER MODIFY - Main FastAPI application
├── requirements.txt    # You can ADD packages here
├── services/           # CREATE service files here
│   ├── __init__.py
│   └── *.py           # Your service modules
└── models/            # CREATE Pydantic models here
    ├── __init__.py
    └── *.py           # Your model modules
```

### **2. app.py Structure (READ-ONLY)**

The `app.py` file contains:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import api_router

app = FastAPI()

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "Backend API running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### **3. Service Files Creation**

When creating backend functionality, ALWAYS create service files in the `services/` directory:

**Example: services/user_service.py**
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Create a router for this service
router = APIRouter()

# Define your endpoints
@router.post("/users")
async def create_user(user: UserCreate):
    # Implementation
    return {"id": "123", "name": user.name}

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    # Implementation
    return {"id": user_id, "name": "John Doe"}

@router.put("/users/{user_id}")
async def update_user(user_id: str, user: UserUpdate):
    # Implementation
    return {"id": user_id, **user.dict()}
```

**services/__init__.py** (Auto-import all routers):
```python
from fastapi import APIRouter

api_router = APIRouter()

# Auto-import all service routers
try:
    from .user_service import router as user_router
    api_router.include_router(user_router, tags=["users"])
except ImportError:
    pass

try:
    from .product_service import router as product_router
    api_router.include_router(product_router, tags=["products"])
except ImportError:
    pass

# Add more service imports as needed
```

### **4. Model Files Creation**

Create Pydantic models in the `models/` directory:

**Example: models/user_models.py**
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, regex="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class UserResponse(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### **5. Requirements.txt Management**

When adding packages to `requirements.txt`, follow these rules:

1. **Use STABLE versions, not latest**:
   ```
   # GOOD - Stable versions
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   pydantic==2.5.0
   sqlalchemy==2.0.23
   httpx==0.25.2
   python-jose[cryptography]==3.3.0
   passlib[bcrypt]==1.7.4
   python-multipart==0.0.6
   
   # BAD - Latest versions
   fastapi
   uvicorn[standard]
   pydantic
   ```

2. **Only add packages when necessary**
3. **Include sub-dependencies explicitly** (e.g., `uvicorn[standard]` not just `uvicorn`)
4. **Comment why unusual packages are needed**

### **6. API Design Patterns**

All APIs should follow RESTful conventions:

```python
# Pattern for CRUD operations
POST   /api/resources     # Create
GET    /api/resources     # List all
GET    /api/resources/{id} # Get one
PUT    /api/resources/{id} # Update
DELETE /api/resources/{id} # Delete

# Pattern for actions
POST   /api/resources/{id}/action
```

### **7. Error Handling**

Always use proper HTTP status codes and error messages:

```python
from fastapi import HTTPException

# Not found
raise HTTPException(status_code=404, detail="Resource not found")

# Bad request
raise HTTPException(status_code=400, detail="Invalid input data")

# Unauthorized
raise HTTPException(status_code=401, detail="Not authenticated")

# Forbidden
raise HTTPException(status_code=403, detail="Not authorized")
```

### **8. Database Operations (if needed)**

If database is required, use SQLAlchemy with async support:

```python
# models/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### **9. Important Rules**

1. **NEVER modify app.py** - It's the entry point and should remain stable
2. **ALWAYS create services in services/ directory**
3. **ALWAYS create models in models/ directory**
4. **USE the /api prefix** - All your endpoints will be under /api/
5. **IMPORT models properly** - Use relative imports within the backend
6. **TEST your endpoints** - Consider the frontend will call these APIs
7. **HANDLE errors gracefully** - Always return proper error responses
8. **DOCUMENT your endpoints** - Use FastAPI's built-in documentation features

### **10. Example Backend Task**

**User Request**: "Create a task management API"

**Model Response**: Creates these files:

`services/task_service.py`:
```python
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from models.task_models import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

# In-memory storage for demo
tasks_db = {}

@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    task_id = str(len(tasks_db) + 1)
    task_data = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "completed": False,
        "created_at": datetime.now()
    }
    tasks_db[task_id] = task_data
    return task_data

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    return list(tasks_db.values())

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]
```

`models/task_models.py`:
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
```

Updates `requirements.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
```

This ensures clean, maintainable, and scalable backend code!