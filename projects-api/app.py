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
import sys
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

# Set up environment for project service
os.environ["WORKSPACE_PATH"] = "/tmp/workspace"
os.environ["PROJECTS_PATH"] = "/tmp/projects"
os.environ["BOILERPLATE_PATH"] = str(Path(__file__).parent / "boilerplate")

# Create required directories
Path("/tmp/workspace").mkdir(parents=True, exist_ok=True)
Path("/tmp/projects").mkdir(parents=True, exist_ok=True)

# Try to import the projects router with error handling
try:
    from projects import router as projects_router
    # Include the projects router
    app.include_router(projects_router, prefix="/api")
    logger.info("Projects router loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import projects router: {e}")
    # Create a fallback router for basic functionality
    from fastapi import APIRouter
    fallback_router = APIRouter()
    
    @fallback_router.get("/projects")
    async def fallback_projects():
        return {"projects": [], "message": "Projects service not available"}
    
    app.include_router(fallback_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "message": "Projects API", 
        "status": "running", 
        "docs": "/docs",
        "node_version": os.popen("node --version").read().strip() if os.system("which node") == 0 else "Not installed",
        "python_version": sys.version
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "projects-api",
        "node_available": os.system("which node") == 0,
        "npm_available": os.system("which npm") == 0
    }

# Helper function to get project (simplified version)
def get_project_simple(project_id: str):
    """Simple project getter for preview functionality"""
    projects_path = Path("/tmp/projects")
    for project_dir in projects_path.iterdir():
        if project_dir.is_dir():
            metadata_file = project_dir / ".project_metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    data = json.load(f)
                    if data.get("id") == project_id:
                        return data
    return None

@app.post("/api/projects/{project_id}/preview/start")
async def start_preview(project_id: str):
    """Start the development server for live preview"""
    project = get_project_simple(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        port = await project_servers.start_dev_server(project_id, project["path"])
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
    project = get_project_simple(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if dev server is running
    if project_id not in project_servers.servers:
        # Try to start it
        try:
            await project_servers.start_dev_server(project_id, project["path"])
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
            # Forward the request with proper headers
            forward_headers = {}
            for k, v in request.headers.items():
                if k.lower() not in ['host', 'content-length', 'connection']:
                    forward_headers[k] = v
            
            # Set proper host header for Vite
            forward_headers['host'] = f'localhost:{port}'
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=await request.body() if request.method in ['POST', 'PUT', 'PATCH'] else None,
                follow_redirects=True
            )
            
            # Process response headers
            response_headers = {}
            for k, v in response.headers.items():
                if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                    response_headers[k] = v
            
            # Fix HTML content to use correct base path for assets
            content = response.content
            if response.headers.get('content-type', '').startswith('text/html'):
                content_str = content.decode('utf-8')
                # Replace Vite asset paths to go through our proxy
                base_url = f"/api/projects/{project_id}/preview"
                content_str = content_str.replace('src="/', f'src="{base_url}/')
                content_str = content_str.replace('href="/', f'href="{base_url}/')
                content_str = content_str.replace('from "/', f'from "{base_url}/')
                content_str = content_str.replace('import("/', f'import("{base_url}/')
                # Fix Vite specific paths
                content_str = content_str.replace('"/@', f'"{base_url}/@')
                content = content_str.encode('utf-8')
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'text/html')
            )
    except httpx.ConnectError:
        logger.error(f"Could not connect to dev server on port {port}")
        raise HTTPException(status_code=503, detail="Dev server is starting up, please try again in a few seconds")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# Add catch-all route for Vite assets that might not include the full path
@app.get("/@vite/{path:path}")
@app.get("/@react-refresh")
@app.get("/src/{path:path}")
async def vite_assets_fallback(request: Request):
    """Fallback for Vite assets that don't go through the preview proxy"""
    # Try to find an active project server and redirect
    if project_servers.servers:
        # Get the first active project (you might want to make this smarter)
        project_id = list(project_servers.servers.keys())[0]
        asset_path = request.url.path.lstrip('/')
        redirect_url = f"/api/projects/{project_id}/preview/{asset_path}"
        if request.url.query:
            redirect_url += f"?{request.url.query}"
        
        # Return a redirect
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url, status_code=302)
    
    raise HTTPException(status_code=404, detail="No active preview servers")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)