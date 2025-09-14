"""
FastAPI Streaming Conversation API
Provides real-time streaming interface for model conversations with action tracking
Azure-compatible deployment
"""
import os
import json
import uuid
import asyncio
import queue
import threading
import shutil
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from cloud_storage import get_cloud_storage

# Import the model system and project pool
from agent_class import BoilerplatePersistentGroq, FrontendCommandInterrupt
from project_pool_manager import get_pool_manager

# Import deployment modules
from api.netlify_deployment import deploy_frontend_to_netlify
from api.cloudflare_deployment import deploy_frontend_to_cloudflare

# Import session tracking for token usage analysis
# Stream session tracking now handled by token tracker's audit logging


# =============================================================================
# MODAL.COM BACKEND DEPLOYMENT API
# =============================================================================

class ModalDeploymentRequest(BaseModel):
    project_id: str
    app_name: str
    app_title: Optional[str] = "AI Generated Backend"
    app_description: Optional[str] = "Auto-generated FastAPI backend"
    secrets: Optional[Dict[str, str]] = None
    database_name: Optional[str] = None
    redeployment: bool = False

class ModalSecretsRequest(BaseModel):
    secret_name: str
    secrets: Dict[str, str]
    overwrite: bool = True

class ServerInfoRequest(BaseModel):
    type: str  # "logs" or "network"
    timestamp: int
    time: str
    # For logs
    logType: Optional[str] = None
    args: Optional[List[str]] = None
    message: Optional[str] = None
    # For network requests
    method: Optional[str] = None
    url: Optional[str] = None
    status: Optional[int] = None
    duration: Optional[int] = None
    requestData: Optional[str] = None
    responseData: Optional[str] = None
    responseHeaders: Optional[str] = None

class ModalDeploymentResponse(BaseModel):
    status: str
    app_name: str
    url: Optional[str] = None
    docs_url: Optional[str] = None
    logs_command: Optional[str] = None
    error: Optional[str] = None
    deployment_output: Optional[str] = None
    stdout: Optional[str] = None  # Add STDOUT capture
    stderr: Optional[str] = None  # Add STDERR capture

class ModalSecretsResponse(BaseModel):
    status: str
    secret_name: str
    secret_count: int
    error: Optional[str] = None

class BulkFileRequest(BaseModel):
    project_id: str
    file_paths: List[str]  # List of file paths to retrieve

class FileContent(BaseModel):
    file_path: str
    content: Optional[str] = None
    error: Optional[str] = None
    exists: bool = True
    success: bool = True

class BulkFileResponse(BaseModel):
    status: str
    project_id: str
    files: List[FileContent]
    total_files: int
    successful_files: int
    failed_files: int

class FileUpdateRequest(BaseModel):
    file_path: str
    content: str

class FileUpdateResponse(BaseModel):
    status: str
    project_id: str
    file_path: str
    message: str
    error: Optional[str] = None

# =============================================================================
# NETLIFY FRONTEND DEPLOYMENT API
# =============================================================================

class NetlifyDeploymentRequest(BaseModel):
    project_id: str
    project_name: Optional[str] = None

class NetlifyDeploymentResponse(BaseModel):
    status: str
    project_id: str
    netlify_url: Optional[str] = None
    site_name: Optional[str] = None
    backend_url: Optional[str] = None
    env_vars: Optional[int] = None
    deployed_at: Optional[str] = None
    error: Optional[str] = None

# CLOUDFLARE PAGES DEPLOYMENT API

class CloudflareDeploymentRequest(BaseModel):
    project_id: str
    project_name: Optional[str] = None  # Auto-generated if not provided
    environment: Optional[str] = "production"
    env_vars: Optional[Dict[str, str]] = None  # Only for overrides, project .env is used by default

class CloudflareDeploymentResponse(BaseModel):
    status: str
    project_id: str
    deployment_url: Optional[str] = None
    preview_url: Optional[str] = None
    project_name: Optional[str] = None
    environment: Optional[str] = None
    logs: Optional[List[str]] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None


# Separate Azure storage clients for resource isolation
_streaming_azure_client = None
_general_azure_client = None

def get_streaming_azure_client():
    """Get dedicated Azure client for streaming operations (highest priority)"""
    global _streaming_azure_client
    if _streaming_azure_client is None:
        from cloud_storage import AzureBlobStorage
        _streaming_azure_client = AzureBlobStorage()
        print("🎯 Initialized dedicated Azure client for STREAMING (high priority)")
    return _streaming_azure_client

def get_general_azure_client():
    """Get shared Azure client for general API operations"""
    global _general_azure_client
    if _general_azure_client is None:
        from cloud_storage import AzureBlobStorage
        _general_azure_client = AzureBlobStorage()
        print("🔧 Initialized shared Azure client for GENERAL APIs")
    return _general_azure_client

