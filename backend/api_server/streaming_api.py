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
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import the model system and project pool
from base_test_azure_hybrid import BoilerplatePersistentGroq, FrontendCommandInterrupt
from project_pool_manager import get_pool_manager


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

class ModalDeploymentResponse(BaseModel):
    status: str
    app_name: str
    url: Optional[str] = None
    docs_url: Optional[str] = None
    logs_command: Optional[str] = None
    error: Optional[str] = None
    deployment_output: Optional[str] = None

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
from utils import generate_short_app_name

def extract_modal_url(output: str, app_name: str) -> Optional[str]:
    """Extract the deployed URL from Modal's output"""
    lines = output.split('\n')
    for line in lines:
        if 'modal.run' in line and 'https://' in line:
            words = line.split()
            for word in words:
                if word.startswith('https://') and 'modal.run' in word:
                    return word.rstrip('.,!?')

    # Fallback URL pattern (will need to be updated with actual username)
    return f"https://your-username--{app_name}-fastapi-app.modal.run"




async def _execute_modal_deployment(request: ModalDeploymentRequest) -> ModalDeploymentResponse:
    """Execute the actual Modal deployment (extracted from original function)"""
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

            # Handle secrets creation for first deployment with fallback
            secrets_created_successfully = True
            final_secrets = {}  # Initialize to avoid undefined variable

            if not request.redeployment:
                print(f"🔐 Creating Modal secrets for first deployment")

                default_secrets = {
                    "SECRET_KEY": f"auto-generated-key-{request.app_name}-{hash(request.project_id) % 10000}",
                    "DATABASE_NAME": request.database_name or f"{request.app_name}_database.db",
                    "APP_TITLE": request.app_title or "AI Generated Backend",
                    "APP_DESCRIPTION": request.app_description or "Auto-generated FastAPI backend"
                }

                final_secrets = {**default_secrets}
                if request.secrets:
                    final_secrets.update(request.secrets)

                # Try to create secrets, but fallback to redeployment if it fails
                try:
                    secrets_request = ModalSecretsRequest(
                        secret_name=secret_name,
                        secrets=final_secrets,
                        overwrite=False  # Don't try to delete - we know secrets don't exist
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
                print(f"🔄 Redeployment mode: checking if secrets exist...")

                # For redeployments, we still need to ensure secrets exist
                # Set up default secrets in case they need to be created
                default_secrets = {
                    "SECRET_KEY": f"auto-generated-key-{request.app_name}-{hash(request.project_id) % 10000}",
                    "DATABASE_NAME": request.database_name or f"{request.app_name}_database.db",
                    "APP_TITLE": request.app_title or "AI Generated Backend",
                    "APP_DESCRIPTION": request.app_description or "Auto-generated FastAPI backend"
                }

                final_secrets = {**default_secrets}
                if request.secrets:
                    final_secrets.update(request.secrets)

                # Skip secret creation for now, but we'll handle missing secrets after deployment fails
                secrets_created_successfully = False

            # Change to project directory and deploy with REAL Modal CLI
            original_cwd = os.getcwd()
            os.chdir(project_path)

            try:
                print(f"🚀 REAL Modal deployment starting...")

                # Run ACTUAL modal deploy command
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
                            env_content = f"VITE_APP_BACKEND_URL={deployed_url}\n"
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
            deployment_output=f"Successfully deployed {request.app_name} with {len(backend_files)} backend files"
        )

    except subprocess.CalledProcessError as e:
        # For subprocess errors, use the detailed error information we prepared
        error_details = e.stderr if e.stderr else str(e)
        return ModalDeploymentResponse(
            status="error",
            app_name=request.app_name,
            error=error_details
        )
    except Exception as e:
        return ModalDeploymentResponse(
            status="error",
            app_name=request.app_name,
            error=str(e)
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
        api_key = os.getenv("GROQ_API_KEY", "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")
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is required")
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

        async def stream_response(self, message: str) -> AsyncGenerator[str, None]:
            """Stream the model response with action tracking"""
            try:
                print(f"🌊 Starting stream_response for: {message[:30]}...")
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
                    result = await self.model_system._process_update_request_with_interrupts(message, streaming_callback=stream_callback)

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

                    # Try to get an available project from the pool
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

                        # Mark project as active in the pool
                        pool_manager.mark_project_active(pooled_project_id)

                        initialization_time = datetime.now()
                        print(f"⚡ Total initialization time: {(initialization_time - start_time).total_seconds():.3f}s")
                        mode = "create_from_pool"
                    else:
                        # Fallback: create project normally (emergency case)
                        print(f"⚠️ No pooled projects available, creating emergency project")
                        from base_test_azure_hybrid import generate_project_name

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

            # Save user message to streaming conversation history (avoid command results)
            if not is_action_result:
                try:
                    from cloud_storage import AzureBlobStorage

                    project_id = getattr(model_system, 'project_id', None)
                    if project_id:
                        user_message_chunk = {
                            "type": "user_message",
                            "data": {
                                "content": request.message,
                                "message_type": "user"
                            },
                            "conversation_id": conversation_id,
                            "timestamp": datetime.now().isoformat(),
                            "action_id": None,
                            "is_command_result": False
                        }

                        cloud_storage = get_streaming_azure_client()
                        cloud_storage.append_streaming_chunk(project_id, user_message_chunk)
                        print(f"💾 Saved user message to streaming history")

                except Exception as e:
                    print(f"⚠️ Failed to save user message to streaming history: {e}")
            else:
                # This is a command result - save with special marker
                try:
                    from cloud_storage import AzureBlobStorage

                    project_id = getattr(model_system, 'project_id', None)
                    if project_id:
                        command_result_chunk = {
                            "type": "user_message",
                            "data": {
                                "content": request.message,
                                "message_type": "user"
                            },
                            "conversation_id": conversation_id,
                            "timestamp": datetime.now().isoformat(),
                            "action_id": None,
                            "is_command_result": True
                        }

                        cloud_storage = get_streaming_azure_client()
                        cloud_storage.append_streaming_chunk(project_id, command_result_chunk)
                        print(f"💾 Saved command result to streaming history")

                except Exception as e:
                    print(f"⚠️ Failed to save command result to streaming history: {e}")

            # Create streaming wrapper
            streaming_wrapper = StreamingModelWrapper(model_system, conversation_id)

            # Add timing context to wrapper
            streaming_wrapper.request_start_time = start_time

            # Return streaming response
            return StreamingResponse(
                streaming_wrapper.stream_response(request.message),
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
            from base_test_azure_hybrid import BoilerplatePersistentGroq, generate_project_name

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
            webcontainer_files = convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)

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

                # Skip excluded patterns
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

            print(f"📁 Found {len(frontend_files)} frontend files for project {project_id}")

            # Convert to WebContainer mount format
            webcontainer_files = convert_to_webcontainer_format(project_id, frontend_files, cloud_storage)

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

            for file_path in request.file_paths:
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
                total_files=len(request.file_paths),
                successful_files=successful_count,
                failed_files=failed_count
            )

        except Exception as e:
            print(f"❌ Error in bulk file retrieval for {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")

    def convert_to_webcontainer_format(project_id: str, files_list: list, cloud_storage) -> dict:
        """Convert cloud files to WebContainer mount format"""
        try:
            webcontainer_files = {}

            for file_path in files_list:
                # For downloading, we need the original path with frontend/ prefix
                original_path = f"frontend/{file_path}" if not file_path.startswith('frontend/') else file_path

                # Download file content from cloud using original path
                content = cloud_storage.download_file(project_id, original_path)
                if content is None:
                    print(f"⚠️ Could not download content for {original_path}")
                    continue

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
                    "message": "Deployment completed successfully"
                }
            else:
                return {
                    "status": "error",
                    "app_name": result.app_name,
                    "error": result.error,
                    "message": "Deployment failed"
                }

        except Exception as e:
            print(f"❌ Synchronous deployment failed: {e}")
            return {
                "status": "error",
                "app_name": request.app_name,
                "error": str(e),
                "message": "Deployment failed with exception"
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

    # Add secrets and redeploy backend
    @app.post("/projects/{project_id}/backend/secrets/update")
    async def update_backend_secrets_and_redeploy(project_id: str, secrets: Dict[str, str]):
            """Add/update individual backend secrets without replacing existing ones"""
            try:
                import asyncio

                # Use general Azure client for non-streaming operations
                cloud_storage = get_general_azure_client()

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

                # Add each new secret variable individually using modal secret set
                updated_secrets = []
                failed_secrets = []

                for key, value in secrets.items():
                    try:
                        print(f"🔑 Adding secret: {key}")

                        # Use modal secret set to ADD this variable to existing secret
                        proc = await asyncio.create_subprocess_exec(
                            "modal", "secret", "set", secret_name, f"{key}={value}",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )

                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                        stdout = stdout.decode('utf-8') if stdout else ""
                        stderr = stderr.decode('utf-8') if stderr else ""

                        if proc.returncode == 0:
                            print(f"✅ Successfully added secret: {key}")
                            updated_secrets.append(key)
                        else:
                            print(f"❌ Failed to add secret {key}: {stderr}")
                            failed_secrets.append({"key": key, "error": stderr})

                    except Exception as e:
                        print(f"❌ Error adding secret {key}: {e}")
                        failed_secrets.append({"key": key, "error": str(e)})

                # Update metadata with new secret keys (add to existing list)
                current_secret_keys = backend_deployment.get("secret_keys", [])
                new_secret_keys = list(set(current_secret_keys + updated_secrets))  # Remove duplicates

                # Update backend deployment info in metadata
                backend_deployment["secret_keys"] = new_secret_keys
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
    print("=" * 50)

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8084)

# For Azure deployment
app = create_app()
