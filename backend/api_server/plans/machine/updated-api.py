import os
import uuid
import asyncio
import json
import zipfile
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient, BlobClient
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;EndpointSuffix=core.windows.net"
QUEUE_NAME = "llm-jobs"
CONTAINER_NAME = "codebase-projects"
RESULT_DIR = "results"
PROJECTS_DIR = "projects"
POLL_INTERVAL_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 120

app = FastAPI(title="LLM Agent Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)
blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Request Models
class CommandRequest(BaseModel):
    project_id: str
    command: str
    working_dir: Optional[str] = None  # "frontend", "backend", or None for root

class FileRequest(BaseModel):
    project_id: str
    file_path: str
    working_dir: Optional[str] = None  # "frontend", "backend", or None for root

class FileCreateRequest(BaseModel):
    project_id: str
    file_path: str
    content: str
    working_dir: Optional[str] = None
    overwrite: Optional[bool] = False

class FileUpdateRequest(BaseModel):
    project_id: str
    file_path: str
    content: str
    working_dir: Optional[str] = None
    create_if_missing: Optional[bool] = True

class FileDeleteRequest(BaseModel):
    project_id: str
    file_path: str
    working_dir: Optional[str] = None

class SyncRequest(BaseModel):
    project_id: str
    force_refresh: Optional[bool] = False

class CloudflareDeployRequest(BaseModel):
    project_id: str
    project_name: str  # Cloudflare project name (must be unique)
    environment: Optional[str] = "production"  # or "staging"
    env_vars: Optional[Dict[str, str]] = {}  # Environment variables
    force_rebuild: Optional[bool] = False

def get_project_path(project_id: str, working_dir: Optional[str] = None) -> str:
    """Get the full path for a project, optionally in frontend/backend subdirectory"""
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if working_dir:
        return os.path.join(base_path, working_dir)
    return base_path

def download_project_from_azure(project_id: str) -> bool:
    """Download project structure from Azure blob storage"""
    try:
        container_client = blob_service.get_container_client(CONTAINER_NAME)
        project_base_path = os.path.join(PROJECTS_DIR, project_id)

        # Create project directory
        os.makedirs(project_base_path, exist_ok=True)

        print(f"Downloading project {project_id} from Azure...")

        # List all blobs for this project
        blob_list = container_client.list_blobs(name_starts_with=f"{project_id}/")

        downloaded_files = 0
        for blob in blob_list:
            # blob.name format: "project-id/frontend/src/App.js" or "project-id/backend/app.py"
            relative_path = blob.name[len(project_id)+1:]  # Remove "project-id/" prefix
            local_file_path = os.path.join(project_base_path, relative_path)

            # Create subdirectories if needed
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download file
            blob_client = container_client.get_blob_client(blob.name)
            with open(local_file_path, 'wb') as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())

            downloaded_files += 1

        print(f"Downloaded {downloaded_files} files for project {project_id}")

        # Update last access time
        os.utime(project_base_path, None)
        return True

    except Exception as e:
        print(f"Error downloading project {project_id}: {e}")
        return False

def is_project_cached(project_id: str) -> bool:
    """Check if project exists locally and has both frontend/backend dirs"""
    project_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(project_path):
        return False

    # Update last access time
    os.utime(project_path, None)
    return True

async def ensure_project_available(project_id: str, force_refresh: bool = False) -> bool:
    """Ensure project is available locally, download if needed"""
    if force_refresh or not is_project_cached(project_id):
        return download_project_from_azure(project_id)
    return True

# API Endpoints
@app.get("/")
async def root():
    return {"message": "LLM Agent Backend API", "status": "running", "cors": "enabled"}

