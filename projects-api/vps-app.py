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
import sys
from contextlib import asynccontextmanager
import docker
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker client
docker_client = docker.from_env()

# VPS Configuration - PERSISTENT STORAGE
VPS_BASE_PATH = Path("/opt/codebase-platform")
VPS_PROJECTS_PATH = VPS_BASE_PATH / "projects"
VPS_BOILERPLATE_PATH = VPS_BASE_PATH / "boilerplate" / "shadcn-boilerplate"

# Ensure directories exist
VPS_BASE_PATH.mkdir(parents=True, exist_ok=True)
VPS_PROJECTS_PATH.mkdir(parents=True, exist_ok=True)

class VPSProjectManager:
    """Manages Docker containers for isolated project environments"""
    
    def __init__(self):
        self.containers: Dict[str, Dict] = {}
        self.port_pool = list(range(3001, 3999))  # Reserve 3000 for API
        self.used_ports = set()
    
    def _get_available_port(self) -> int:
        """Get next available port"""
        for port in self.port_pool:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        raise Exception("No available ports")
    
    def _release_port(self, port: int):
        """Release port back to pool"""
        self.used_ports.discard(port)
    
    async def create_project(self, project_id: str, files: Dict[str, str]) -> Dict:
        """Create new project from boilerplate with modifications"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        # Remove existing project if exists
        if project_path.exists():
            shutil.rmtree(project_path)
        
        # Copy boilerplate
        if not VPS_BOILERPLATE_PATH.exists():
            raise HTTPException(500, f"Boilerplate not found at {VPS_BOILERPLATE_PATH}")
        
        shutil.copytree(VPS_BOILERPLATE_PATH, project_path)
        logger.info(f"Copied boilerplate to {project_path}")
        
        # Apply file modifications
        for file_path, content in files.items():
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Modified file: {file_path}")
        
        # Create project metadata
        metadata = {
            "id": project_id,
            "path": str(project_path),
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }
        
        with open(project_path / ".project_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    async def start_dev_server(self, project_id: str) -> Dict:
        """Start Docker container with Vite dev server"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Stop existing container if running
        if project_id in self.containers:
            await self.stop_dev_server(project_id)
        
        # Get available port
        port = self._get_available_port()
        
        try:
            # Start Docker container
            container = docker_client.containers.run(
                "node:18-alpine",
                command="sh -c 'npm install && npm run dev -- --host 0.0.0.0 --port 5173'",
                volumes={str(project_path): {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                ports={'5173/tcp': port},
                environment={
                    "NODE_ENV": "development",
                    "NODE_OPTIONS": "--max-old-space-size=512"
                },
                detach=True,
                name=f"project-{project_id}",
                remove=True,  # Auto-remove when stopped
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Store container info
            self.containers[project_id] = {
                'container': container,
                'port': port,
                'status': 'starting',
                'project_path': str(project_path)
            }
            
            # Wait for startup
            await asyncio.sleep(5)
            
            # Check if container is still running
            container.reload()
            if container.status == 'running':
                self.containers[project_id]['status'] = 'running'
                logger.info(f"Started dev server for {project_id} on port {port}")
                return {
                    "project_id": project_id,
                    "status": "running",
                    "port": port,
                    "preview_url": f"http://YOUR_VPS_IP:{port}"
                }
            else:
                # Container failed to start
                self._release_port(port)
                del self.containers[project_id]
                logs = container.logs().decode('utf-8')
                logger.error(f"Container failed to start: {logs}")
                raise HTTPException(500, f"Failed to start dev server: {logs[-500:]}")
                
        except docker.errors.APIError as e:
            self._release_port(port)
            logger.error(f"Docker error: {e}")
            raise HTTPException(500, f"Docker error: {str(e)}")
    
    async def stop_dev_server(self, project_id: str):
        """Stop project's dev server container"""
        if project_id not in self.containers:
            return
        
        container_info = self.containers[project_id]
        container = container_info['container']
        port = container_info['port']
        
        try:
            container.stop(timeout=10)
            logger.info(f"Stopped container for project {project_id}")
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
        
        # Release port and cleanup
        self._release_port(port)
        del self.containers[project_id]
    
    async def update_file(self, project_id: str, file_path: str, content: str):
        """Update project file - triggers HMR automatically"""
        project_path = VPS_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Create directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated {file_path} in project {project_id}")
        return {"status": "updated", "file": file_path}
    
    async def read_file(self, project_id: str, file_path: str) -> str:
        """Read project file"""
        project_path = VPS_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not full_path.exists():
            raise HTTPException(404, f"File {file_path} not found")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def list_files(self, project_id: str) -> List[str]:
        """List all files in project"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # Skip node_modules and .git
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.docker']]
            
            for filename in filenames:
                if not filename.startswith('.'):
                    rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                    files.append(rel_path)
        
        return sorted(files)
    
    def get_project_status(self, project_id: str) -> Dict:
        """Get project and container status"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Read metadata
        metadata_file = project_path / ".project_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        
        # Container status
        container_status = "stopped"
        port = None
        if project_id in self.containers:
            container_info = self.containers[project_id]
            container_status = container_info['status']
            port = container_info['port']
        
        return {
            "project_id": project_id,
            "metadata": metadata,
            "container_status": container_status,
            "port": port,
            "preview_url": f"http://YOUR_VPS_IP:{port}" if port else None
        }
    
    async def cleanup(self):
        """Stop all containers on shutdown"""
        for project_id in list(self.containers.keys()):
            await self.stop_dev_server(project_id)

# Global project manager
project_manager = VPSProjectManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("VPS Projects API starting up...")
    
    # Check if boilerplate exists
    if not VPS_BOILERPLATE_PATH.exists():
        logger.warning(f"Boilerplate not found at {VPS_BOILERPLATE_PATH}")
        logger.info("Please ensure boilerplate is deployed to VPS")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await project_manager.cleanup()

app = FastAPI(title="VPS Projects API", version="2.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class CreateProjectRequest(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    files: Dict[str, str] = Field(default_factory=dict)

class UpdateFileRequest(BaseModel):
    content: str

# API Routes
@app.get("/")
def read_root():
    return {
        "message": "VPS Projects API", 
        "status": "running",
        "storage": str(VPS_PROJECTS_PATH),
        "boilerplate": str(VPS_BOILERPLATE_PATH),
        "boilerplate_exists": VPS_BOILERPLATE_PATH.exists(),
        "docker_available": True,
        "node_version": "Available in containers"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "vps-projects-api",
        "docker_available": True,
        "storage_path": str(VPS_PROJECTS_PATH),
        "active_containers": len(project_manager.containers)
    }

@app.post("/api/projects")
async def create_project(request: CreateProjectRequest):
    """Create new project from boilerplate"""
    try:
        metadata = await project_manager.create_project(request.project_id, request.files)
        return {
            "status": "created",
            "project": metadata,
            "message": "Project created successfully. Use /start-preview to begin development."
        }
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(500, f"Failed to create project: {str(e)}")

@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    projects = []
    
    if VPS_PROJECTS_PATH.exists():
        for project_dir in VPS_PROJECTS_PATH.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / ".project_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        
                    # Add container status
                    container_status = "stopped"
                    if metadata["id"] in project_manager.containers:
                        container_status = project_manager.containers[metadata["id"]]["status"]
                    
                    metadata["container_status"] = container_status
                    projects.append(metadata)
    
    return {"projects": projects}

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    return project_manager.get_project_status(project_id)

@app.post("/api/projects/{project_id}/start-preview")
async def start_preview(project_id: str):
    """Start development server for project"""
    return await project_manager.start_dev_server(project_id)

@app.post("/api/projects/{project_id}/stop-preview")
async def stop_preview(project_id: str):
    """Stop development server"""
    await project_manager.stop_dev_server(project_id)
    return {"status": "stopped", "project_id": project_id}

@app.get("/api/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """List all files in project"""
    files = await project_manager.list_files(project_id)
    return {"project_id": project_id, "files": files}

@app.get("/api/projects/{project_id}/files/{file_path:path}")
async def read_project_file(project_id: str, file_path: str):
    """Read specific file content"""
    content = await project_manager.read_file(project_id, file_path)
    return {"project_id": project_id, "file_path": file_path, "content": content}

@app.put("/api/projects/{project_id}/files/{file_path:path}")
async def update_project_file(project_id: str, file_path: str, request: UpdateFileRequest):
    """Update file content (triggers HMR)"""
    result = await project_manager.update_file(project_id, file_path, request.content)
    return result

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete project (stops container and archives files)"""
    # Stop container if running
    if project_id in project_manager.containers:
        await project_manager.stop_dev_server(project_id)
    
    # Archive project instead of deleting
    project_path = VPS_PROJECTS_PATH / project_id
    if project_path.exists():
        archive_path = VPS_BASE_PATH / "archives" / f"{project_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        archive_path.parent.mkdir(exist_ok=True)
        shutil.move(str(project_path), str(archive_path))
        
        return {"status": "archived", "project_id": project_id, "archive_path": str(archive_path)}
    
    raise HTTPException(404, f"Project {project_id} not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting VPS Projects API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)