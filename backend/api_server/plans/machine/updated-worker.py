import os
import time
import json
import subprocess
import tempfile
import shutil
from azure.storage.queue import QueueClient
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;EndpointSuffix=core.windows.net"
QUEUE_NAME = "llm-jobs"
PROJECTS_DIR = "projects"
RESULT_DIR = "results"
POLL_INTERVAL_SECONDS = 1

print("Worker starting...")
queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)

def get_project_working_directory(project_id: str, working_dir: Optional[str] = None) -> str:
    """Get the working directory for a project command"""
    base_path = os.path.join(PROJECTS_DIR, project_id)

    if working_dir:
        # Specific subdirectory requested (frontend/backend)
        target_path = os.path.join(base_path, working_dir)
        # FIXED: Always return the target path, let the calling function handle directory creation
        return target_path

    return base_path

def execute_command(project_id: str, command: str, working_dir: Optional[str] = None) -> dict:
    """Execute a shell command in project directory"""
    project_path = get_project_working_directory(project_id, working_dir)

    # Create working directory if it doesn't exist
    if not os.path.exists(project_path):
        # Check if base project exists first
        base_path = os.path.join(PROJECTS_DIR, project_id)
        if not os.path.exists(base_path):
            return {
                "stdout": "",
                "stderr": f"Project directory {project_id} not found",
                "return_code": 1,
                "working_directory": project_path
            }

        # Create the working directory
        try:
            os.makedirs(project_path, exist_ok=True)
            print(f"Created working directory: {project_path}")
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Failed to create working directory {project_path}: {str(e)}",
                "return_code": 1,
                "working_directory": project_path
            }

    try:
        print(f"Executing '{command}' in {project_path}")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=300,  # 5 minute timeout
            env={**os.environ, 'PATH': f"{os.environ.get('PATH', '')}:/usr/local/bin"}
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "working_directory": project_path
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 5 minutes",
            "return_code": 124,
            "working_directory": project_path
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "return_code": 1,
            "working_directory": project_path
        }

def read_file(project_id: str, file_path: str, working_dir: Optional[str] = None) -> dict:
    """Read a file from project directory"""
    project_path = get_project_working_directory(project_id, working_dir)
    full_path = os.path.join(project_path, file_path)

    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "content": "",
            "error": f"Project directory {project_id} not found",
            "exists": False,
            "working_directory": project_path,
            "file_path": file_path
        }

    if not os.path.exists(full_path):
        return {
            "content": "",
            "error": f"File {file_path} not found",
            "exists": False,
            "working_directory": project_path,
            "file_path": file_path
        }

    try:
        # Check if it's a text file (avoid reading binary files)
        try:
            with open(full_path, 'rb') as f:
                sample = f.read(512)
                if b'\0' in sample:
                    return {
                        "content": "",
                        "error": "File appears to be binary",
                        "exists": True,
                        "working_directory": project_path,
                        "file_path": file_path,
                        "is_binary": True
                    }
        except:
            pass

        # Read text file
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        file_stats = os.stat(full_path)

        return {
            "content": content,
            "error": None,
            "exists": True,
            "size": len(content),
            "working_directory": project_path,
            "file_path": file_path,
            "last_modified": file_stats.st_mtime,
            "is_binary": False
        }
    except Exception as e:
        return {
            "content": "",
            "error": f"Error reading file: {str(e)}",
            "exists": True,
            "working_directory": project_path,
            "file_path": file_path
        }

