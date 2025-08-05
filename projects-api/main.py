"""
Minimal FastAPI for project management with live preview support
"""
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import os
import shutil
import uuid
import json
import subprocess
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import httpx
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global project servers manager
class ProjectServers:
    def __init__(self):
        self.servers: Dict[str, Dict] = {}
        self.port_pool = list(range(3000, 4000))
        self.used_ports = set()
    
    async def start_dev_server(self, project_id: str, project_path: str) -> int:
        """Start a Vite dev server for a project"""
        if project_id in self.servers:
            return self.servers[project_id]['port']
        
        # Get available port
        port = None
        for p in self.port_pool:
            if p not in self.used_ports:
                port = p
                self.used_ports.add(p)
                break
        
        if not port:
            raise Exception("No available ports")
        
        # Kill any existing process on this port
        subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, capture_output=True)
        
        # Start Vite dev server
        env = os.environ.copy()
        env['NODE_OPTIONS'] = '--max-old-space-size=512'  # Limit memory
        
        # Use wrapper script if available, otherwise direct vite
        wrapper_path = Path(__file__).parent / "vite_wrapper.sh"
        if wrapper_path.exists():
            process = await asyncio.create_subprocess_exec(
                'bash', str(wrapper_path), project_path, str(port),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            process = await asyncio.create_subprocess_exec(
                'npx', 'vite', '--host', '0.0.0.0', '--port', str(port),
                cwd=project_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        
        self.servers[project_id] = {
            'port': port,
            'process': process,
            'path': project_path
        }
        
        # Wait a bit for server to start
        await asyncio.sleep(3)
        
        logger.info(f"Started dev server for project {project_id} on port {port}")
        return port
    
    async def stop_dev_server(self, project_id: str):
        """Stop a project's dev server"""
        if project_id in self.servers:
            server = self.servers[project_id]
            if server['process']:
                server['process'].terminate()
                await server['process'].wait()
            self.used_ports.discard(server['port'])
            del self.servers[project_id]
            logger.info(f"Stopped dev server for project {project_id}")
    
    async def cleanup(self):
        """Stop all dev servers"""
        for project_id in list(self.servers.keys()):
            await self.stop_dev_server(project_id)

project_servers = ProjectServers()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await project_servers.cleanup()

app = FastAPI(title="Projects API", version="1.0.0", lifespan=lifespan)

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

class FileContent(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"

class ReadFileRequest(BaseModel):
    file_path: str = Field(..., description="File path relative to project root")

class UpdateFileRequest(BaseModel):
    file_path: str = Field(..., description="File path relative to project root")
    content: str
    encoding: str = "utf-8"

class ListFilesRequest(BaseModel):
    path: str = Field(default="", description="Directory path relative to project root")

class DeleteFileRequest(BaseModel):
    file_path: str = Field(..., description="File path relative to project root")

class CommandRequest(BaseModel):
    command: str = Field(..., description="Full command string to execute (e.g., 'npm run build')")
    cwd: Optional[str] = Field(None, description="Working directory")

class CommandResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int

class FileInfo(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None

class FileListResponse(BaseModel):
    files: List[FileInfo]
    path: str

# Global paths
PROJECTS_PATH = Path("/app/projects")
BOILERPLATE_PATH = Path("/app/boilerplate")

# Service functions
def get_project(project_id: str) -> Optional[ProjectInfo]:
    """Get project by ID"""
    for project_dir in PROJECTS_PATH.iterdir():
        if project_dir.is_dir():
            metadata_file = project_dir / ".project_metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    data = json.load(f)
                    if data.get("id") == project_id:
                        return ProjectInfo(**data)
    return None

def create_project(name: str, request: str, template: str = "shadcn-boilerplate") -> ProjectInfo:
    """Create a new project"""
    project_id = str(uuid.uuid4())
    project_path = PROJECTS_PATH / name
    template_path = BOILERPLATE_PATH / template
    
    if not template_path.exists():
        raise ValueError(f"Template '{template}' not found")
    
    if project_path.exists():
        raise ValueError(f"Project '{name}' already exists")
    
    # Copy template
    shutil.copytree(template_path, project_path, ignore=shutil.ignore_patterns('node_modules', '.git'))
    
    # Create project info
    project = ProjectInfo(
        id=project_id,
        name=name,
        path=str(project_path),
        status="created",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        request=request,
        template=template
    )
    
    # Save metadata
    metadata_file = project_path / ".project_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(project.model_dump(mode='json'), f, indent=2, default=str)
    
    return project

def execute_command(project_id: str, command: str, cwd: str = None) -> CommandResponse:
    """Execute command in project directory"""
    project = get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    
    project_path = Path(project.path)
    if cwd:
        work_dir = project_path / cwd
        try:
            work_dir.resolve().relative_to(project_path.resolve())
        except ValueError:
            raise ValueError("Access denied: Working directory outside project")
    else:
        work_dir = project_path
    
    if not work_dir.exists():
        raise ValueError(f"Working directory '{cwd or '.'}' not found")
    
    try:
        logger.info(f"Executing command in {work_dir}: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return CommandResponse(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None,
            exit_code=result.returncode
        )
        
    except subprocess.TimeoutExpired:
        raise ValueError("Command timed out after 5 minutes")
    except Exception as e:
        raise ValueError(f"Failed to execute command: {str(e)}")

# API Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "projects-api"}

@app.post("/api/projects", response_model=ProjectInfo)
async def create_project_endpoint(request: CreateProjectRequest):
    """Create a new project"""
    try:
        project = create_project(request.name, request.request, request.template)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    projects = []
    if PROJECTS_PATH.exists():
        for project_dir in PROJECTS_PATH.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / ".project_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        data = json.load(f)
                        projects.append(ProjectInfo(**data))
    return {"projects": projects}

@app.post("/api/projects/{project_id}/files/read", response_model=FileContent)
async def read_file(project_id: str, request: ReadFileRequest):
    """Read a file from project"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file_path = Path(project.path) / request.file_path
    try:
        file_path.resolve().relative_to(Path(project.path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return FileContent(path=request.file_path, content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@app.post("/api/projects/{project_id}/files/write")
async def write_file(project_id: str, request: UpdateFileRequest):
    """Write/update a file in project"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file_path = Path(project.path) / request.file_path
    try:
        file_path.resolve().relative_to(Path(project.path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding=request.encoding) as f:
            f.write(request.content)
        return {"message": f"File '{request.file_path}' updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

@app.post("/api/projects/{project_id}/files/list", response_model=FileListResponse)
async def list_files(project_id: str, request: ListFilesRequest):
    """List files in project directory"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    dir_path = Path(project.path) / request.path
    try:
        dir_path.resolve().relative_to(Path(project.path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    
    try:
        files = []
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith('.') and item.name not in ['.project_metadata.json']:
                continue
            
            relative_path = str(item.relative_to(Path(project.path)))
            files.append(FileInfo(
                name=item.name,
                path=relative_path,
                type="directory" if item.is_dir() else "file",
                size=item.stat().st_size if item.is_file() else None
            ))
        
        return FileListResponse(files=files, path=request.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.post("/api/projects/{project_id}/command", response_model=CommandResponse)
async def execute_command_endpoint(project_id: str, request: CommandRequest):
    """Execute a command in the project directory"""
    try:
        result = execute_command(project_id, request.command, request.cwd)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute command: {str(e)}")

@app.post("/api/projects/{project_id}/preview/start")
async def start_preview(project_id: str):
    """Start the development server for live preview"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        port = await project_servers.start_dev_server(project_id, project.path)
        return {"status": "started", "port": port, "preview_url": f"/api/projects/{project_id}/preview/"}
    except Exception as e:
        logger.error(f"Failed to start dev server: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start preview: {str(e)}")

@app.post("/api/projects/{project_id}/preview/stop")
async def stop_preview(project_id: str):
    """Stop the development server"""
    await project_servers.stop_dev_server(project_id)
    return {"status": "stopped"}

@app.get("/api/projects/{project_id}/preview/{path:path}")
async def preview_proxy(request: Request, project_id: str, path: str = ""):
    """Proxy requests to the Vite dev server"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if dev server is running
    if project_id not in project_servers.servers:
        # Try to start it
        try:
            await project_servers.start_dev_server(project_id, project.path)
        except Exception as e:
            logger.error(f"Failed to start dev server: {e}")
            raise HTTPException(status_code=500, detail="Preview server not running. Please start it first.")
    
    # Get the dev server port
    server_info = project_servers.servers.get(project_id)
    if not server_info:
        raise HTTPException(status_code=500, detail="Dev server not available")
    
    port = server_info['port']
    target_url = f"http://localhost:{port}/{path}"
    
    # Add query params
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
                content=await request.body() if request.method in ['POST', 'PUT', 'PATCH'] else None,
                follow_redirects=True
            )
            
            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']},
                media_type=response.headers.get('content-type', 'text/html')
            )
    except httpx.ConnectError:
        logger.error(f"Could not connect to dev server on port {port}")
        raise HTTPException(status_code=503, detail="Dev server is starting up, please try again in a few seconds")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)