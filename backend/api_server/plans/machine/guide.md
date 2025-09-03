Quick-Start Guide: Setting Up Your LLM Agent Backend
This guide provides a step-by-step plan to quickly set up a working prototype of the architecture on Azure.

Phase 1: Provision Azure Resources (Azure Portal)
Create a Resource Group: Create a new resource group to hold all your components (e.g., llm-agent-rg).

Create Storage Account:

Create a new Storage Account.

Inside it, go to Queues and create a new queue named llm-jobs.

Go to Containers and create a new blob container named project-source-code.

Navigate to Access keys and copy one of the Connection Strings. You'll need this for your code.

Create Virtual Machine:

Deploy a new Azure Virtual Machine.

Image: Ubuntu Server 22.04 LTS.

Size: Start with Standard_B4ms (4 vCPU, 16 GB RAM).

Ensure it's in the same resource group.

Configure VM Networking:

Assign DNS Name: Go to the VM's Overview page. Click on the Public IP address. In the configuration for the IP address, set a DNS name label (e.g., my-llm-api). This will give you a URL like http://my-llm-api.eastus.cloudapp.azure.com.

Open API Port: In the VM's Networking settings, add an inbound port rule:

Destination port ranges: 8000

Protocol: TCP

Action: Allow

Name: Allow-API-Port-8000

Phase 2: Configure the VM (via SSH)
Connect to your VM using SSH.

Update System & Install Tools:

sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv ripgrep

Create Project Structure:

# Create the main directory for your backend code
mkdir ~/llm_agent_backend
cd ~/llm_agent_backend

# Create directories for projects, results, and a virtual environment
mkdir projects results
python3 -m venv venv
source venv/bin/activate

# Install Python libraries
pip install fastapi "uvicorn[standard]" azure-storage-queue

Phase 3: Write the Backend Code
Create the following two Python files inside ~/llm_agent_backend.

1. api.py (The Central API):

import os
import uuid
import asyncio
import json
from fastapi import FastAPI
from pydantic import BaseModel
from azure.storage.queue import QueueClient

# --- CONFIGURATION ---
CONNECTION_STRING = "PASTE_YOUR_AZURE_STORAGE_CONNECTION_STRING_HERE"
QUEUE_NAME = "llm-jobs"
RESULT_DIR = "results"
POLL_INTERVAL_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 120

app = FastAPI()
queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)

class CommandRequest(BaseModel):
    project_id: str
    command: str

@app.post("/execute")
async def execute_command(req: CommandRequest):
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # 1. Create and send the job message
    job_message = json.dumps({
        "job_id": job_id,
        "project_id": req.project_id,
        "command": req.command
    })
    queue_client.send_message(job_message)

    # 2. Wait for the result file to appear
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    # 3. Read and return the result
    with open(result_path, 'r') as f:
        result = json.load(f)

    # 4. Clean up the result file
    os.remove(result_path)
    return result

2. worker.py (A Single Worker):

import os
import time
import json
import subprocess
from azure.storage.queue import QueueClient

# --- CONFIGURATION ---
CONNECTION_STRING = "PASTE_YOUR_AZURE_STORAGE_CONNECTION_STRING_HERE"
QUEUE_NAME = "llm-jobs"
PROJECTS_DIR = "projects"
RESULT_DIR = "results"
POLL_INTERVAL_SECONDS = 1

print("Worker starting...")
queue_client = QueueClient.from_connection_string(CONNECTION_STRING, QUEUE_NAME)

while True:
    messages = queue_client.receive_messages(messages_per_page=1, visibility_timeout=300)

    for message in messages:
        try:
            job = json.loads(message.content)
            job_id = job["job_id"]
            project_id = job["project_id"]
            command = job["command"]

            print(f"Processing job {job_id} for project {project_id}")

            # NOTE: Add project syncing logic here later
            project_path = os.path.join(PROJECTS_DIR, project_id)
            if not os.path.exists(project_path):
                 os.makedirs(project_path) # Placeholder

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=project_path # IMPORTANT: Run in project's directory
            )

            # Prepare result
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }

            # Write result to file
            result_path = os.path.join(RESULT_DIR, f"{job_id}.json")
            with open(result_path, 'w') as f:
                json.dump(output, f)

            # Delete message from queue
            queue_client.delete_message(message)
            print(f"Finished job {job_id}")

        except Exception as e:
            print(f"Error processing message: {e}")

    time.sleep(POLL_INTERVAL_SECONDS)

Phase 4: Run & Test
Start the API Server:

# Make sure you are in the venv
source ~/llm_agent_backend/venv/bin/activate

# Run from inside ~/llm_agent_backend
uvicorn api:app --host 0.0.0.0 --port 8000

Start a Worker: Open a new SSH session to your VM.

# Navigate to the directory and activate venv
cd ~/llm_agent_backend
source venv/bin/activate

# Start the worker script
python worker.py

(To run multiple workers, simply open more SSH sessions and run the script again. For a real setup, use a process manager like systemd or supervisor.)

Test from your local machine:
Use a tool like curl or Postman to send a request to your public API endpoint.

curl -X POST "[http://your-dns-name.eastus.cloudapp.azure.com:8000/execute](http://your-dns-name.eastus.cloudapp.azure.com:8000/execute)" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "test-project",
    "command": "echo \"Hello from the VM!\" && ls -la"
}'

You should see the output from your command returned as a JSON response!