def create_file(project_id: str, payload: dict, working_dir: Optional[str] = None) -> dict:
    """Create a new file in project directory"""
    project_path = get_project_working_directory(project_id, working_dir)
    file_path = payload["file_path"]
    content = payload["content"]
    overwrite = payload.get("overwrite", False)
    full_path = os.path.join(project_path, file_path)

    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "success": False,
            "error": f"Project directory {project_id} not found",
            "working_directory": project_path,
            "file_path": file_path
        }

    # Check if file exists and overwrite is False
    if os.path.exists(full_path) and not overwrite:
        return {
            "success": False,
            "error": f"File {file_path} already exists and overwrite is False",
            "working_directory": project_path,
            "file_path": file_path,
            "exists": True
        }

    try:
        # FIXED: Create the full directory structure including working_dir
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        # Also ensure the working directory itself exists
        os.makedirs(project_path, exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        file_stats = os.stat(full_path)

        print(f"Created file {file_path} in {project_path}")

        return {
            "success": True,
            "error": None,
            "working_directory": project_path,
            "file_path": file_path,
            "size": len(content),
            "last_modified": file_stats.st_mtime
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error creating file: {str(e)}",
            "working_directory": project_path,
            "file_path": file_path
        }

def update_file(project_id: str, payload: dict, working_dir: Optional[str] = None) -> dict:
    """Update an existing file in project directory"""
    project_path = get_project_working_directory(project_id, working_dir)
    file_path = payload["file_path"]
    content = payload["content"]
    create_if_missing = payload.get("create_if_missing", True)
    full_path = os.path.join(project_path, file_path)

    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "success": False,
            "error": f"Project directory {project_id} not found",
            "working_directory": project_path,
            "file_path": file_path
        }

    # Check if file exists
    if not os.path.exists(full_path) and not create_if_missing:
        return {
            "success": False,
            "error": f"File {file_path} does not exist and create_if_missing is False",
            "working_directory": project_path,
            "file_path": file_path,
            "exists": False
        }

    try:
        # FIXED: Create the full directory structure including working_dir
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        # Also ensure the working directory itself exists
        os.makedirs(project_path, exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        file_stats = os.stat(full_path)

        print(f"Updated file {file_path} in {project_path}")

        return {
            "success": True,
            "error": None,
            "working_directory": project_path,
            "file_path": file_path,
            "size": len(content),
            "last_modified": file_stats.st_mtime
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error updating file: {str(e)}",
            "working_directory": project_path,
            "file_path": file_path
        }

def delete_file(project_id: str, file_path: str, working_dir: Optional[str] = None) -> dict:
    """Delete a file from project directory"""
    project_path = get_project_working_directory(project_id, working_dir)
    full_path = os.path.join(project_path, file_path)

    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "success": False,
            "error": f"Project directory {project_id} not found",
            "working_directory": project_path,
            "file_path": file_path
        }

    if not os.path.exists(full_path):
        return {
            "success": False,
            "error": f"File {file_path} not found",
            "working_directory": project_path,
            "file_path": file_path,
            "exists": False
        }

    try:
        # Delete file
        os.remove(full_path)

        print(f"Deleted file {file_path} from {project_path}")

        return {
            "success": True,
            "error": None,
            "working_directory": project_path,
            "file_path": file_path,
            "deleted": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error deleting file: {str(e)}",
            "working_directory": project_path,
            "file_path": file_path
        }

def list_directory(project_id: str, dir_path: str = ".", working_dir: Optional[str] = None) -> dict:
    """List directory contents in project"""
    project_path = get_project_working_directory(project_id, working_dir)
    full_path = os.path.join(project_path, dir_path)

    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "files": [],
            "directories": [],
            "error": f"Project directory {project_id} not found",
            "working_directory": project_path
        }

    if not os.path.exists(full_path):
        return {
            "files": [],
            "directories": [],
            "error": f"Directory {dir_path} not found",
            "working_directory": project_path
        }

    try:
        items = os.listdir(full_path)
        files = []
        directories = []

        for item in items:
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                files.append(item)
            elif os.path.isdir(item_path):
                directories.append(item)

        return {
            "files": sorted(files),
            "directories": sorted(directories),
            "error": None,
            "working_directory": project_path,
            "listed_path": dir_path
        }
    except Exception as e:
        return {
            "files": [],
            "directories": [],
            "error": f"Error listing directory: {str(e)}",
            "working_directory": project_path
        }

