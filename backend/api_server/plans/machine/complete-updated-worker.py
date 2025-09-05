import os
import time
import json
import subprocess
from azure.storage.queue import QueueClient
from typing import Optional

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
        if os.path.exists(target_path):
            return target_path
        else:
            # Fallback to base project if subdirectory doesn't exist
            return base_path
    
    return base_path

def execute_command(project_id: str, command: str, working_dir: Optional[str] = None) -> dict:
    """Execute a shell command in project directory"""
    project_path = get_project_working_directory(project_id, working_dir)
    
    if not os.path.exists(project_path):
        return {
            "stdout": "",
            "stderr": f"Project directory {project_id} not found",
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
    
    if not os.path.exists(project_path):
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
    
    if not os.path.exists(project_path):
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
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
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
    
    if not os.path.exists(project_path):
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
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
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
    
    if not os.path.exists(project_path):
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
    
    if not os.path.exists(project_path):
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