async def create_modal_secrets_standalone(request: ModalSecretsRequest) -> ModalSecretsResponse:
    """Create or update Modal.com secrets programmatically - standalone reusable function"""
    try:
        import subprocess
        import tempfile

        print(f"🔐 Creating Modal secrets: {request.secret_name}")

        # Build modal secret create command
        cmd = ["modal", "secret", "create", request.secret_name]

        # Add overwrite flag if needed
        if request.overwrite:
            # Delete existing secret first (ignore errors) - async
            try:
                proc = await asyncio.create_subprocess_exec(
                    "modal", "secret", "delete", request.secret_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()  # Don't care about result for deletion
            except:
                pass

        # Add all key=value pairs
        for key, value in request.secrets.items():
            cmd.append(f"{key}={value}")

        # Execute modal command (async to avoid blocking other requests)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        stdout = stdout.decode('utf-8') if stdout else ""
        stderr = stderr.decode('utf-8') if stderr else ""

        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, stderr)

        # Create result object to match original subprocess.run interface
        result = type('Result', (), {
            'stdout': stdout,
            'stderr': stderr,
            'returncode': proc.returncode
        })()

        print(f"✅ Modal secrets created: {request.secret_name}")

        return ModalSecretsResponse(
            status="success",
            secret_name=request.secret_name,
            secret_count=len(request.secrets) if isinstance(request.secrets, (dict, list)) else 0
        )

    except subprocess.CalledProcessError as e:
        error_msg = f"Modal secrets creation failed: {e.stderr or str(e)}"
        print(f"❌ {error_msg}")
        return ModalSecretsResponse(
            status="error",
            secret_name=request.secret_name,
            secret_count=0,
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Secrets creation error: {str(e)}"
        print(f"❌ {error_msg}")
        return ModalSecretsResponse(
            status="error",
            secret_name=request.secret_name,
            secret_count=0,
            error=error_msg
        )



def generate_modal_secret_name(app_name: str) -> str:
    """Generate a Modal-compliant secret name that's under 64 characters"""
    import hashlib

    # Start with app_name prefix (truncated if needed)
    base_name = app_name
    suffix = "-secrets"

    # If the full name would be too long, create a shorter version
    full_name = f"{base_name}{suffix}"
    if len(full_name) >= 64:
        # Create a hash-based short name that's deterministic
        hash_obj = hashlib.md5(app_name.encode())
        short_hash = hash_obj.hexdigest()[:8]

        # Use first part of app_name + hash + suffix
        max_base_length = 64 - len(suffix) - len(short_hash) - 1  # -1 for dash
        short_base = base_name[:max_base_length].rstrip('-')
        full_name = f"{short_base}-{short_hash}{suffix}"

    # Ensure it's under 64 chars and valid
    full_name = full_name[:63]  # Leave room for safety

    # Replace any invalid characters with dashes
    import re
    full_name = re.sub(r'[^a-zA-Z0-9._-]', '-', full_name)

    return full_name

def generate_modal_volume_name(app_name: str) -> str:
    """Generate a Modal-compliant volume name that's under 64 characters"""
    import hashlib
    import re

    # Start with app_name prefix (truncated if needed)
    base_name = app_name
    suffix = "-database"

    # If the full name would be too long, create a shorter version
    full_name = f"{base_name}{suffix}"
    if len(full_name) >= 64:
        # Create a hash-based short name that's deterministic
        hash_obj = hashlib.md5(app_name.encode())
        short_hash = hash_obj.hexdigest()[:8]

        # Use first part of app_name + hash + suffix
        max_base_length = 64 - len(suffix) - len(short_hash) - 1  # -1 for dash
        short_base = base_name[:max_base_length].rstrip('-')
        full_name = f"{short_base}-{short_hash}{suffix}"

    # Ensure it's under 64 chars and valid
    full_name = full_name[:63]  # Leave room for safety

    # Replace any invalid characters with underscores (volumes prefer underscores)
    full_name = re.sub(r'[^a-zA-Z0-9._-]', '_', full_name)

    # Replace consecutive dashes/underscores with single underscore
    full_name = re.sub(r'[-_]+', '_', full_name)

    # Ensure it doesn't start or end with dash/underscore
    full_name = full_name.strip('-_')

    return full_name

# Import shared utility function
from utils.basic import generate_short_app_name

def extract_modal_url(output: str, app_name: str) -> Optional[str]:
    """Extract the deployed URL from Modal's output"""
    # First, try to find complete URLs in single lines
    lines = output.split('\n')
    for line in lines:
        if 'modal.run' in line and 'https://' in line:
            words = line.split()
            for word in words:
                if word.startswith('https://') and 'modal.run' in word:
                    return word.rstrip('.,!?')
    
    # Second, handle URLs broken across lines (common in Modal output)
    # Look for patterns like "https://...modal.r" followed by "un" on next lines
    import re
    
    # Remove ANSI color codes and clean up the output
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    
    # Try to find broken URLs and reconstruct them
    url_pattern = r'https://[^\s]*?--[^\s]*?-fastapi-app\.modal\.r\s*un'
    matches = re.findall(url_pattern, clean_output.replace('\n', ' '))
    if matches:
        # Reconstruct the URL by removing spaces
        url = matches[0].replace(' ', '').replace('r un', 'run')
        return url
    
    # Third, try a more flexible pattern to catch any modal.run URLs
    url_pattern = r'https://[^\s]*modal\.run[^\s]*'
    matches = re.findall(url_pattern, clean_output)
    if matches:
        return matches[0].rstrip('.,!?')
    
    # Fallback URL pattern (will need to be updated with actual username)
    return f"https://your-username--{app_name}-fastapi-app.modal.run"




async def _execute_modal_deployment(request: ModalDeploymentRequest) -> ModalDeploymentResponse:
    """Execute the actual Modal deployment (extracted from original function)"""
    # Initialize stdout/stderr variables to capture deployment output
    deployment_stdout = ""
    deployment_stderr = ""

    try:
        from cloud_storage import get_cloud_storage
        import tempfile
        import subprocess
        import shutil
        from pathlib import Path
        import os

        print(f"🚀 Starting REAL Modal deployment: {request.app_name}")
        print(f"📋 Project: {request.project_id}")

        # Check if project has backend files first
        # Use general Azure client for deployment operations
        cloud_storage = get_general_azure_client()

        # Check for backend files
        backend_files = cloud_storage.list_files(request.project_id, 'backend/')
        if not backend_files:
            raise Exception(f"No backend files found for project {request.project_id}")

        print(f"📂 Found {len(backend_files)} backend files - proceeding with REAL deployment")

        # Create temporary directory for REAL deployment
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_path = temp_path / "project"
            project_path.mkdir(parents=True)

            print(f"📥 Downloading backend from Azure Storage...")

            # Download all backend files
            success_count = 0
            for file_path in backend_files:
                try:
                    content = cloud_storage.download_file(request.project_id, file_path)
                    if content:
                        # Remove 'backend/' prefix and create local file
                        relative_path = file_path.replace('backend/', '', 1)
                        local_file = project_path / relative_path
                        local_file.parent.mkdir(parents=True, exist_ok=True)
                        local_file.write_text(content, encoding='utf-8')
                        success_count += 1
                    else:
                        print(f"⚠️ Failed to download: {file_path}")
                except Exception as e:
                    print(f"❌ Error downloading {file_path}: {e}")

            if success_count == 0:
                raise Exception(f"Failed to download any backend files for project {request.project_id}")

            print(f"✅ Successfully downloaded {success_count} backend files")

            # Generate short, Modal-compliant app name
            short_app_name = generate_short_app_name(request.project_id)
            print(f"🔧 Generated short app name: {short_app_name} (from {request.app_name})")

            # Set up environment variables for the deployment
            env = os.environ.copy()
            env.update({
                "MODAL_APP_NAME": short_app_name,
                "APP_TITLE": request.app_title or "AI Generated Backend",
                "APP_DESCRIPTION": request.app_description or "Auto-generated FastAPI backend",
            })

            # Set database name if provided
            if request.database_name:
                env["DATABASE_NAME"] = request.database_name
            else:
                env["DATABASE_NAME"] = f"{short_app_name}_database.db"

            secret_name = generate_modal_secret_name(short_app_name)
            env["MODAL_SECRET_NAME"] = secret_name

            # Handle secrets creation - ALWAYS ensure .env file and Modal secrets are synchronized
            secrets_created_successfully = True
            final_secrets = {}

            # STEP 1: Download and parse existing .env file to get current keys
            print(f"📥 Reading existing .env file to ensure synchronization...")
            env_path = "backend/.env"
            existing_env = cloud_storage.download_file(request.project_id, env_path) or ""
            
            # Parse existing .env variables
            env_vars = {}
            for line in existing_env.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    env_vars[k] = v
            
            print(f"🔍 Found {len(env_vars)} existing keys in .env: {list(env_vars.keys())}")

            # STEP 2: Define default secrets that should always exist
            default_secrets = {
                "SECRET_KEY": f"auto-generated-key-{request.app_name}-{hash(request.project_id) % 10000}",
                "DATABASE_NAME": request.database_name or f"{request.app_name}_database.db",
                "APP_TITLE": request.app_title or "AI Generated Backend",
                "APP_DESCRIPTION": request.app_description or "Auto-generated FastAPI backend",
                "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
                "EXA_API_KEY": "16fe8779-7264-44c1-a911-e8187cb629c6",
                "MODAL_SECRET_NAME": secret_name
            }

            # STEP 3: Merge all sources in order of priority: .env existing > request.secrets > defaults
            final_secrets = {**default_secrets}
            if request.secrets:
                final_secrets.update(request.secrets)
            # Existing .env keys take highest priority (don't overwrite them)
            for key, value in env_vars.items():
                final_secrets[key] = value

            print(f"🔗 Final secret set has {len(final_secrets)} keys: {list(final_secrets.keys())}")

            # STEP 4: Update .env file with complete key set
            new_env_lines = []
            for k, v in sorted(final_secrets.items()):
                if ' ' in v or '"' in v:
                    v = v.replace('"', '\\"')
                    new_env_lines.append(f'{k}="{v}"')
                else:
                    new_env_lines.append(f'{k}={v}')
            
            new_env_content = '\n'.join(new_env_lines) + '\n'
            cloud_storage.upload_file(request.project_id, env_path, new_env_content)
            print(f"✅ Updated .env with {len(final_secrets)} synchronized keys")

            # STEP 5: Create Modal secrets using the synchronized key set
            if not request.redeployment:
                print(f"🔐 Creating Modal secrets for first deployment")

                try:
                    secrets_request = ModalSecretsRequest(
                        secret_name=secret_name,
                        secrets=final_secrets,
                        overwrite=False
                    )
                    secrets_result = await create_modal_secrets_standalone(secrets_request)

                    if secrets_result and secrets_result.status == "success":
                        print(f"✅ Secrets created: {secret_name}")
                        secrets_created_successfully = True
                    else:
                        print(f"⚠️ Secret creation failed: {secrets_result.error if secrets_result else 'Unknown error'}")
                        print(f"🔄 Falling back to redeployment mode (secrets may already exist)")
                        secrets_created_successfully = False
                except Exception as e:
                    print(f"⚠️ Secret creation error: {e}")
                    print(f"🔄 Falling back to redeployment mode (secrets may already exist)")
                    secrets_created_successfully = False
            else:
                print(f"🔄 Redeployment mode: .env synchronized, secrets should exist...")
                secrets_created_successfully = False

            # Change to project directory and deploy with REAL Modal CLI
            original_cwd = os.getcwd()
            os.chdir(project_path)

            try:
                print(f"🚀 REAL Modal deployment starting...")

                # Run ACTUAL modal deploy command with virtual environment
                proc = await asyncio.create_subprocess_exec(
                    "modal", "deploy", "app.py",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)  # 10 minutes
                    stdout = stdout.decode('utf-8') if stdout else ""
                    stderr = stderr.decode('utf-8') if stderr else ""

                    # Capture for return to LLM
                    deployment_stdout = stdout
                    deployment_stderr = stderr

                    if proc.returncode != 0:
                        print(f"❌ Modal deploy failed with exit code {proc.returncode}")
                        print(f"📤 STDOUT: {stdout}")
                        print(f"📥 STDERR: {stderr}")

                        # Check if failure is due to missing secrets
                        if "Secret" in stderr and "not found" in stderr and request.redeployment:
                            print(f"🔍 Detected missing secrets during redeployment - attempting to create them...")

                            try:
                                # Create the missing secrets
                                secrets_request = ModalSecretsRequest(
                                    secret_name=secret_name,
                                    secrets=final_secrets,
                                    overwrite=False  # Don't overwrite in case some secrets exist
                                )
                                secrets_result = await create_modal_secrets_standalone(secrets_request)

                                if secrets_result and secrets_result.status == "success":
                                    print(f"✅ Created missing secrets: {secret_name}")
                                    print(f"🔄 Retrying Modal deployment...")

                                    # Retry the deployment with secrets now available
                                    retry_proc = await asyncio.create_subprocess_exec(
                                        "modal", "deploy", "app.py",
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE,
                                        env=env
                                    )

                                    try:
                                        retry_stdout, retry_stderr = await asyncio.wait_for(retry_proc.communicate(), timeout=600)
                                        retry_stdout = retry_stdout.decode('utf-8') if retry_stdout else ""
                                        retry_stderr = retry_stderr.decode('utf-8') if retry_stderr else ""

                                        # Update captured output with retry results
                                        deployment_stdout = retry_stdout
                                        deployment_stderr = retry_stderr

                                        if retry_proc.returncode != 0:
                                            print(f"❌ Modal deploy retry failed with exit code {retry_proc.returncode}")
                                            print(f"📤 RETRY STDOUT: {retry_stdout}")
                                            print(f"📥 RETRY STDERR: {retry_stderr}")
                                            retry_error_details = f"Command '['modal', 'deploy', 'app.py']' returned non-zero exit status {retry_proc.returncode} (retry attempt).\n\nSTDOUT:\n{retry_stdout}\n\nSTDERR:\n{retry_stderr}"
                                            raise subprocess.CalledProcessError(retry_proc.returncode, ["modal", "deploy", "app.py"], retry_error_details)
                                        else:
                                            print(f"✅ Modal deploy retry succeeded!")
                                            # Use retry output for URL extraction
                                            stdout = retry_stdout
                                            stderr = retry_stderr

                                    except asyncio.TimeoutError:
                                        retry_proc.kill()
                                        raise subprocess.TimeoutExpired(["modal", "deploy", "app.py"], 600)

                                else:
                                    print(f"❌ Failed to create missing secrets: {secrets_result.error if secrets_result else 'Unknown error'}")
                                    error_details = f"Command '['modal', 'deploy', 'app.py']' returned non-zero exit status {proc.returncode}. Secret creation failed.\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
                                    raise subprocess.CalledProcessError(proc.returncode, ["modal", "deploy", "app.py"], error_details)

                            except Exception as secret_error:
                                print(f"❌ Error handling missing secrets: {secret_error}")
                                error_details = f"Command '['modal', 'deploy', 'app.py']' returned non-zero exit status {proc.returncode}. Secret handling error: {secret_error}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
                                raise subprocess.CalledProcessError(proc.returncode, ["modal", "deploy", "app.py"], error_details)
                        else:
                            # Not a secrets error, or not a redeployment - raise original error with full details
                            error_details = f"Command '['modal', 'deploy', 'app.py']' returned non-zero exit status {proc.returncode}.\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
                            raise subprocess.CalledProcessError(proc.returncode, ["modal", "deploy", "app.py"], error_details)

                    print(f"✅ Modal deploy command completed successfully")

                    # Extract URL from Modal output
                    output = stdout + stderr
                    deployed_url = extract_modal_url(output, request.app_name)

                    if not deployed_url or "placeholder" in deployed_url:
                        # Fallback URL generation if extraction fails
                        import hashlib
                        hash_suffix = hashlib.md5(request.project_id.encode()).hexdigest()[:8]
                        deployed_url = f"https://user--{request.app_name}-{hash_suffix}.modal.run"

                    print(f"✅ Deployment successful: {deployed_url}")

                    # Update project metadata with deployment information
                    try:
                        from datetime import datetime

                        # Load existing metadata
                        existing_metadata = cloud_storage.load_project_metadata(request.project_id) or {}

                        # Update with deployment info
                        deployment_info = {
                            "backend_deployment": {
                                "status": "deployed",
                                "url": deployed_url,
                                "docs_url": f"{deployed_url}/docs" if deployed_url else None,
                                "app_name": request.app_name,
                                "secret_name": secret_name,
                                "secret_keys": list(final_secrets.keys()),
                                "deployed_at": datetime.now().isoformat(),
                                "last_deployment": datetime.now().isoformat()
                            }
                        }

                        # Merge with existing metadata
                        updated_metadata = {**existing_metadata, **deployment_info}

                        # Save updated metadata
                        metadata_success = cloud_storage.save_project_metadata(request.project_id, updated_metadata)
                        if metadata_success:
                            print(f"✅ Updated project metadata with deployment info")
                        else:
                            print(f"⚠️ Failed to update project metadata")

                        # Update frontend .env file with backend URL (only on first deployment)
                        if not request.redeployment:
                            env_content = f"VITE_APP_BACKEND_URL={deployed_url}\nVITE_APP_PROJECT_ID={request.project_id}\n"
                            env_success = cloud_storage.upload_file(request.project_id, "frontend/.env", env_content)
                            if env_success:
                                print(f"✅ Updated frontend .env with backend URL")
                            else:
                                print(f"⚠️ Failed to update frontend .env file")

                    except Exception as e:
                        print(f"⚠️ Error updating project metadata: {e}")

                except asyncio.TimeoutError:
                    proc.kill()
                    raise subprocess.TimeoutExpired(["modal", "deploy", "app.py"], 600)

            finally:
                os.chdir(original_cwd)

        return ModalDeploymentResponse(
            status="success",
            app_name=request.app_name,
            url=deployed_url,
            docs_url=f"{deployed_url}/docs",
            logs_command=f"modal logs {request.app_name}",
            deployment_output=f"Successfully deployed {request.app_name} with {len(backend_files)} backend files",
            stdout=deployment_stdout,  # Include captured STDOUT
            stderr=deployment_stderr   # Include captured STDERR
        )

    except subprocess.CalledProcessError as e:
        # For subprocess errors, use the detailed error information we prepared
        error_details = e.stderr if e.stderr else str(e)
        return ModalDeploymentResponse(
            status="error",
            app_name=request.app_name,
            error=error_details,
            stdout=deployment_stdout,  # Include captured STDOUT
            stderr=deployment_stderr   # Include captured STDERR
        )
    except Exception as e:
        return ModalDeploymentResponse(
            status="error",
            app_name=request.app_name,
            error=str(e),
            stdout=deployment_stdout,  # Include captured STDOUT
            stderr=deployment_stderr   # Include captured STDERR
        )




# Create FastAPI app
def create_app():

    app = FastAPI(title="Model Conversation API with Project Pool", version="1.0.0")

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global storage for active conversations
    active_conversations: Dict[str, BoilerplatePersistentGroq] = {}
    conversation_metadata: Dict[str, dict] = {}

    # Global storage for deployment status tracking
    deployment_status: Dict[str, dict] = {}

    class ConversationRequest(BaseModel):
        message: str
        conversation_id: Optional[str] = None
        project_id: Optional[str] = None
        action_result: Optional[bool] = False
        images: Optional[List[str]] = None  # Base64 encoded images from frontend

    class StreamChunk(BaseModel):
        type: str  # "text", "action_start", "action_content", "action_result", "error"
        data: dict
        conversation_id: str
        timestamp: str
        action_id: Optional[str] = None

    class ConversationInfo(BaseModel):
        conversation_id: str
        project_id: Optional[str]
        created_at: str
        last_activity: str
        message_count: int
        status: str

    def generate_conversation_id() -> str:
        """Generate a unique conversation ID"""
        return f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    def get_api_key() -> str:
        """Get API key from environment"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = os.getenv("OPENROUTER_API_KEY")  # Fallback to OpenRouter key
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY or OPENROUTER_API_KEY environment variable is required")
        return api_key

    def create_stream_chunk(chunk_type: str, data: dict, conversation_id: str, action_id: str = None) -> str:
        """Create a properly formatted stream chunk"""
        chunk = StreamChunk(
            type=chunk_type,
            data=data,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            action_id=action_id
        )
        return f"data: {chunk.model_dump_json()}\n\n"

    class StreamingModelWrapper:
        """Wrapper to capture model streaming and actions"""

        def __init__(self, model_system: BoilerplatePersistentGroq, conversation_id: str):
            self.model_system = model_system
            self.conversation_id = conversation_id
            self.current_action_id = None

            # File tracking for this streaming session
            self.files_created = []  # List of file paths created
            self.files_updated = []  # List of file paths updated
            
            # Session tracking for token usage analysis
            self.session_id = None
            self.initial_token_state = None

            # Load existing streaming chunks from this conversation (cumulative approach)
            project_id = getattr(model_system, 'project_id', None)
            if project_id:
                try:
                    # Use dedicated streaming Azure client for highest priority
                    cloud_storage = get_streaming_azure_client()
                    self.streaming_chunks = cloud_storage.load_conversation_history_streaming(project_id)
                    print(f"📦 Loaded {len(self.streaming_chunks)} existing streaming chunks from conversation")
                except Exception as e:
                    print(f"⚠️ Failed to load existing streaming chunks: {e}")
                    self.streaming_chunks = []
            else:
                self.streaming_chunks = []  # New conversation, start fresh

            self.last_save_count = len(self.streaming_chunks)  # Track baseline for saves

        async def stream_response(self, message) -> AsyncGenerator[str, None]:
            """Stream the model response with action tracking"""
            try:
                # Handle both string messages and content arrays
                if isinstance(message, list):
                    # Extract text from content array for preview
                    text_content = ""
                    for item in message:
                        if item.get("type") == "text":
                            text_content = item.get("text", "")
                            break
                    print(f"🌊 Starting stream_response for content array with text: {text_content[:30]}...")
                else:
                    print(f"🌊 Starting stream_response for: {message[:30]}...")
                
                # Start token tracker session for audit logging
                project_id = getattr(self.model_system, 'project_id', None) or "unknown"
                if hasattr(self.model_system, '_token_tracker') and self.model_system._token_tracker:
                    # Generate session ID based on conversation and timestamp
                    session_id = f"{self.conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.session_id = self.model_system._token_tracker.start_session(session_id)
                    print(f"🎯 Token audit session started: {self.session_id}")
                
                # Capture initial token state
                if hasattr(self.model_system, '_token_tracker') and self.model_system._token_tracker:
                    self.initial_token_state = self.model_system._token_tracker.get_token_usage()
                    print(f"🎯 Session {self.session_id}: Initial token state captured - {self.initial_token_state.get('total_tokens', 0):,} tokens")
                
                # Use a simple thread-safe queue
                import queue
                stream_queue = queue.Queue()
                action_counter = 0
                model_finished = threading.Event()

                def queue_callback(content_type: str, content: str, action_data: dict = None):
                    """Callback to add content to stream queue (thread-safe)"""
                    nonlocal action_counter

                    if content_type == "action_start":
                        action_counter += 1
                        action_id = f"action_{action_counter}"
                        chunk = create_stream_chunk("action_start", {
                            "action_type": action_data.get("action_type") if action_data else "unknown",
                            "action_details": action_data or {},
                            "content": content
                        }, self.conversation_id, action_id)
                    elif content_type == "action_result":
                        # Extract important fields to root level for file operations
                        data = {
                            "result": content,
                            "status": action_data.get("status") if action_data else "completed",
                            "action_details": action_data or {}
                        }

                        # For file operations, include action_type and content at root level
                        if action_data:
                            action_type = action_data.get("action_type")
                            if action_type in ["read_file", "create_file", "update_file", "file"]:
                                data["action_type"] = action_type
                                if "content" in action_data:
                                    data["content"] = action_data["content"]
                                if "file_path" in action_data:
                                    file_path = action_data["file_path"]
                                    data["file_path"] = file_path

                                    # Track file operations for session summary
                                    if action_type == "create_file":
                                        if file_path not in self.files_created:
                                            self.files_created.append(file_path)
                                            print(f"📄 FILE TRACKING: Created {file_path}")
                                    elif action_type == "update_file":
                                        # Only track as updated if the status indicates success
                                        status = action_data.get("status", "completed")
                                        if status == "success" and file_path not in self.files_updated:
                                            self.files_updated.append(file_path)
                                            print(f"📝 FILE TRACKING: Updated {file_path}")
                                        elif status == "error":
                                            print(f"❌ FILE TRACKING: Failed to update {file_path}")
                                    elif action_type == "file":
                                        # "file" action_type is typically used for creating files
                                        if file_path not in self.files_created:
                                            self.files_created.append(file_path)
                                            print(f"📄 FILE TRACKING: Created {file_path} (via file action)")

                        chunk = create_stream_chunk("action_result", data, self.conversation_id, f"action_{action_counter}")
                    elif content_type == "assistant_message":
                        chunk = create_stream_chunk("assistant_message", {
                            "content": content
                        }, self.conversation_id)
                    elif content_type == "error":
                        chunk = create_stream_chunk("error", {
                            "error": content,
                            "action_details": action_data or {}
                        }, self.conversation_id)
                    else:
                        # Legacy text type - convert to assistant message
                        chunk = create_stream_chunk("assistant_message", {
                            "content": content
                        }, self.conversation_id)

                    # Collect streaming chunk in memory (save at strategic points for performance)
                    try:
                        import json

                        # Parse the chunk data to collect it
                        chunk_lines = chunk.split('\n')
                        data_line = next((line for line in chunk_lines if line.startswith('data: ')), None)

                        if data_line:
                            chunk_json_str = data_line[6:]  # Remove 'data: '
                            chunk_data = json.loads(chunk_json_str)

                            # Collect in memory for batch saving later
                            self.streaming_chunks.append(chunk_data)

                            # Strategic saving at certain points
                            should_save_now = (
                                # Save every 10 chunks to avoid losing too much data
                                len(self.streaming_chunks) % 10 == 0 or
                                # Save after action_result chunks (good completion points)
                                content_type == "action_result" or
                                # Save after assistant_message chunks that look like completions
                                (content_type == "assistant_message" and
                                ("completed" in content.lower() or "✅" in content or "finished" in content.lower()))
                            )

                            if should_save_now:
                                # Non-blocking save in background thread
                                import threading
                                save_thread = threading.Thread(
                                    target=self._save_streaming_chunks_sync,
                                    daemon=True
                                )
                                save_thread.start()

                    except Exception as e:
                        print(f"⚠️ Failed to collect streaming chunk: {e}")

                    # Thread-safe queue put
                    stream_queue.put(chunk)

                # Yield conversation/project identifiers FIRST (most important!)
                first_chunk_time = datetime.now()
                project_id = getattr(self.model_system, 'project_id', None)

                # Calculate time to first chunk
                if hasattr(self, 'request_start_time'):
                    time_to_first_chunk = (first_chunk_time - self.request_start_time).total_seconds()
                    print(f"⚡ TIME TO FIRST CHUNK: {time_to_first_chunk:.3f}s")

                yield create_stream_chunk("conversation_info", {
                    "conversation_id": self.conversation_id,
                    "project_id": project_id,
                    "timestamp": first_chunk_time.isoformat(),
                    "status": "streaming_started",
                    "time_to_first_chunk_ms": round(time_to_first_chunk * 1000, 1) if hasattr(self, 'request_start_time') else None
                }, self.conversation_id)
                await asyncio.sleep(0.01)  # Allow immediate flush

                # Yield initial processing message
                yield create_stream_chunk("text", {
                    "content": f"🚀 Processing your request: {message[:100]}..."
                }, self.conversation_id)
                await asyncio.sleep(0.01)  # Allow immediate flush

                # Start model execution as async task (no threads needed!)
                async def run_model():
                    try:
                        result = await self._execute_model_with_streaming(message, queue_callback)
                        stream_queue.put(("FINAL_RESULT", result))
                    except Exception as e:
                        stream_queue.put(("ERROR", str(e)))
                    finally:
                        model_finished.set()
                        stream_queue.put(("FINISHED", None))

                # Create async task instead of thread
                model_task = asyncio.create_task(run_model())

                # Stream content from queue with immediate yielding
                while True:
                    try:
                        # Wait for items with very short timeout for real-time streaming
                        item = stream_queue.get(timeout=0.01)

                        if isinstance(item, tuple):
                            command, data = item
                            if command == "FINAL_RESULT":
                                project_id = getattr(self.model_system, 'project_id', None)

                                # Prepare file tracking summary
                                files_changed = self._get_file_tracking_summary()

                                yield create_stream_chunk("text", {
                                    "content": "✅ Conversation completed successfully",
                                    "final_result": data,
                                    "project_id": project_id,
                                    "files_changed": files_changed
                                }, self.conversation_id)
                            elif command == "ERROR":
                                project_id = getattr(self.model_system, 'project_id', None)

                                # Include file tracking even in error cases
                                files_changed = self._get_file_tracking_summary()

                                yield create_stream_chunk("error", {
                                    "error": data,
                                    "message": "An error occurred during model execution",
                                    "project_id": project_id,
                                    "files_changed": files_changed
                                }, self.conversation_id)
                            elif command == "FINISHED":
                                break
                        else:
                            # Regular stream chunk - yield immediately
                            yield item
                            await asyncio.sleep(0.001)  # Very brief pause for responsiveness

                    except queue.Empty:
                        # Check if model finished - if so, break after a short delay
                        if model_finished.is_set():
                            # Give a little time for any final messages
                            await asyncio.sleep(0.1)
                            # Check one more time for any remaining items
                            try:
                                while True:
                                    item = stream_queue.get_nowait()
                                    if isinstance(item, tuple) and item[0] == "FINISHED":
                                        break
                                    elif not isinstance(item, tuple):
                                        yield item
                                        await asyncio.sleep(0.001)
                            except queue.Empty:
                                pass
                            break
                        # Continue waiting if model still running
                        await asyncio.sleep(0.01)
                        continue
                    except Exception as e:
                        yield create_stream_chunk("error", {
                            "error": str(e),
                            "message": "Error in streaming loop"
                        }, self.conversation_id)
                        break

            except Exception as e:
                yield create_stream_chunk("error", {
                    "error": str(e),
                    "message": "Failed to initialize streaming"
                }, self.conversation_id)
            finally:
                # End token tracker session for audit logging
                if hasattr(self.model_system, '_token_tracker') and self.model_system._token_tracker:
                    try:
                        self.model_system._token_tracker.end_session()
                    except Exception as e:
                        print(f"⚠️ Failed to end token tracking session: {e}")
                
                # Batch save all streaming chunks to Azure at the end
                await self._save_streaming_chunks_batch()

        async def _execute_model_with_streaming(self, message: str, stream_callback) -> dict:
            """Execute the model request with proper action streaming (async for concurrency)"""
            try:
                # Initial status updates
                if hasattr(self.model_system, 'project_id') and self.model_system.project_id:
                    stream_callback("assistant_message", f"I'll help you update your project: {self.model_system.project_id}")
                    mode = "update"
                else:
                    stream_callback("assistant_message", f"I'll create a new project for you based on your request.")
                    mode = "creation"

                # Call the actual processing method with streaming callback (now async!)
                if hasattr(self.model_system, '_process_update_request_with_interrupts'):
                    result = await self.model_system._process_update_request_with_interrupts(message, mode=mode, streaming_callback=stream_callback)

                    # Save conversation history
                    if hasattr(self.model_system, '_save_conversation_history'):
                        self.model_system._save_conversation_history()
                else:
                    stream_callback("error", f"{mode} processing method not available")
                    result = f"{mode} processing method not available"

                return {
                    "status": "completed",
                    "result": result,
                    "project_id": getattr(self.model_system, 'project_id', None)
                }

            except Exception as e:
                print(f"🐛 STREAMING API: Exception caught - type: {type(e).__name__}, class name: {e.__class__.__name__}")

                # Check if this is a frontend command interrupt
                if e.__class__.__name__ == 'FrontendCommandInterrupt':
                    print(f"🚨 STREAMING API: FRONTEND COMMAND INTERRUPT DETECTED: {e.command}")
                    print(f"🚨 STREAMING API: About to return interrupted status...")

                    # Send the command to frontend via stream
                    stream_callback("action_start", f"Running frontend command: {e.command}", {
                        "action_type": "run_command",
                        "command": e.command,
                        "cwd": e.cwd,
                        "needs_interrupt": True,
                        "project_id": e.project_id
                    })

                    # Return interrupt signal with file tracking information
                    interrupt_result = {
                        "status": "interrupted",
                        "reason": "frontend_command",
                        "command": e.command,
                        "cwd": e.cwd,
                        "project_id": e.project_id,
                        "message": f"Stream interrupted for frontend command: {e.command}",
                        "files_changed": self._get_file_tracking_summary()
                    }
                    print(f"🚨 STREAMING API: Returning interrupt result: {interrupt_result}")
                    return interrupt_result
                else:
                    print(f"🐛 STREAMING API: Not a frontend interrupt, exception: {e}")
                    stream_callback("error", f"Model execution failed: {str(e)}")
                    raise Exception(f"Model execution failed: {str(e)}")

        async def _save_streaming_chunks_batch(self):
            """Batch save all collected streaming chunks to Azure Blob Storage"""
            try:
                if not self.streaming_chunks:
                    print("📦 No streaming chunks to save")
                    return

                project_id = getattr(self.model_system, 'project_id', None)
                if not project_id:
                    print("⚠️ No project_id available for saving streaming chunks")
                    return

                # Use dedicated streaming Azure client for highest priority
                cloud_storage = get_streaming_azure_client()

                # Save all chunks in one operation
                success = cloud_storage.save_conversation_history_streaming(project_id, self.streaming_chunks)

                if success:
                    print(f"✅ Batch saved {len(self.streaming_chunks)} streaming chunks to Azure")
                else:
                    print(f"❌ Failed to batch save {len(self.streaming_chunks)} streaming chunks")

            except Exception as e:
                print(f"⚠️ Error during batch save of streaming chunks: {e}")

        def _save_streaming_chunks_sync(self):
            """Synchronous version of streaming chunks save for background thread"""
            try:
                if not self.streaming_chunks:
                    return

                # Only save if we have new chunks since last save
                chunks_to_save = len(self.streaming_chunks)
                if chunks_to_save <= self.last_save_count:
                    return

                project_id = getattr(self.model_system, 'project_id', None)
                if not project_id:
                    return

                # Use dedicated streaming Azure client for highest priority
                cloud_storage = get_streaming_azure_client()

                # Save all chunks (including previously saved ones - overwrite approach)
                success = cloud_storage.save_conversation_history_streaming(project_id, self.streaming_chunks)

                if success:
                    new_chunks = chunks_to_save - self.last_save_count
                    print(f"💾 Saved {new_chunks} new streaming chunks ({chunks_to_save} total)")
                    self.last_save_count = chunks_to_save

            except Exception as e:
                print(f"⚠️ Background save error: {e}")

        def _get_file_tracking_summary(self):
            """Get file tracking summary for this streaming session"""
            return {
                "files_created": self.files_created.copy(),
                "files_updated": self.files_updated.copy(),
                "total_files_changed": len(self.files_created) + len(self.files_updated)
            }

    @app.get("/")
    async def root():
        """API health check"""
        pool_manager = get_pool_manager()
        pool_stats = pool_manager.get_pool_stats()

        return {
            "status": "healthy",
            "service": "Model Conversation API with Project Pool",
            "version": "1.0.0",
            "active_conversations": len(active_conversations),
            "project_pool": pool_stats
        }

    @app.get("/health")
    async def health_check():
        """Railway health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/pool/status")
    async def get_pool_status():
        """Get detailed project pool status"""
        pool_manager = get_pool_manager()
        return pool_manager.get_pool_status()

    @app.get("/conversations", response_model=List[ConversationInfo])
    async def list_conversations():
        """List all active conversations"""
        conversations = []
        for conv_id, metadata in conversation_metadata.items():
            conversations.append(ConversationInfo(
                conversation_id=conv_id,
                project_id=metadata.get("project_id"),
                created_at=metadata.get("created_at"),
                last_activity=metadata.get("last_activity"),
                message_count=metadata.get("message_count", 0),
                status=metadata.get("status", "active")
            ))
        return conversations

    @app.delete("/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: str):
        """Delete a conversation"""
        if conversation_id in active_conversations:
            del active_conversations[conversation_id]
        if conversation_id in conversation_metadata:
            del conversation_metadata[conversation_id]
        return {"status": "deleted", "conversation_id": conversation_id}

    async def process_request_with_images(request: ConversationRequest, conversation_id: str) -> tuple:
        """Process images and return (formatted_message, image_urls)"""
        if not request.images or len(request.images) == 0:
            # No images, return original message and empty list
            return request.message, []

        print(f"🖼️ Processing {len(request.images)} images for conversation {conversation_id}")

        # Upload images to Azure storage and get public URLs
        cloud_storage = get_cloud_storage()
        image_urls = []

        for i, base64_image in enumerate(request.images):
            try:
                public_url = cloud_storage.upload_image(base64_image, conversation_id)
                if public_url:
                    image_urls.append(public_url)
                    print(f"✅ Image {i+1} uploaded: {public_url[:50]}...")
                else:
                    print(f"❌ Failed to upload image {i+1}")
            except Exception as e:
                print(f"❌ Error uploading image {i+1}: {str(e)}")

        if not image_urls:
            # No images uploaded successfully, return original message
            return request.message, []

        # Create OpenAI format content array
        content_array = [{"type": "text", "text": request.message}]
        for url in image_urls:
            content_array.append({
                "type": "image_url", 
                "image_url": {"url": url}
            })

        print(f"📝 Created content array with {len(image_urls)} images")
        return content_array, image_urls

    @app.post("/chat/stream")
    async def stream_chat(request: ConversationRequest):
        """Main streaming chat endpoint"""

        try:
            start_time = datetime.now()
            print(f"📡 Received streaming request: {request.message[:50]}...")

            # Check if this is an action result continuation (frontend sending command result back)
            is_action_result = getattr(request, 'action_result', False)

            # Determine if this is create or update mode
            # If we have a project_id, it's update mode (regardless of conversation_id)
            is_update_mode = bool(request.project_id)
            conversation_id = request.conversation_id or generate_conversation_id()

            print(f"📡 Generated conversation_id: {conversation_id}")
            print(f"📡 Update mode: {is_update_mode}")
            print(f"📡 Action result continuation: {is_action_result}")

            # Initialize or get existing model system
            if conversation_id not in active_conversations:
                api_key = get_api_key()

                if is_update_mode:
                    # Update mode - use existing project
                    print(f"🔄 Initializing update mode for project: {request.project_id}")
                    model_system = BoilerplatePersistentGroq(
                        api_key=api_key,
                        project_id=request.project_id
                    )
                    mode = "update"
                else:
                    # Create mode - try to get a pre-warmed project from pool
                    print(f"🚀 Initializing create mode")
                    pool_manager = get_pool_manager()

                    # Try to get an available project from the pool (needs to be sync - we need the result)
                    pooled_project_id = pool_manager.get_available_project(conversation_id, request.message)

                    if pooled_project_id:
                        # Use pre-warmed project from pool
                        pool_allocation_time = datetime.now()
                        print(f"🎯 Using pre-warmed project from pool: {pooled_project_id}")
                        print(f"⚡ Pool allocation time: {(pool_allocation_time - start_time).total_seconds():.3f}s")

                        model_system = BoilerplatePersistentGroq(
                            api_key=api_key,
                            project_id=pooled_project_id  # Use pooled project directly
                        )

                        # Mark project as active in the pool (non-blocking fire-and-forget)
                        await pool_manager.mark_project_active_async(pooled_project_id)

                        initialization_time = datetime.now()
                        print(f"⚡ Total initialization time: {(initialization_time - start_time).total_seconds():.3f}s")
                        mode = "create_from_pool"
                    else:
                        # Fallback: create project normally (emergency case)
                        print(f"⚠️ No pooled projects available, creating emergency project")
                        from agent_class import generate_project_name

                        base_project_name = generate_project_name(request.message)
                        timestamp = datetime.now().strftime("%H%M%S")
                        project_name = f"emergency-{base_project_name}-{timestamp}"

                        model_system = BoilerplatePersistentGroq(api_key, project_name)
                        mode = "create_emergency"

                active_conversations[conversation_id] = model_system
                conversation_metadata[conversation_id] = {
                    "project_id": getattr(model_system, 'project_id', None),
                    "created_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat(),
                    "message_count": 0,
                    "status": "active",
                    "mode": mode
                }
            else:
                model_system = active_conversations[conversation_id]
                conversation_metadata[conversation_id]["last_activity"] = datetime.now().isoformat()

            # Update message count
            conversation_metadata[conversation_id]["message_count"] += 1

            # Process images if present BEFORE saving to history
            message_content, image_urls = await process_request_with_images(request, conversation_id)
            print(f"🐛 DEBUG: message_content type: {type(message_content)}, content: {message_content if isinstance(message_content, str) else 'ARRAY'}")

            # Save user message to streaming conversation history (avoid command results)
            user_message_chunk = None  # Initialize outside try block
            if not is_action_result:
                try:
                    from cloud_storage import AzureBlobStorage

                    # Use request.project_id if available (update mode), otherwise get from model_system
                    project_id = request.project_id or getattr(model_system, 'project_id', None)
                    
                    if project_id:
                        # Use the same content array from image processing
                        user_message_chunk = {
                            "type": "user_message",
                            "data": {
                                "content": message_content if isinstance(message_content, list) else [{"type": "text", "text": message_content}],
                                "message_type": "user"
                            },
                            "conversation_id": conversation_id,
                            "timestamp": datetime.now().isoformat(),
                            "action_id": None,
                            "is_command_result": False
                        }

                        cloud_storage = get_streaming_azure_client()
                        # Save user message chunk in background thread to avoid blocking
                        import threading
                        save_thread = threading.Thread(
                            target=lambda: cloud_storage.append_streaming_chunk(project_id, user_message_chunk),
                            daemon=True
                        )
                        save_thread.start()
                        print(f"💾 Background save of user message to streaming history initiated")

                except Exception as e:
                    print(f"⚠️ Failed to save user message to streaming history: {e}")
            else:
                # This is a command result - save with special marker
                try:
                    from cloud_storage import AzureBlobStorage

                    project_id = getattr(model_system, 'project_id', None)
                    if project_id:
                        # Command results are text only, but keep consistent format
                        content_array = [{"type": "text", "text": request.message}]
                        
                        command_result_chunk = {
                            "type": "user_message",
                            "data": {
                                "content": content_array,
                                "message_type": "user"
                            },
                            "conversation_id": conversation_id,
                            "timestamp": datetime.now().isoformat(),
                            "action_id": None,
                            "is_command_result": True
                        }

                        cloud_storage = get_streaming_azure_client()
                        # Save command result chunk in background thread to avoid blocking
                        import threading
                        save_thread = threading.Thread(
                            target=lambda: cloud_storage.append_streaming_chunk(project_id, command_result_chunk),
                            daemon=True
                        )
                        save_thread.start()
                        print(f"💾 Background save of command result to streaming history initiated")

                except Exception as e:
                    print(f"⚠️ Failed to save command result to streaming history: {e}")

            # Create streaming wrapper
            streaming_wrapper = StreamingModelWrapper(model_system, conversation_id)
            
            # Add user message chunk to wrapper's streaming chunks for update mode
            if user_message_chunk is not None:
                streaming_wrapper.streaming_chunks.append(user_message_chunk)
                print(f"📝 Added user message to streaming chunks (total: {len(streaming_wrapper.streaming_chunks)})")

            # Add timing context to wrapper
            streaming_wrapper.request_start_time = start_time

            # Return streaming response
            return StreamingResponse(
                streaming_wrapper.stream_response(message_content),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Conversation-ID": conversation_id,
                    "X-Request-Start-Time": start_time.isoformat(),
                    "Access-Control-Allow-Origin": "*",
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize conversation: {str(e)}")

    @app.get("/conversations/{conversation_id}/info")
    async def get_conversation_info(conversation_id: str):
        """Get detailed information about a conversation"""
        if conversation_id not in conversation_metadata:
            raise HTTPException(status_code=404, detail="Conversation not found")

        metadata = conversation_metadata[conversation_id]
        model_system = active_conversations.get(conversation_id)

        return {
            "conversation_id": conversation_id,
            "metadata": metadata,
            "project_id": getattr(model_system, 'project_id', None) if model_system else None,
            "has_active_system": conversation_id in active_conversations
        }

    @app.get("/conversations/{conversation_id}/history")
    async def get_conversation_history(conversation_id: str):
        """Get the full conversation history for a specific conversation from Azure Blob Storage"""
        if conversation_id not in active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")

        model_system = active_conversations[conversation_id]
        project_id = getattr(model_system, 'project_id', None)

        if not project_id:
            raise HTTPException(status_code=404, detail="Project ID not found for conversation")

        # Load conversation history from Azure Blob Storage
        try:
            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()

            # Load conversation history using cloud storage method
            conversation_history = cloud_storage.load_conversation_history(project_id)

            return {
                "conversation_id": conversation_id,
                "project_id": project_id,
                "message_count": len(conversation_history),
                "messages": conversation_history
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load conversation history: {str(e)}")

    @app.get("/projects/{project_id}/history")
    async def get_project_conversation_history(project_id: str):
        """Get conversation history directly by project ID from Azure Blob Storage"""
        try:
            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()

            # Load conversation history using cloud storage method
            conversation_history = cloud_storage.load_conversation_history(project_id)

            return {
                "project_id": project_id,
                "message_count": len(conversation_history),
                "messages": conversation_history,
                "source": "azure_blob_storage"
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load conversation history: {str(e)}")

    @app.get("/projects/{project_id}/history/streaming-format")
    async def get_project_conversation_history_streaming_format(project_id: str):
        """Get conversation history in EXACT streaming format that frontend expects - from saved streaming data"""
        try:
            from cloud_storage import AzureBlobStorage

            cloud_storage = AzureBlobStorage()

            # First try to load from saved streaming conversation history
            streaming_chunks = cloud_storage.load_conversation_history_streaming(project_id)

            if streaming_chunks:
                # Return saved streaming data
                fake_conversation_id = f"conv_history_{project_id}"

                return {
                    "project_id": project_id,
                    "conversation_id": fake_conversation_id,
                    "message_count": "calculated_from_streaming",
                    "streaming_chunks_count": len(streaming_chunks),
                    "streaming_chunks": streaming_chunks,
                    "source": "azure_blob_storage_streaming",
                    "format": "live_streaming_format"
                }

            else:
                # Fallback: convert from raw conversation history if no streaming data exists
                from conversation_history_converter import ConversationHistoryConverter

                print(f"⚠️ No streaming data found for {project_id}, converting from raw conversation history")
                conversation_history = cloud_storage.load_conversation_history(project_id)

                if conversation_history:
                    converter = ConversationHistoryConverter()
                    result = converter.convert_to_streaming_format(conversation_history, project_id)
                    result["source"] = "azure_blob_storage_converted"
                    result["format"] = "converted_from_raw"
                    return result
                else:
                    return {
                        "project_id": project_id,
                        "conversation_id": f"conv_history_{project_id}",
                        "message_count": 0,
                        "streaming_chunks_count": 0,
                        "streaming_chunks": [],
                        "source": "empty",
                        "format": "no_data_found"
                    }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load conversation history in streaming format: {str(e)}")

    # ===== WEBCONTAINER INTEGRATION ENDPOINTS =====

    @app.post("/projects/create")
    async def create_project_for_webcontainer(request: dict):
        """Create a new project for webcontainer using the same flow as streaming chat"""
        try:
            from agent_class import BoilerplatePersistentGroq, generate_project_name

            # Get initial message to generate project name, default to generic name
            initial_message = request.get('initial_message', 'New WebContainer Project')

            print(f"🚀 Creating new project for webcontainer: {initial_message[:50]}")

            # Generate project name using same logic as streaming API
            base_project_name = generate_project_name(initial_message)
            timestamp = datetime.now().strftime("%H%M%S")
            project_name = f"{base_project_name}-{timestamp}"

            # Initialize model system - this calls create_project_via_cloud_storage
            api_key = get_api_key()
            model_system = BoilerplatePersistentGroq(api_key, project_name)
            project_id = model_system.project_id

            print(f"✅ Project created via cloud storage: {project_id}")

            # Get frontend files for webcontainer mounting
            cloud_storage = model_system.cloud_storage
            all_files = cloud_storage.list_files(project_id)

            # Filter frontend files for WebContainer (only exclude cache/temp files)
            frontend_files = []
            exclude_patterns = [
                # Project metadata (not needed in WebContainer)
                'conversation_history.json',
                'project_metadata.json',
                'read_files_tracking.json',

                # Backend files (frontend-only mount)
                'backend/',

                # Cache and temporary files
                'node_modules/',
                '.git/',
                '.vscode/',
                '.idea/',
                'dist/',
                'build/',
                '.next/',
                'coverage/',

                # Lock files (WebContainer will regenerate)
                'package-lock.json',
                'yarn.lock',
                'pnpm-lock.yaml',
            ]

            for file_path in all_files:
                if not file_path or file_path.startswith('backend/'):
                    continue
                should_exclude = any(pattern in file_path for pattern in exclude_patterns)
                if should_exclude:
                    continue

                # Remove 'frontend/' prefix for WebContainer mounting at root level
                if file_path.startswith('frontend/'):
                    clean_path = file_path[9:]  # Remove 'frontend/' prefix
                    if clean_path:  # Only add if there's content after removing prefix
                        frontend_files.append(clean_path)
                else:
                    frontend_files.append(file_path)

            # Convert to WebContainer format
            webcontainer_files = await convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)

            print(f"✅ Project ready for WebContainer: {project_id} with {len(frontend_files)} frontend files")

            return {
                "project_id": project_id,
                "project_name": project_name,
                "files": webcontainer_files,
                "message": f"Project created and ready: {project_name}"
            }

        except Exception as e:
            print(f"❌ Error creating project: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

    @app.get("/projects/list")
    async def list_projects():
        """Get list of all projects from project pool (fast!)"""
        try:
            # Get projects from the project pool manager instead of scanning Azure
            pool_manager = get_pool_manager()
            pool_status = pool_manager.get_pool_status()

            # Extract project list from pool status
            project_list = []
            if 'projects' in pool_status:
                for project_data in pool_status['projects']:
                    project_id = project_data.get('id', project_data.get('name', 'unknown'))
                    project_list.append({
                        "id": project_id,
                        "name": project_id.replace('-', ' ').title(),
                        "description": f"Project: {project_id}",
                        "created_at": project_data.get("created_at"),
                        "status": project_data.get("status", "unknown"),
                        "file_count": project_data.get("file_count", "N/A")
                    })

            # Sort by creation date
            project_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            print(f"📋 Retrieved {len(project_list)} projects from pool (fast!)")
            return {"projects": project_list}

        except Exception as e:
            print(f"❌ Error listing projects: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

    @app.get("/projects/{project_id}/frontend-files")
    async def get_frontend_files(project_id: str):
        """Get frontend files from cloud project for WebContainer mounting"""
        try:
            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()

            # Get all files for this project
            all_files = cloud_storage.list_files(project_id)

            # Filter frontend files for WebContainer (only exclude cache/temp files)
            frontend_files = []

            # Exclude patterns that WebContainer doesn't need
            exclude_patterns = [
                # Project metadata (not needed in WebContainer)
                'conversation_history.json',
                'project_metadata.json',
                'read_files_tracking.json',

                # Backend files (frontend-only mount)
                'backend/',

                # Cache and temporary files
                'node_modules/',
                '.git/',
                '.vscode/',
                '.idea/',
                'dist/',
                'build/',
                '.next/',
                'coverage/',

                # Lock files (WebContainer will regenerate)
                'package-lock.json',
                'yarn.lock',
                'pnpm-lock.yaml',
            ]

            for file_path in all_files:
                if not file_path or file_path.startswith('backend/'):
                    continue

                # Always include .env files from frontend folder
                is_env_file = file_path.endswith('.env') or file_path.endswith('/.env')

                # Skip excluded patterns except .env files
                should_exclude = any(pattern in file_path for pattern in exclude_patterns) and not is_env_file
                if should_exclude:
                    continue

                # Remove 'frontend/' prefix for WebContainer mounting at root level
                if file_path.startswith('frontend/'):
                    clean_path = file_path[9:]  # Remove 'frontend/' prefix
                    if clean_path:  # Only add if there's content after removing prefix
                        frontend_files.append(clean_path)
                else:
                    frontend_files.append(file_path)

            print(f"📁 Found {len(frontend_files)} frontend files for project {project_id}")

            # Convert to WebContainer mount format
            webcontainer_files = await convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)

            return {"files": webcontainer_files, "project_id": project_id}

        except Exception as e:
            print(f"❌ Error getting frontend files for {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get frontend files: {str(e)}")

    @app.put("/projects/{project_id}/files/update", response_model=FileUpdateResponse)
    async def update_file_content(project_id: str, request: FileUpdateRequest):
        """Update a specific file's content in Azure Blob Storage"""
        try:
            print(f"📝 Updating file {request.file_path} in project {project_id}")

            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()

            # Upload the updated file content to Azure Blob Storage
            success = cloud_storage.upload_file(project_id, request.file_path, request.content)

            if success:
                print(f"✅ Successfully updated file: {request.file_path}")

                # Update project metadata to track the file modification
                try:
                    existing_metadata = cloud_storage.load_project_metadata(project_id) or {}

                    # Track file updates in metadata
                    file_updates = existing_metadata.get("file_updates", {})
                    file_updates[request.file_path] = {
                        "updated_at": datetime.now().isoformat(),
                        "content_length": len(request.content),
                        "update_method": "api_direct"
                    }
                    existing_metadata["file_updates"] = file_updates
                    existing_metadata["last_file_update"] = datetime.now().isoformat()

                    # Save updated metadata
                    cloud_storage.save_project_metadata(project_id, existing_metadata)
                    print(f"✅ Updated project metadata with file modification tracking")

                except Exception as e:
                    print(f"⚠️ Failed to update project metadata: {e}")

                return FileUpdateResponse(
                    status="success",
                    project_id=project_id,
                    file_path=request.file_path,
                    message=f"File {request.file_path} updated successfully"
                )
            else:
                print(f"❌ Failed to update file: {request.file_path}")
                return FileUpdateResponse(
                    status="error",
                    project_id=project_id,
                    file_path=request.file_path,
                    message="Failed to update file",
                    error="Azure Blob Storage upload failed"
                )

        except Exception as e:
            print(f"❌ Error updating file {request.file_path}: {e}")
            return FileUpdateResponse(
                status="error",
                project_id=project_id,
                file_path=request.file_path,
                message="File update failed",
                error=str(e)
            )

    @app.post("/projects/{project_id}/files/bulk", response_model=BulkFileResponse)
    async def get_bulk_file_contents(project_id: str, request: BulkFileRequest):
        """Get contents of multiple files from a project"""
        try:
            print(f"📁 Bulk file request for project {project_id}: {len(request.file_paths)} files")

            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()

            # Validate project_id matches request
            if project_id != request.project_id:
                raise HTTPException(status_code=400, detail="Project ID mismatch between URL and request body")

            files_result = []
            successful_count = 0
            failed_count = 0

            # Always include frontend's .env file
            file_paths_to_retrieve = list(request.file_paths)
            if "frontend/.env" not in file_paths_to_retrieve:
                file_paths_to_retrieve.append("frontend/.env")
                print(f"📧 Added frontend/.env to bulk request")

            for file_path in file_paths_to_retrieve:
                try:
                    # Download file content from cloud storage
                    content = cloud_storage.download_file(project_id, file_path)

                    if content is not None:
                        files_result.append(FileContent(
                            file_path=file_path,
                            content=content,
                            exists=True,
                            success=True,
                            error=None
                        ))
                        successful_count += 1
                        print(f"✅ Retrieved: {file_path}")
                    else:
                        files_result.append(FileContent(
                            file_path=file_path,
                            content=None,
                            exists=False,
                            success=False,
                            error="File not found"
                        ))
                        failed_count += 1
                        print(f"❌ Not found: {file_path}")

                except Exception as e:
                    files_result.append(FileContent(
                        file_path=file_path,
                        content=None,
                        exists=False,
                        success=False,
                        error=str(e)
                    ))
                    failed_count += 1
                    print(f"❌ Error retrieving {file_path}: {e}")

            status = "success" if failed_count == 0 else "partial" if successful_count > 0 else "error"

            print(f"📊 Bulk file retrieval complete: {successful_count} success, {failed_count} failed")

            return BulkFileResponse(
                status=status,
                project_id=project_id,
                files=files_result,
                total_files=len(file_paths_to_retrieve),
                successful_files=successful_count,
                failed_files=failed_count
            )

        except Exception as e:
            print(f"❌ Error in bulk file retrieval for {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")

    async def convert_to_webcontainer_format(project_id: str, files_list: list, cloud_storage) -> dict:
        """Convert cloud files to WebContainer mount format (async with thread pool)"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        try:
            webcontainer_files = {}

            # Download files using thread pool to avoid blocking the event loop
            def download_single_file(file_path):
                try:
                    # For downloading, we need the original path with frontend/ prefix
                    original_path = f"frontend/{file_path}" if not file_path.startswith('frontend/') else file_path

                    # Download file content from cloud using original path
                    content = cloud_storage.download_file(project_id, original_path)
                    if content is None:
                        print(f"⚠️ Could not download content for {original_path}")
                        return None
                    return (file_path, content)
                except Exception as e:
                    print(f"❌ Error downloading {file_path}: {e}")
                    return None

            # Use ThreadPoolExecutor to run downloads in parallel without blocking
            with ThreadPoolExecutor(max_workers=5) as executor:
                loop = asyncio.get_event_loop()
                download_tasks = [
                    loop.run_in_executor(executor, download_single_file, file_path)
                    for file_path in files_list
                ]

                # Wait for all downloads to complete
                download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

            # Process all results
            for result in download_results:
                if result is None or isinstance(result, Exception):
                    continue

                file_path, content = result

                # Build nested structure for WebContainer
                path_parts = file_path.split('/')
                current_level = webcontainer_files

                # Navigate/create directory structure
                for i, part in enumerate(path_parts):
                    if i == len(path_parts) - 1:
                        # This is the file
                        current_level[part] = {
                            'file': {
                                'contents': content
                            }
                        }
                    else:
                        # This is a directory
                        if part not in current_level:
                            current_level[part] = {'directory': {}}
                        current_level = current_level[part]['directory']

            print(f"✅ Converted {len(files_list)} files to WebContainer format")
            return webcontainer_files

        except Exception as e:
            print(f"❌ Error converting files to WebContainer format: {e}")
            return {}

    @app.post("/modal/secrets/create", response_model=ModalSecretsResponse)
    async def create_modal_secrets(request: ModalSecretsRequest):
        """Create or update Modal.com secrets programmatically"""
        try:
            import subprocess
            import tempfile

            print(f"🔐 Creating Modal secrets: {request.secret_name}")

            # Build modal secret create command
            cmd = ["modal", "secret", "create", request.secret_name]

            # Add overwrite flag if needed
            if request.overwrite:
                # Delete existing secret first (ignore errors) - async
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "modal", "secret", "delete", request.secret_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()  # Don't care about result for deletion
                except:
                    pass

            # Add all key=value pairs
            for key, value in request.secrets.items():
                cmd.append(f"{key}={value}")

            # Execute modal command (async to avoid blocking other requests)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()
            stdout = stdout.decode('utf-8') if stdout else ""
            stderr = stderr.decode('utf-8') if stderr else ""

            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd, stderr)

            # Create result object to match original subprocess.run interface
            result = type('Result', (), {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': proc.returncode
            })()

            print(f"✅ Modal secrets created: {request.secret_name}")

            return ModalSecretsResponse(
                status="success",
                secret_name=request.secret_name,
                secret_count=len(request.secrets) if isinstance(request.secrets, (dict, list)) else 0
            )

        except subprocess.CalledProcessError as e:
            error_msg = f"Modal secrets creation failed: {e.stderr}"
            print(f"❌ {error_msg}")
            return ModalSecretsResponse(
                status="error",
                secret_name=request.secret_name,
                secret_count=0,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Secrets creation error: {str(e)}"
            print(f"❌ {error_msg}")
            return ModalSecretsResponse(
                status="error",
                secret_name=request.secret_name,
                secret_count=0,
                error=error_msg
            )

    async def _deploy_backend_background(deployment_id: str, request: ModalDeploymentRequest):
        """Background task for Modal deployment to avoid blocking the server"""
        try:
            deployment_status[deployment_id] = {
                "status": "deploying",
                "progress": "Initializing deployment...",
                "started_at": datetime.now().isoformat()
            }

            # Execute the actual deployment logic in background
            result = await _execute_modal_deployment(request)

            # Update status with result
            deployment_status[deployment_id] = {
                "status": result.status,
                "progress": "Deployment completed",
                "result": result.dict(),
                "completed_at": datetime.now().isoformat()
            }

        except Exception as e:
            deployment_status[deployment_id] = {
                "status": "error",
                "progress": f"Deployment failed: {str(e)}",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }

    @app.post("/modal/deploy")
    async def deploy_backend_to_modal(request: ModalDeploymentRequest):
        """Deploy Modal backend synchronously (blocking but reliable)"""
        try:
            print(f"🚀 Starting SYNCHRONOUS Modal deployment for: {request.app_name}")

            # Call the actual deployment function directly (no background task)
            result = await _execute_modal_deployment(request)

            print(f"✅ Synchronous deployment completed: {result.status}")

            if result.status == "success":
                return {
                    "status": "success",
                    "app_name": result.app_name,
                    "url": result.url,
                    "docs_url": result.docs_url,
                    "logs_command": result.logs_command,
                    "message": "Deployment completed successfully",
                    "stdout": result.stdout,  # Pass STDOUT to LLM
                    "stderr": result.stderr   # Pass STDERR to LLM
                }
            else:
                return {
                    "status": "error",
                    "app_name": result.app_name,
                    "error": result.error,
                    "message": "Deployment failed",
                    "stdout": result.stdout,  # Pass STDOUT to LLM
                    "stderr": result.stderr   # Pass STDERR to LLM
                }

        except Exception as e:
            print(f"❌ Synchronous deployment failed: {e}")
            return {
                "status": "error",
                "app_name": request.app_name,
                "error": str(e),
                "message": "Deployment failed with exception",
                "stdout": "",  # No STDOUT available in this case
                "stderr": str(e)  # Exception as STDERR
            }

    @app.get("/modal/deploy/status/{deployment_id}")
    async def get_deployment_status(deployment_id: str):
        """Get deployment status for background deployment"""
        if deployment_id not in deployment_status:
            return {
                "status": "not_found",
                "error": "Deployment ID not found",
                "deployment_id": deployment_id
            }

        return {
            "deployment_id": deployment_id,
            **deployment_status[deployment_id]
        }

    @app.post("/netlify/deploy", response_model=NetlifyDeploymentResponse)
    async def deploy_frontend_to_netlify_api(request: NetlifyDeploymentRequest):
        """Deploy frontend to Netlify"""
        try:
            print(f"🚀 Starting Netlify deployment for project: {request.project_id}")
            
            # Call the deployment function with project_name parameter
            project_name = getattr(request, 'project_name', None) or f"app-{request.project_id.replace('_', '-').lower()}"
            result = deploy_frontend_to_netlify(request.project_id, project_name)
            
            if result["status"] == "success":
                print(f"✅ Netlify deployment completed successfully")
                
                return NetlifyDeploymentResponse(
                    status="success",
                    project_id=request.project_id,
                    netlify_url=result.get("deployment_url"),
                    site_name=result.get("project_name"),
                    backend_url=None,  # Not provided by new API
                    env_vars=None,     # Not provided by new API
                    deployed_at=None   # Not provided by new API
                )
            else:
                # Handle error from deployment function
                error_msg = result.get("message", "Deployment failed")
                print(f"❌ {error_msg}")
                
                return NetlifyDeploymentResponse(
                    status="error",
                    project_id=request.project_id,
                    error=error_msg
                )
            
        except Exception as e:
            error_msg = f"Netlify deployment failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return NetlifyDeploymentResponse(
                status="error",
                project_id=request.project_id,
                error=error_msg
            )

    @app.post("/cloudflare/deploy", response_model=CloudflareDeploymentResponse)
    async def deploy_frontend_to_cloudflare_api(request: CloudflareDeploymentRequest):
        """Deploy frontend to Cloudflare Pages"""
        try:
            print(f"🚀 Starting Cloudflare Pages deployment for project: {request.project_id}")
            
            # Call the deployment function
            result = deploy_frontend_to_cloudflare(
                project_id=request.project_id,
                project_name=request.project_name,
                environment=request.environment,
                custom_env_vars=request.env_vars
            )
            
            if result.get("status") == "success":
                print(f"✅ Cloudflare Pages deployment completed successfully")
                
                return CloudflareDeploymentResponse(
                    status="success",
                    project_id=request.project_id,
                    deployment_url=result.get("deployment_url"),
                    preview_url=result.get("preview_url"),
                    project_name=result.get("project_name"),
                    environment=result.get("environment"),
                    logs=result.get("logs", [])
                )
            else:
                print(f"❌ Cloudflare Pages deployment failed: {result.get('message')}")
                
                return CloudflareDeploymentResponse(
                    status="error",
                    project_id=request.project_id,
                    error_type=result.get("error_type"),
                    message=result.get("message"),
                    suggestions=result.get("suggestions", []),
                    logs=result.get("logs", [])
                )
            
        except Exception as e:
            error_msg = f"Cloudflare Pages deployment failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return CloudflareDeploymentResponse(
                status="error",
                project_id=request.project_id,
                message=error_msg,
                error_type="unexpected_error"
            )

    @app.get("/modal/apps")
    async def list_modal_apps():
        """List deployed Modal.com apps"""
        try:
            import subprocess

            # Async subprocess to avoid blocking other requests
            proc = await asyncio.create_subprocess_exec(
                "modal", "app", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                stdout = stdout.decode('utf-8') if stdout else ""
                stderr = stderr.decode('utf-8') if stderr else ""

                if proc.returncode != 0:
                    raise subprocess.CalledProcessError(proc.returncode, ["modal", "app", "list"], stderr)

                # Create result object to match original subprocess.run interface
                result = type('Result', (), {
                    'stdout': stdout,
                    'stderr': stderr,
                    'returncode': proc.returncode
                })()

            except asyncio.TimeoutError:
                proc.kill()
                raise subprocess.TimeoutExpired(["modal", "app", "list"], 30)

            # Parse the output to extract app names and status
            apps = []
            lines = result.stdout.split('\n')

            for line in lines:
                if line.strip() and not line.startswith('App Name'):
                    parts = line.split()
                    if len(parts) >= 2:
                        apps.append({
                            "name": parts[0],
                            "status": parts[1] if len(parts) > 1 else "unknown"
                        })

            return {
                "status": "success",
                "apps": apps,
                "total_apps": len(apps)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "apps": []
            }

    @app.delete("/modal/apps/{app_name}")
    async def delete_modal_app(app_name: str):
        """Delete a Modal.com app"""
        try:
            import subprocess

            # Async subprocess to avoid blocking other requests
            proc = await asyncio.create_subprocess_exec(
                "modal", "app", "stop", app_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                stdout = stdout.decode('utf-8') if stdout else ""
                stderr = stderr.decode('utf-8') if stderr else ""

                if proc.returncode != 0:
                    raise subprocess.CalledProcessError(proc.returncode, ["modal", "app", "stop", app_name], stderr)

            except asyncio.TimeoutError:
                proc.kill()
                raise subprocess.TimeoutExpired(["modal", "app", "stop", app_name], 30)

            return {
                "status": "success",
                "app_name": app_name,
                "message": "App stopped successfully"
            }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "app_name": app_name,
                "error": f"Failed to stop app: {e.stderr}"
            }
        except Exception as e:
            return {
                "status": "error",
                "app_name": app_name,
                "error": str(e)
            }

    # Global cache for backend info to prevent stream interference
    _backend_info_cache = {}
    _cache_timeout = 25  # 25 seconds cache (less than 30s frontend polling)

    async def run_with_streaming_priority(coro, operation_name="streaming_op"):
        """Run coroutine with high priority for streaming operations"""
        task = asyncio.create_task(coro, name=f"HIGH_PRIORITY_{operation_name}")
        return await task

    # Backend info endpoint with health check
    @app.get("/projects/{project_id}/backend/info")
    async def get_project_backend_info(project_id: str):
            """Get project backend deployment info and health status - CACHED to protect streaming"""
            try:
                from cloud_storage import get_cloud_storage
                from datetime import datetime
                import asyncio
                import aiohttp

                # Check cache first to avoid Azure storage contention with streaming
                now = datetime.now()
                cache_key = f"backend_info_{project_id}"

                if cache_key in _backend_info_cache:
                    cached_data, cached_time = _backend_info_cache[cache_key]
                    age_seconds = (now - cached_time).total_seconds()

                    if age_seconds < _cache_timeout:
                        print(f"📋 Backend info CACHE HIT for {project_id} (age: {age_seconds:.1f}s)")
                        return cached_data
                    else:
                        print(f"📋 Backend info cache expired for {project_id} (age: {age_seconds:.1f}s)")

                # Use dedicated general Azure client (separate from streaming)
                cloud_storage = get_general_azure_client()

                # Load project metadata (async, non-blocking)
                metadata = await asyncio.to_thread(cloud_storage.load_project_metadata, project_id)
                if not metadata:
                    return {
                        "status": "error",
                        "error": "Project metadata not found",
                        "project_id": project_id
                    }

                backend_deployment = metadata.get("backend_deployment")
                if not backend_deployment:
                    return {
                        "status": "not_deployed",
                        "message": "Backend not deployed yet",
                        "project_id": project_id,
                        "metadata": metadata
                    }

                # Get backend URL for health check
                backend_url = backend_deployment.get("url")
                health_status = None
                health_error = None

                if backend_url:
                    try:
                        # Perform health check with SHORT timeout to avoid interfering with streaming
                        timeout = aiohttp.ClientTimeout(total=3)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(f"{backend_url}/health") as response:
                                if response.status == 200:
                                    health_data = await response.json()
                                    health_status = "healthy"
                                    health_data["response_time_ms"] = response.headers.get("X-Response-Time", "N/A")
                                    health_data["status_code"] = response.status
                                else:
                                    health_status = "unhealthy"
                                    health_error = f"HTTP {response.status}"
                                    health_data = {"status_code": response.status}

                    except asyncio.TimeoutError:
                        health_status = "timeout"
                        health_error = "Health check timeout (10s)"
                        health_data = {}
                    except Exception as e:
                        health_status = "error"
                        health_error = str(e)
                        health_data = {}
                else:
                    health_status = "no_url"
                    health_error = "No backend URL found"
                    health_data = {}

                result = {
                    "status": "success",
                    "project_id": project_id,
                    "backend_deployment": backend_deployment,
                    "health_check": {
                        "status": health_status,
                        "error": health_error,
                        "data": health_data,
                        "checked_at": datetime.now().isoformat()
                    },
                    "frontend_env_updated": metadata.get("frontend_env_updated", False)
                }

                # Cache the result to prevent future Azure storage contention with streaming
                _backend_info_cache[cache_key] = (result, now)
                print(f"📋 Backend info cached for {project_id} (expires in {_cache_timeout}s)")

                return result

            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "project_id": project_id
                }

    # Global cache for database inspection to prevent stream interference
    _database_inspection_cache = {}
    _db_cache_timeout = 10  # 10 seconds cache for database inspection

    @app.get("/projects/{project_id}/backend/database/inspect")
    async def inspect_deployed_backend_database(project_id: str):
        """
        Call the deployed backend's /_internal/db/inspect endpoint to get database contents
        CACHED to prevent interference with streaming operations
        """
        try:
            from datetime import datetime
            import aiohttp
            import asyncio

            # Check cache first to avoid Azure storage contention with streaming
            now = datetime.now()
            cache_key = f"db_inspect_{project_id}"

            if cache_key in _database_inspection_cache:
                cached_data, cached_time = _database_inspection_cache[cache_key]
                age_seconds = (now - cached_time).total_seconds()

                if age_seconds < _db_cache_timeout:
                    print(f"🔍 Database inspection CACHE HIT for {project_id} (age: {age_seconds:.1f}s)")
                    return cached_data
                else:
                    print(f"🔍 Database inspection cache expired for {project_id} (age: {age_seconds:.1f}s)")

            # Use dedicated general Azure client (separate from streaming)
            cloud_storage = get_general_azure_client()

            # Load project metadata
            metadata = cloud_storage.load_project_metadata(project_id)
            if not metadata:
                return {
                    "status": "error",
                    "error": "Project metadata not found",
                    "project_id": project_id
                }

            backend_deployment = metadata.get("backend_deployment")
            if not backend_deployment:
                return {
                    "status": "not_deployed",
                    "message": "Backend not deployed yet - cannot inspect database",
                    "project_id": project_id,
                    "suggestion": "Deploy the backend first using the deploy API endpoint"
                }

            # Get backend URL for database inspection
            backend_url = backend_deployment.get("url")
            if not backend_url:
                return {
                    "status": "error",
                    "error": "Backend URL not found in deployment metadata",
                    "project_id": project_id,
                    "suggestion": "Redeploy the backend to regenerate the URL"
                }

            # Call the deployed backend's internal database inspection endpoint
            call_start_time = datetime.now()
            database_inspection_data = None
            call_error = None
            call_status = None

            try:
                # Use short timeout to avoid interfering with streaming operations
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    inspect_url = f"{backend_url}/_internal/db/inspect"
                    print(f"🔍 Calling database inspection: {inspect_url}")

                    async with session.get(inspect_url) as response:
                        call_duration = (datetime.now() - call_start_time).total_seconds() * 1000

                        if response.status == 200:
                            database_inspection_data = await response.json()
                            call_status = "success"
                            print(f"✅ Database inspection successful ({call_duration:.1f}ms)")

                            # Add response metadata
                            if isinstance(database_inspection_data, dict):
                                database_inspection_data["_call_metadata"] = {
                                    "called_from": "streaming_api",
                                    "response_time_ms": round(call_duration, 1),
                                    "called_at": call_start_time.isoformat(),
                                    "backend_url": backend_url
                                }

                        else:
                            call_status = "error"
                            try:
                                error_response = await response.json()
                                call_error = f"Backend returned HTTP {response.status}: {error_response.get('error', 'Unknown error')}"
                            except:
                                call_error = f"Backend returned HTTP {response.status}"
                            print(f"❌ Database inspection failed: {call_error} ({call_duration:.1f}ms)")

            except asyncio.TimeoutError:
                call_duration = (datetime.now() - call_start_time).total_seconds() * 1000
                call_status = "timeout"
                call_error = f"Database inspection timeout after 5 seconds"
                print(f"⏰ Database inspection timeout ({call_duration:.1f}ms)")
            except Exception as e:
                call_duration = (datetime.now() - call_start_time).total_seconds() * 1000
                call_status = "error"
                call_error = f"Connection error: {str(e)}"
                print(f"❌ Database inspection connection error: {e} ({call_duration:.1f}ms)")

            # Prepare result
            result = {
                "status": call_status,
                "project_id": project_id,
                "backend_url": backend_url,
                "backend_deployment": {
                    "app_name": backend_deployment.get("app_name"),
                    "deployed_at": backend_deployment.get("deployed_at"),
                    "status": backend_deployment.get("status")
                },
                "call_info": {
                    "response_time_ms": round(call_duration, 1) if 'call_duration' in locals() else None,
                    "called_at": call_start_time.isoformat(),
                    "inspect_endpoint": f"{backend_url}/_internal/db/inspect"
                }
            }

            if call_status == "success" and database_inspection_data:
                result["database_inspection"] = database_inspection_data
                result["message"] = "Database inspection successful"
            else:
                result["error"] = call_error
                if call_status == "timeout":
                    result["suggestion"] = "Backend may be slow or unresponsive. Try redeploying the backend."
                elif call_status == "error":
                    result["suggestion"] = "Backend may be down or unreachable. Check backend deployment status and redeploy if needed."

            # Cache the result to prevent future calls from interfering with streaming
            _database_inspection_cache[cache_key] = (result, now)
            print(f"🔍 Database inspection cached for {project_id} (expires in {_db_cache_timeout}s)")

            return result

        except Exception as e:
            print(f"❌ Database inspection API error for {project_id}: {e}")
            return {
                "status": "error",
                "error": f"Database inspection failed: {str(e)}",
                "project_id": project_id,
                "suggestion": "Check backend deployment status and try again"
            }

    @app.get("/projects/{project_id}/backend/database/tables/{table_name}")
    async def get_deployed_backend_table(project_id: str, table_name: str):
        """
        Get specific table data from deployed backend in structured format
        """
        try:
            from datetime import datetime
            import aiohttp
            import asyncio

            # Check cache first
            now = datetime.now()
            cache_key = f"table_view_{project_id}_{table_name}"

            if cache_key in _database_inspection_cache:
                cached_data, cached_time = _database_inspection_cache[cache_key]
                age_seconds = (now - cached_time).total_seconds()

                if age_seconds < _db_cache_timeout:
                    print(f"📋 Table view CACHE HIT for {project_id}/{table_name} (age: {age_seconds:.1f}s)")
                    return cached_data

            # Use dedicated general Azure client
            cloud_storage = get_general_azure_client()

            # Load project metadata
            metadata = cloud_storage.load_project_metadata(project_id)
            if not metadata:
                return {
                    "status": "error",
                    "error": "Project metadata not found",
                    "project_id": project_id
                }

            backend_deployment = metadata.get("backend_deployment")
            if not backend_deployment:
                return {
                    "status": "not_deployed",
                    "message": "Backend not deployed yet - cannot view table",
                    "project_id": project_id,
                    "table_name": table_name
                }

            backend_url = backend_deployment.get("url")
            if not backend_url:
                return {
                    "status": "error",
                    "error": "Backend URL not found in deployment metadata",
                    "project_id": project_id,
                    "table_name": table_name
                }

            # Call the deployed backend's table management endpoint for GET operation
            call_start_time = datetime.now()

            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    manage_url = f"{backend_url}/_internal/db/tables/{table_name}/manage"
                    request_payload = {"operation": "get"}

                    print(f"📋 Getting table data: {manage_url}")

                    async with session.post(manage_url, json=request_payload) as response:
                        call_duration = (datetime.now() - call_start_time).total_seconds() * 1000

                        if response.status == 200:
                            table_response = await response.json()

                            if table_response.get("status") == "success":
                                table_data = table_response.get("data", [])

                                # Extract column information from the data
                                columns = []
                                if table_data:
                                    # Get all unique column names from all records
                                    all_columns = set()
                                    for record in table_data:
                                        if isinstance(record, dict):
                                            all_columns.update(record.keys())
                                    columns = sorted(list(all_columns))

                                result = {
                                    "status": "success",
                                    "project_id": project_id,
                                    "table_name": table_name,
                                    "columns": columns,
                                    "rows": table_data,
                                    "metadata": {
                                        "row_count": len(table_data),
                                        "column_count": len(columns),
                                        "primary_key": "id" if "id" in columns else None
                                    },
                                    "call_info": {
                                        "response_time_ms": round(call_duration, 1),
                                        "backend_url": backend_url
                                    }
                                }

                                # Cache the result
                                _database_inspection_cache[cache_key] = (result, now)
                                print(f"📋 Table view cached for {project_id}/{table_name}")

                                return result
                            else:
                                return {
                                    "status": "error",
                                    "error": table_response.get("error", "Unknown error from backend"),
                                    "project_id": project_id,
                                    "table_name": table_name
                                }
                        else:
                            return {
                                "status": "error",
                                "error": f"Backend returned HTTP {response.status}",
                                "project_id": project_id,
                                "table_name": table_name
                            }

            except asyncio.TimeoutError:
                return {
                    "status": "timeout",
                    "error": "Table view request timed out",
                    "project_id": project_id,
                    "table_name": table_name
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Connection error: {str(e)}",
                    "project_id": project_id,
                    "table_name": table_name
                }

        except Exception as e:
            print(f"❌ Table view API error for {project_id}/{table_name}: {e}")
            return {
                "status": "error",
                "error": f"Table view failed: {str(e)}",
                "project_id": project_id,
                "table_name": table_name
            }

    # Pydantic models for table operations
    class TableOperationRequest(BaseModel):
        operation: str  # "insert", "update", "delete"
        data: Dict[str, Any] = None  # Record data for insert/update
        row_id: Optional[int] = None  # Required for update/delete

    @app.post("/projects/{project_id}/backend/database/tables/{table_name}/manage")
    async def manage_deployed_backend_table(project_id: str, table_name: str, request: TableOperationRequest):
        """
        Unified table operations endpoint for deployed backend (insert/update/delete)
        """
        try:
            from datetime import datetime
            import aiohttp
            import asyncio

            # Use dedicated general Azure client
            cloud_storage = get_general_azure_client()

            # Load project metadata
            metadata = cloud_storage.load_project_metadata(project_id)
            if not metadata:
                return {
                    "status": "error",
                    "error": "Project metadata not found",
                    "project_id": project_id
                }

            backend_deployment = metadata.get("backend_deployment")
            if not backend_deployment:
                return {
                    "status": "not_deployed",
                    "message": f"Backend not deployed yet - cannot perform {request.operation}",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

            backend_url = backend_deployment.get("url")
            if not backend_url:
                return {
                    "status": "error",
                    "error": "Backend URL not found in deployment metadata",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

            # Validate operation
            valid_operations = ["insert", "update", "delete"]
            if request.operation not in valid_operations:
                return {
                    "status": "error",
                    "error": f"Invalid operation: {request.operation}. Valid operations: {valid_operations}",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

            # Validate required fields
            if request.operation in ["update", "delete"] and request.row_id is None:
                return {
                    "status": "error",
                    "error": f"row_id is required for {request.operation} operation",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

            if request.operation in ["insert", "update"] and not request.data:
                return {
                    "status": "error",
                    "error": f"data is required for {request.operation} operation",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

            # Call the deployed backend's table management endpoint
            call_start_time = datetime.now()

            try:
                timeout = aiohttp.ClientTimeout(total=10)  # Longer timeout for write operations
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    manage_url = f"{backend_url}/_internal/db/tables/{table_name}/manage"

                    # Prepare request payload for backend
                    request_payload = {
                        "operation": request.operation,
                        "data": request.data,
                        "row_id": request.row_id
                    }

                    print(f"🔧 Table operation {request.operation} on {table_name}: {manage_url}")

                    async with session.post(manage_url, json=request_payload) as response:
                        call_duration = (datetime.now() - call_start_time).total_seconds() * 1000

                        if response.status == 200:
                            operation_response = await response.json()

                            # Add streaming API metadata to response
                            operation_response["project_id"] = project_id
                            operation_response["call_info"] = {
                                "response_time_ms": round(call_duration, 1),
                                "called_at": call_start_time.isoformat(),
                                "backend_url": backend_url
                            }

                            # Clear relevant cache entries after successful write operations
                            if operation_response.get("status") == "success":
                                # Clear table view cache for this table
                                table_cache_key = f"table_view_{project_id}_{table_name}"
                                if table_cache_key in _database_inspection_cache:
                                    del _database_inspection_cache[table_cache_key]
                                    print(f"🧹 Cleared table view cache for {project_id}/{table_name}")

                                # Clear database inspection cache for this project
                                db_cache_key = f"db_inspect_{project_id}"
                                if db_cache_key in _database_inspection_cache:
                                    del _database_inspection_cache[db_cache_key]
                                    print(f"🧹 Cleared database inspection cache for {project_id}")

                            print(f"✅ Table operation {request.operation} completed ({call_duration:.1f}ms)")
                            return operation_response
                        else:
                            try:
                                error_response = await response.json()
                                error_msg = error_response.get("error", f"HTTP {response.status}")
                            except:
                                error_msg = f"Backend returned HTTP {response.status}"

                            return {
                                "status": "error",
                                "error": error_msg,
                                "project_id": project_id,
                                "table_name": table_name,
                                "operation": request.operation,
                                "call_info": {
                                    "response_time_ms": round(call_duration, 1),
                                    "backend_url": backend_url
                                }
                            }

            except asyncio.TimeoutError:
                return {
                    "status": "timeout",
                    "error": f"Table {request.operation} operation timed out",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation,
                    "suggestion": "Operation may be slow or backend unresponsive"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Connection error: {str(e)}",
                    "project_id": project_id,
                    "table_name": table_name,
                    "operation": request.operation
                }

        except Exception as e:
            print(f"❌ Table operation API error for {project_id}/{table_name}: {e}")
            return {
                "status": "error",
                "error": f"Table operation failed: {str(e)}",
                "project_id": project_id,
                "table_name": table_name,
                "operation": getattr(request, 'operation', 'unknown')
            }

    # Add secrets and redeploy backend
    @app.post("/projects/{project_id}/backend/secrets/update")
    async def update_backend_secrets_and_redeploy(project_id: str, secrets: Dict[str, str]):
        """Add/update individual backend secrets without replacing existing ones"""
        try:
            import asyncio
            from utils.crypto_utils import decrypt_data

            # Use general Azure client for non-streaming operations
            cloud_storage = get_general_azure_client()
            
            # Process and decrypt secrets if needed
            decrypted_secrets = {}
            for key, value in secrets.items():
                # Check if value is encrypted (base64 string > 100 chars)
                if isinstance(value, str) and len(value) > 100:
                    try:
                        # Try to decrypt
                        decrypted_value = decrypt_data(value)
                        decrypted_secrets[key] = decrypted_value
                        print(f"🔓 Decrypted: {key}")
                    except:
                        # Not encrypted or decryption failed, use as is
                        decrypted_secrets[key] = value
                else:
                    decrypted_secrets[key] = value
            
            # Update .env file in cloud storage
            env_path = "backend/.env"
            existing_env = cloud_storage.download_file(project_id, env_path) or ""
            
            # Parse existing .env
            env_vars = {}
            for line in existing_env.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    env_vars[k] = v
            
            # Add new secrets
            env_vars.update(decrypted_secrets)
            
            # Build new .env content
            new_env = []
            for k, v in sorted(env_vars.items()):
                if ' ' in v or '"' in v:
                    v = v.replace('"', '\\"')
                    new_env.append(f'{k}="{v}"')
                else:
                    new_env.append(f'{k}={v}')
            
            new_env_content = '\n'.join(new_env) + '\n'
            
            # Upload updated .env
            cloud_storage.upload_file(project_id, env_path, new_env_content)
            print(f"✅ Updated .env with {len(decrypted_secrets)} secrets")
            
            # Use decrypted secrets for Modal
            secrets = decrypted_secrets

            # Load existing project metadata
            metadata = cloud_storage.load_project_metadata(project_id)
            if not metadata or not metadata.get("backend_deployment"):
                return {
                    "status": "error",
                    "error": "No backend deployment found for this project",
                    "project_id": project_id
                }

            backend_deployment = metadata["backend_deployment"]
            secret_name = backend_deployment.get("secret_name")
            app_name = backend_deployment["app_name"]

            if not secret_name:
                return {
                    "status": "error",
                    "error": "No secret name found in backend deployment info",
                    "project_id": project_id
                }

            print(f"🔐 Adding new secrets to existing Modal secret: {secret_name}")

            try:
                # Step 1: Use all environment variables from .env file as the complete secret set
                # This ensures we don't lose any existing keys and have the most up-to-date values
                print(f"🔍 Using .env file variables as complete secret set for: {secret_name}")
                print(f"📋 Total environment variables: {list(env_vars.keys())}")
                
                # Step 2: Create secret args from all .env variables (which now includes new secrets)
                secret_args = []
                for key, value in env_vars.items():
                    # Escape any special characters in values
                    escaped_value = value.replace('"', '\\"') if '"' in value else value
                    secret_args.append(f"{key}={escaped_value}")
                
                print(f"🔗 Creating Modal secret with {len(secret_args)} total keys")
                
                # Step 3: Recreate the secret with all .env keys using --force
                create_proc = await asyncio.create_subprocess_exec(
                    "modal", "secret", "create", "--force", secret_name, *secret_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await asyncio.wait_for(create_proc.communicate(), timeout=30)
                stdout = stdout.decode('utf-8') if stdout else ""
                stderr = stderr.decode('utf-8') if stderr else ""

                if create_proc.returncode == 0:
                    print(f"✅ Successfully updated secret with new keys: {list(secrets.keys())}")
                    updated_secrets = list(secrets.keys())
                    failed_secrets = []
                else:
                    print(f"❌ Failed to update secret: {stderr}")
                    updated_secrets = []
                    failed_secrets = [{"key": "all", "error": stderr}]

            except Exception as e:
                print(f"❌ Error updating secrets: {e}")
                updated_secrets = []
                failed_secrets = [{"key": "all", "error": str(e)}]

            # Update metadata with all secret keys from .env file
            all_secret_keys = list(env_vars.keys())  # Use all keys from .env as the complete list

            # Update backend deployment info in metadata
            backend_deployment["secret_keys"] = all_secret_keys
            backend_deployment["last_secrets_update"] = datetime.now().isoformat()

            # Save updated metadata
            metadata["backend_deployment"] = backend_deployment
            cloud_storage.save_project_metadata(project_id, metadata)

            if updated_secrets:
                return {
                    "status": "success",
                    "message": f"Successfully added {len(updated_secrets)} secret(s) to existing backend",
                    "app_name": app_name,
                    "secret_name": secret_name,
                    "updated_secrets": updated_secrets,
                    "failed_secrets": failed_secrets,
                    "project_id": project_id
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to add any secrets",
                    "failed_secrets": failed_secrets,
                    "project_id": project_id
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "project_id": project_id
            }

    @app.get("/{project_id}/server_info")
    async def get_server_info(project_id: str):
        """
        Get basic server information for a project (for testing/debugging)
        """
        try:
            return {
                "status": "success",
                "message": "Server info endpoint is working",
                "project_id": project_id,
                "timestamp": int(time.time() * 1000),
                "server": "streaming_api",
                "methods": {
                    "POST": "Submit logs/network data",
                    "GET": "Get server status"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "project_id": project_id
            }

    @app.post("/{project_id}/server_info")
    async def handle_server_info(project_id: str, request: Request, info_request: ServerInfoRequest):
        """
        Handle frontend logs and network requests for a specific project
        ULTRA-FAST: Queues data immediately and returns, processes in background
        """
        try:
            from log_queue import get_log_queue

            # Get the fast queue (no DB connection needed here)
            log_queue = get_log_queue()

            # Prepare the data entry
            entry_data = {
                "timestamp": info_request.timestamp,
                "time": info_request.time,
                "type": info_request.type,
            }

            # Add type-specific data
            if info_request.type == "logs":
                entry_data.update({
                    "logType": info_request.logType,
                    "args": info_request.args,
                    "message": info_request.message
                })
            elif info_request.type == "network":
                entry_data.update({
                    "method": info_request.method,
                    "url": info_request.url,
                    "status": info_request.status,
                    "duration": info_request.duration,
                    "requestData": info_request.requestData,
                    "responseData": info_request.responseData,
                    "responseHeaders": info_request.responseHeaders
                })

            # Queue for background processing (immediate return)
            queued = log_queue.add_entry(project_id, info_request.type, entry_data)

            # Return immediately (no waiting for DB operations)
            return {
                "status": "success",
                "message": f"Queued {info_request.type} data for processing",
                "project_id": project_id,
                "queued": queued,
                "storage": "background_queue"
            }

        except Exception as e:
            print(f"❌ Error queuing server_info for project {project_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "project_id": project_id
            }

    @app.get("/{project_id}/logs/{log_type}")
    async def get_project_logs(project_id: str, log_type: str, limit: int = 100):
        """
        Retrieve stored logs or network requests for a specific project

        Args:
            project_id: Project identifier
            log_type: Either "logs" or "network"
            limit: Maximum number of entries to return (default: 100)
        """
        try:
            from cosmos_db import get_cosmos_client

            # Validate log_type
            if log_type not in ["logs", "network"]:
                raise HTTPException(status_code=400, detail="log_type must be 'logs' or 'network'")

            print(f"📋 Retrieving {log_type} data for project {project_id} (limit: {limit})")

            # Get Cosmos DB client
            cosmos = get_cosmos_client()

            # Retrieve entries
            entries = cosmos.get_entries(project_id, log_type, limit)
            entry_count = cosmos.get_entry_count(project_id, log_type)

            print(f"📊 Found {len(entries)} {log_type} entries for project {project_id}")

            return {
                "status": "success",
                "project_id": project_id,
                "log_type": log_type,
                "entries": entries,
                "returned_count": len(entries),
                "total_count": entry_count,
                "storage": "cosmos_db"
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error retrieving {log_type} for project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/queue/status")
    async def get_queue_status():
        """Get background queue status and statistics"""
        try:
            from log_queue import get_log_queue

            log_queue = get_log_queue()
            stats = log_queue.get_stats()

            return {
                "status": "success",
                "queue_stats": stats,
                "queue_health": "healthy" if stats["worker_alive"] else "unhealthy"
            }

        except Exception as e:
            print(f"❌ Error getting queue status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app

if __name__ == "__main__":
    # For local development
    import uvicorn

    print("🚀 Starting Model Conversation API Server with WebContainer Integration")
    print("=" * 60)
    print("Endpoints:")
    print("  POST /chat/stream - Stream chat with model")
    print("  GET /conversations - List all conversations")
    print("  GET /conversations/{id}/info - Get conversation details")
    print("  DELETE /conversations/{id} - Delete conversation")
    print("  GET /projects/{id}/backend/info - Get backend deployment info & health")
    print("  GET /projects/{id}/backend/database/inspect - Inspect deployed backend database")
    print("  GET /projects/{id}/backend/database/tables/{table} - View specific table data")
    print("  POST /projects/{id}/backend/database/tables/{table}/manage - Manage table (insert/update/delete)")
    print("  POST /{project_id}/server_info - Queue logs/network (ULTRA-FAST)")
    print("  GET /{project_id}/logs/{type} - Retrieve stored logs/network data")
    print("  GET /queue/status - Background queue statistics")
    print("  POST /modal/deploy - Deploy backend to Modal.com")
    print("  POST /netlify/deploy - Deploy frontend to Netlify")
    print("  POST /cloudflare/deploy - Deploy frontend to Cloudflare Pages")
    print("=" * 50)

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8084)

# For Railway deployment
app = create_app()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