def deploy_cloudflare(project_id: str, payload: dict, working_dir: Optional[str] = None) -> dict:
    """Deploy frontend to Cloudflare Pages using Wrangler CLI"""
    project_path = get_project_working_directory(project_id, working_dir)
    project_name = payload["project_name"]
    environment = payload.get("environment", "production")
    env_vars = payload.get("env_vars", {})
    force_rebuild = payload.get("force_rebuild", False)
    
    # Check if base project exists
    base_path = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(base_path):
        return {
            "status": "error",
            "error_type": "project_not_found",
            "message": f"Project directory {project_id} not found",
            "project_name": project_name
        }
    
    # Check if frontend directory exists
    if not os.path.exists(project_path):
        return {
            "status": "error", 
            "error_type": "frontend_not_found",
            "message": f"Frontend directory not found for project {project_id}",
            "project_name": project_name
        }
    
    # Get Cloudflare credentials from environment
    cf_token = os.getenv('CLOUDFLARE_API_TOKEN')
    cf_account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    
    if not cf_token or not cf_account_id:
        return {
            "status": "error",
            "error_type": "missing_credentials", 
            "message": "Cloudflare API token or Account ID not configured in environment variables",
            "suggestions": [
                "Set CLOUDFLARE_API_TOKEN environment variable",
                "Set CLOUDFLARE_ACCOUNT_ID environment variable"
            ]
        }
    
    deployment_logs = []
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_dir = os.path.join(temp_dir, "deploy")
            
            # Copy frontend files to temporary directory
            deployment_logs.append("📂 Copying frontend files to temporary build directory")
            print(f"Copying {project_path} to {deploy_dir}")
            shutil.copytree(project_path, deploy_dir)
            
            # Create environment file with custom variables
            if env_vars:
                deployment_logs.append(f"🔧 Creating environment file with {len(env_vars)} variables")
                env_content = ["NODE_ENV=production"]
                
                for key, value in env_vars.items():
                    # For Vite applications, use VITE_ prefix for client-side variables
                    if not key.startswith(('VITE_', 'REACT_APP_', 'NEXT_PUBLIC_', 'VUE_APP_')):
                        key = f"VITE_{key}"
                    env_content.append(f"{key}={value}")
                
                env_file_path = os.path.join(deploy_dir, '.env.production')
                with open(env_file_path, 'w') as f:
                    f.write('\n'.join(env_content))
                print(f"Created environment file: {env_file_path}")
            
            # Detect and run build process
            package_json_path = os.path.join(deploy_dir, 'package.json')
            build_dir = deploy_dir
            
            if os.path.exists(package_json_path):
                deployment_logs.append("📦 Detected package.json, running Vite build process")
                
                # Install dependencies first
                deployment_logs.append("⬇️ Installing dependencies...")
                npm_install_result = subprocess.run(
                    ['npm', 'install'],
                    cwd=deploy_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env={**os.environ, 'PATH': f"{os.environ.get('PATH', '')}:/usr/local/bin"}
                )
                
                if npm_install_result.returncode != 0:
                    return {
                        "status": "error",
                        "error_type": "install_failed",
                        "message": "Failed to install dependencies",
                        "logs": deployment_logs + [f"npm install error: {npm_install_result.stderr}"]
                    }
                
                # Run Vite build with proper environment
                deployment_logs.append("🔨 Running Vite build...")
                build_env = os.environ.copy()
                build_env.update({
                    'PATH': f"{deploy_dir}/node_modules/.bin:{os.environ.get('PATH', '')}:/usr/local/bin",
                    'NODE_ENV': 'production'
                })
                
                build_result = subprocess.run(
                    ['npm', 'run', 'build'],
                    cwd=deploy_dir,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=build_env
                )
                
                if build_result.returncode != 0:
                    deployment_logs.append("❌ Build failed, checking for missing dependencies...")
                    deployment_logs.append(f"Build error: {build_result.stderr}")
                    return {
                        "status": "error",
                        "error_type": "build_failed", 
                        "message": "Frontend build process failed",
                        "logs": deployment_logs,
                        "suggestions": [
                            "Check package.json build script",
                            "Verify all dependencies are installed",
                            "Review build logs for missing packages"
                        ]
                    }
                
                # For Vite, build output is typically in 'dist' directory
                vite_dist_dir = os.path.join(deploy_dir, 'dist')
                if os.path.exists(vite_dist_dir):
                    build_dir = vite_dist_dir
                    deployment_logs.append("📁 Using Vite build output: dist/")
                else:
                    # Fallback to other common build directories
                    potential_build_dirs = ['build', 'out', '.next/out']
                    for build_subdir in potential_build_dirs:
                        potential_path = os.path.join(deploy_dir, build_subdir)
                        if os.path.exists(potential_path):
                            build_dir = potential_path
                            deployment_logs.append(f"📁 Detected build output: {build_subdir}/")
                            break
                    else:
                        deployment_logs.append("📁 Using project root as build output")
            else:
                deployment_logs.append("📄 No package.json found, deploying as static files")
            
            # Setup deployment environment
            deployment_env = os.environ.copy()
            deployment_env.update({
                'CLOUDFLARE_API_TOKEN': cf_token,
                'CLOUDFLARE_ACCOUNT_ID': cf_account_id,
                'NODE_ENV': 'production'
            })
            
            # Create Cloudflare Pages project first (it's ok if it already exists)
            deployment_logs.append(f"🔧 Creating Cloudflare Pages project: {project_name}")
            
            create_project_cmd = [
                'npx', 'wrangler', 'pages', 'project', 'create', project_name,
                '--production-branch', 'main'
            ]
            
            create_result = subprocess.run(
                create_project_cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                env=deployment_env,
                timeout=60
            )
            
            if create_result.returncode == 0:
                deployment_logs.append("✅ Project created successfully")
            else:
                deployment_logs.append("ℹ️ Project already exists or creation failed (continuing anyway)")
            
            # Deploy to Cloudflare Pages using Wrangler
            deployment_logs.append(f"🚀 Deploying to Cloudflare Pages: {project_name}")
            
            wrangler_cmd = [
                'npx', 'wrangler', 'pages', 'deploy', build_dir,
                '--project-name', project_name
            ]
            
            print(f"Running deployment command: {' '.join(wrangler_cmd)}")
            
            deploy_result = subprocess.run(
                wrangler_cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                env=deployment_env,
                timeout=600  # 10 minutes
            )
            
            # Parse deployment output
            stdout_lines = deploy_result.stdout.split('\n') if deploy_result.stdout else []
            stderr_lines = deploy_result.stderr.split('\n') if deploy_result.stderr else []
            
            all_output = stdout_lines + stderr_lines
            deployment_logs.extend([line for line in all_output if line.strip()])
            
            if deploy_result.returncode == 0:
                # Extract URLs from deployment output
                deployment_url = None
                preview_url = None
                
                for line in all_output:
                    if 'https://' in line and '.pages.dev' in line:
                        if not deployment_url:
                            deployment_url = line.strip()
                        elif not preview_url and line != deployment_url:
                            preview_url = line.strip()
                
                # Fallback URL construction if not found in output
                if not deployment_url:
                    deployment_url = f"https://{project_name}.pages.dev"
                
                deployment_logs.append(f"✅ Deployment successful!")
                
                return {
                    "status": "success",
                    "deployment_url": deployment_url,
                    "preview_url": preview_url,
                    "project_name": project_name,
                    "environment": environment,
                    "logs": deployment_logs
                }
            else:
                return {
                    "status": "error",
                    "error_type": "deployment_failed",
                    "message": "Cloudflare Pages deployment failed",
                    "logs": deployment_logs,
                    "suggestions": [
                        "Check Cloudflare API token permissions",
                        "Verify project name is available",
                        "Review deployment logs for specific errors",
                        "Try redeploying with force_rebuild=true"
                    ]
                }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Deployment timed out",
            "logs": deployment_logs + ["⏱️ Deployment process timed out after 10 minutes"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unexpected_error",
            "message": f"Unexpected error during deployment: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }

# Main worker loop
while True:
    try:
        messages = queue_client.receive_messages(messages_per_page=1, visibility_timeout=300)

        for message in messages:
            try:
                job = json.loads(message.content)
                job_id = job["job_id"]
                job_type = job["type"]
                project_id = job["project_id"]
                working_dir = job.get("working_dir")  # Optional: "frontend", "backend", or None
                payload = job["payload"]

                print(f"Processing job {job_id} (type: {job_type}) for project {project_id}")
                if working_dir:
                    print(f"  Working directory: {working_dir}")

                # Execute job based on type
                if job_type == "execute":
                    output = execute_command(project_id, payload, working_dir)
                elif job_type == "read_file":
                    output = read_file(project_id, payload, working_dir)
                elif job_type == "list_directory":
                    output = list_directory(project_id, payload, working_dir)
                elif job_type == "create_file":
                    output = create_file(project_id, payload, working_dir)
                elif job_type == "update_file":
                    output = update_file(project_id, payload, working_dir)
                elif job_type == "delete_file":
                    output = delete_file(project_id, payload, working_dir)
                elif job_type == "deploy_cloudflare":
                    output = deploy_cloudflare(project_id, payload, working_dir)
                else:
                    output = {"error": f"Unknown job type: {job_type}"}

                # Write result
                result_path = os.path.join(RESULT_DIR, f"{job_id}.json")
                with open(result_path, 'w') as f:
                    json.dump(output, f, indent=2)

                # Delete message from queue
                queue_client.delete_message(message)
                print(f"Completed job {job_id}")

            except json.JSONDecodeError as e:
                print(f"Error decoding message: {e}")
                queue_client.delete_message(message)
            except Exception as e:
                print(f"Error processing job: {e}")

    except Exception as e:
        print(f"Worker error: {e}")

    time.sleep(POLL_INTERVAL_SECONDS)