@app.post("/sync")
async def sync_project(req: SyncRequest):
    """Sync a project from Azure storage to local cache"""
    try:
        success = await ensure_project_available(req.project_id, req.force_refresh)

        if success:
            project_path = get_project_path(req.project_id)

            # Get project info
            info = {
                "project_id": req.project_id,
                "status": "synced",
                "local_path": project_path,
                "has_frontend": os.path.exists(os.path.join(project_path, "frontend")),
                "has_backend": os.path.exists(os.path.join(project_path, "backend")),
            }

            # Count files
            total_files = 0
            for root, dirs, files in os.walk(project_path):
                total_files += len(files)

            info["total_files"] = total_files
            return info
        else:
            raise HTTPException(status_code=404, detail=f"Project {req.project_id} not found in Azure storage")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.post("/execute")
async def execute_command(req: CommandRequest):
    """Execute a command in a project environment"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "execute",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": req.command
    })

    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/read")
async def read_file(req: FileRequest):
    """Read a file from a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "read_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": req.file_path
    })

    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/create")
async def create_file(req: FileCreateRequest):
    """Create a new file in a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "create_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": {
            "file_path": req.file_path,
            "content": req.content,
            "overwrite": req.overwrite
        }
    })

    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/update")
async def update_file(req: FileUpdateRequest):
    """Update an existing file in a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "update_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": {
            "file_path": req.file_path,
            "content": req.content,
            "create_if_missing": req.create_if_missing
        }
    })

    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/delete")
async def delete_file(req: FileDeleteRequest):
    """Delete a file from a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "delete_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": req.file_path
    })

    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.get("/projects/{project_id}/info")
async def get_project_info(project_id: str):
    """Get information about a cached project"""
    project_path = get_project_path(project_id)

    if not os.path.exists(project_path):
        return {"project_id": project_id, "cached": False}

    info = {
        "project_id": project_id,
        "cached": True,
        "has_frontend": os.path.exists(os.path.join(project_path, "frontend")),
        "has_backend": os.path.exists(os.path.join(project_path, "backend")),
    }

    # Get directory structure
    structure = {}
    if info["has_frontend"]:
        structure["frontend"] = []
        frontend_path = os.path.join(project_path, "frontend")
        for item in os.listdir(frontend_path):
            structure["frontend"].append(item)

    if info["has_backend"]:
        structure["backend"] = []
        backend_path = os.path.join(project_path, "backend")
        for item in os.listdir(backend_path):
            structure["backend"].append(item)

    info["structure"] = structure
    return info

@app.post("/deploy/cloudflare")
async def deploy_to_cloudflare(req: CloudflareDeployRequest):
    """Deploy frontend to Cloudflare Pages"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Check if frontend directory exists
    frontend_path = get_project_path(req.project_id, "frontend")
    if not os.path.exists(frontend_path):
        return {"error": f"Frontend directory not found for project {req.project_id}"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "deploy_cloudflare",
        "project_id": req.project_id,
        "working_dir": "frontend",
        "payload": {
            "project_name": req.project_name,
            "environment": req.environment,
            "env_vars": req.env_vars,
            "force_rebuild": req.force_rebuild
        }
    })

    queue_client.send_message(job_message)

    # Wait for result with extended timeout for deployments
    time_waited = 0
    deployment_timeout = 600  # 10 minutes for deployment
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > deployment_timeout:
            return {"error": "Deployment timed out after 10 minutes"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.get("/health")
async def health_check():
    # Test Azure connectivity
    try:
        container_client = blob_service.get_container_client(CONTAINER_NAME)
        container_client.get_container_properties()
        azure_status = "connected"
    except:
        azure_status = "disconnected"

    # Check Cloudflare credentials
    cf_token = os.getenv('CLOUDFLARE_API_TOKEN')
    cf_account = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    cloudflare_status = "configured" if cf_token and cf_account else "not_configured"

    return {
        "status": "healthy",
        "queue": "connected",
        "azure_storage": azure_status,
        "cloudflare": cloudflare_status,
        "cors": "enabled"
    }

# OPTIONS handlers for CORS preflight requests
@app.options("/{path:path}")
async def options_handler():
    """Handle CORS preflight requests"""
    return {}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting VM API server with CORS support...")
    print("🌐 CORS enabled for all origins (configure for production)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
