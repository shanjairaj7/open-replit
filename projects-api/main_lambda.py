"""
Simplified FastAPI for AWS Lambda - Projects API
Note: File operations removed for Lambda compatibility
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Projects API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class CreateProjectRequest(BaseModel):
    name: str = Field(..., description="Project name")
    request: str = Field(..., description="Project description/request")
    template: str = Field(default="shadcn-boilerplate", description="Template to use")

class ProjectInfo(BaseModel):
    id: str
    name: str
    path: str
    status: str
    created_at: datetime
    updated_at: datetime
    request: str
    template: str
    port: Optional[int] = None
    build_output: Optional[str] = None
    error: Optional[str] = None

class CommandRequest(BaseModel):
    command: str = Field(..., description="Full command string to execute (e.g., 'npm run build')")
    cwd: Optional[str] = Field(None, description="Working directory")

class CommandResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int

# In-memory storage for demo (in production, use DynamoDB)
projects_store = {}

# API Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "projects-api-lambda"}

@app.post("/api/projects", response_model=ProjectInfo)
async def create_project_endpoint(request: CreateProjectRequest):
    """Create a new project (simulated for Lambda)"""
    try:
        project_id = str(uuid.uuid4())
        
        # Simulate project creation
        project = ProjectInfo(
            id=project_id,
            name=request.name,
            path=f"/tmp/projects/{request.name}",  # Lambda temp directory
            status="created",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request=request.request,
            template=request.template
        )
        
        # Store in memory (use DynamoDB in production)
        projects_store[project_id] = project.model_dump(mode='json')
        
        return project
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    projects = [ProjectInfo(**data) for data in projects_store.values()]
    return {"projects": projects}

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project by ID"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectInfo(**projects_store[project_id])

@app.post("/api/projects/{project_id}/command", response_model=CommandResponse)
async def execute_command_endpoint(project_id: str, request: CommandRequest):
    """Execute a command (simulated for Lambda)"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Simulate command execution
    logger.info(f"Simulating command: {request.command}")
    
    # For demo, return success for common commands
    if request.command in ["npm install", "npm run build", "ls -la"]:
        return CommandResponse(
            success=True,
            output=f"Simulated output for: {request.command}",
            error=None,
            exit_code=0
        )
    else:
        return CommandResponse(
            success=False,
            output="",
            error=f"Command not supported in Lambda demo: {request.command}",
            exit_code=1
        )

# Root path for API Gateway
@app.get("/")
async def root():
    return {"message": "Projects API Lambda", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)