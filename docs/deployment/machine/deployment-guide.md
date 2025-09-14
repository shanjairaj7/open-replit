# LLM Agent Backend Deployment Guide

## Step 1: SSH into VM and Install Dependencies

### SSH Connection:
```bash
ssh azureuser@llm-agent-api.eastus.cloudapp.azure.com
```

### Once Connected, Run These Commands:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python, pip, and essential tools
sudo apt-get install -y python3-pip python3-venv ripgrep git curl

# Create project structure
mkdir ~/llm_agent_backend
cd ~/llm_agent_backend
mkdir projects results

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install fastapi "uvicorn[standard]" azure-storage-queue azure-storage-blob requests python-multipart
```

## Step 2: Create Central API (api.py)

```python
# Create api.py
cat > api.py << 'EOF'
import os
import uuid
import asyncio
import json
import zipfile
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient

# Configuration
CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;EndpointSuffix=core.windows.net"
QUEUE_NAME = "llm-jobs"
CONTAINER_NAME = "codebase-projects"
RESULT_DIR = "results"
PROJECTS_DIR = "projects"
POLL_INTERVAL_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 120

app = FastAPI(title="LLM Agent Backend", version="1.0.0")
queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)
blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)

# Ensure directories exist
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

class CommandRequest(BaseModel):
    project_id: str
    command: str

class FileRequest(BaseModel):
    project_id: str
    file_path: str

def download_project_if_needed(project_id: str):
    """Download project from blob storage if not cached locally"""
    project_path = os.path.join(PROJECTS_DIR, project_id)
    
    if os.path.exists(project_path):
        # Update last access time
        os.utime(project_path, None)
        return True
    
    try:
        # Download from blob storage
        blob_client = blob_service.get_blob_client(container=CONTAINER_NAME, blob=f"{project_id}.zip")
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            download_stream = blob_client.download_blob()
            temp_file.write(download_stream.readall())
            temp_file_path = temp_file.name
        
        # Extract project
        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
            zip_ref.extractall(project_path)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        return True
        
    except Exception as e:
        print(f"Error downloading project {project_id}: {e}")
        # Create empty project directory for testing
        os.makedirs(project_path, exist_ok=True)
        return False

@app.get("/")
async def root():
    return {"message": "LLM Agent Backend API", "status": "running"}

@app.post("/execute")
async def execute_command(req: CommandRequest):
    """Execute a command in a project environment"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Download project if needed
    download_project_if_needed(req.project_id)

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "execute",
        "project_id": req.project_id,
        "payload": req.command
    })
    
    # Send to queue
    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    # Read and return result
    with open(result_path, 'r') as f:
        result = json.load(f)

    # Clean up
    os.remove(result_path)
    return result

@app.post("/file/read")
async def read_file(req: FileRequest):
    """Read a file from a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Download project if needed
    download_project_if_needed(req.project_id)

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "read_file",
        "project_id": req.project_id,
        "payload": req.file_path
    })
    
    # Send to queue
    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    # Read and return result
    with open(result_path, 'r') as f:
        result = json.load(f)

    # Clean up
    os.remove(result_path)
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "queue": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
```

## Step 3: Create Worker Process (worker.py)

```python
# Create worker.py
cat > worker.py << 'EOF'
import os
import time
import json
import subprocess
from azure.storage.queue import QueueClient

# Configuration
CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;EndpointSuffix=core.windows.net"
QUEUE_NAME = "llm-jobs"
PROJECTS_DIR = "projects"
RESULT_DIR = "results"
POLL_INTERVAL_SECONDS = 1

print("Worker starting...")
queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)

def execute_command(project_id: str, command: str) -> dict:
    """Execute a shell command in project directory"""
    project_path = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_path):
        return {
            "stdout": "",
            "stderr": f"Project directory {project_id} not found",
            "return_code": 1
        }
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=300  # 5 minute timeout
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 5 minutes",
            "return_code": 124
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "return_code": 1
        }

def read_file(project_id: str, file_path: str) -> dict:
    """Read a file from project directory"""
    project_path = os.path.join(PROJECTS_DIR, project_id)
    full_path = os.path.join(project_path, file_path)
    
    if not os.path.exists(project_path):
        return {
            "content": "",
            "error": f"Project directory {project_id} not found",
            "exists": False
        }
    
    if not os.path.exists(full_path):
        return {
            "content": "",
            "error": f"File {file_path} not found",
            "exists": False
        }
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return {
            "content": content,
            "error": None,
            "exists": True,
            "size": len(content)
        }
    except Exception as e:
        return {
            "content": "",
            "error": f"Error reading file: {str(e)}",
            "exists": True
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
                payload = job["payload"]

                print(f"Processing job {job_id} (type: {job_type}) for project {project_id}")

                # Execute job based on type
                if job_type == "execute":
                    output = execute_command(project_id, payload)
                elif job_type == "read_file":
                    output = read_file(project_id, payload)
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
EOF
```

## Step 4: Create Test Project and Start Services

### Create a sample project:
```bash
# Create test project
mkdir -p projects/test-project
cd projects/test-project

# Create sample files
echo "print('Hello from Python!')" > hello.py
echo "console.log('Hello from Node.js!');" > hello.js
echo "echo 'Hello from Bash!'" > hello.sh
chmod +x hello.sh

# Create package.json for testing
cat > package.json << 'EOF'
{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "start": "node hello.js",
    "test": "echo 'Tests passed!'"
  }
}
EOF

cd ~/llm_agent_backend
```

### Start the services:
```bash
# Terminal 1: Start API server
source venv/bin/activate
python api.py

# Terminal 2: Start worker (open new SSH session)
ssh azureuser@llm-agent-api.eastus.cloudapp.azure.com
cd ~/llm_agent_backend
source venv/bin/activate
python worker.py
```

## Step 5: Test the System

### From your local machine, test the API:

```bash
# Test basic health
curl http://llm-agent-api.eastus.cloudapp.azure.com:8000/

# Test command execution
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "test-project",
    "command": "python3 hello.py"
}'

# Test file reading
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/read" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "test-project", 
    "file_path": "hello.py"
}'

# Test Node.js execution
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "test-project",
    "command": "npm test"
}'
```