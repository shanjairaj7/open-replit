# Complete Setup Guide for Bolt.DIY

This guide will walk you through setting up the entire Bolt.DIY system from scratch.

## Prerequisites

- Ubuntu VM (20.04 or later) with public IP
- Azure Account with Storage service
- Modal.com account
- OpenRouter API key
- Python 3.8+ and Node.js 16+

## Step 1: Azure Storage Setup

### 1.1 Create Storage Account

1. Log into [Azure Portal](https://portal.azure.com)
2. Create a new Storage Account:
   ```
   - Resource Group: Create new or use existing
   - Storage account name: [unique-name]
   - Region: Choose closest to your users
   - Performance: Standard
   - Redundancy: LRS (Locally-redundant storage)
   ```

### 1.2 Create Containers

1. Navigate to your Storage Account
2. Go to "Containers" under "Data storage"
3. Create two containers:
   - `codebase-projects` (Private access)
   - `codebase-docs` (Private access)

### 1.3 Get Connection String

1. Go to "Access keys" under "Security + networking"
2. Copy the connection string from key1
3. Save it for the .env file

## Step 2: VM Setup for Terminal API

### 2.1 Create Ubuntu VM

#### Option A: Azure VM
```bash
# Using Azure CLI
az vm create \
  --resource-group myResourceGroup \
  --name bolt-diy-vm \
  --image Ubuntu2204 \
  --admin-username ubuntu \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

#### Option B: AWS EC2
```bash
# Launch Ubuntu 22.04 instance
# Instance type: t2.medium or larger
# Security group: Allow ports 22 (SSH) and 8000 (API)
```

#### Option C: DigitalOcean Droplet
```bash
# Create Ubuntu 22.04 droplet
# Size: 2GB RAM minimum
# Enable public IP
```

### 2.2 Configure VM

SSH into your VM and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv git curl -y

# Install Node.js (for npm commands)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Create project directory
mkdir -p ~/vm-api
cd ~/vm-api
```

### 2.3 Deploy VM API

Create `vm_api.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import asyncio
from typing import Optional

app = FastAPI()

class CommandRequest(BaseModel):
    project_id: str
    command: str
    cwd: Optional[str] = None

class FileRequest(BaseModel):
    project_id: str
    file_path: str
    content: str
    overwrite: bool = False

@app.post("/execute")
async def execute_command(request: CommandRequest):
    project_dir = f"/home/ubuntu/projects/{request.project_id}"

    # Ensure project directory exists
    os.makedirs(project_dir, exist_ok=True)

    # Set working directory
    cwd = request.cwd if request.cwd else project_dir

    try:
        # Execute command
        process = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )

        stdout, stderr = await process.communicate()

        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-file")
async def create_file(request: FileRequest):
    project_dir = f"/home/ubuntu/projects/{request.project_id}"
    file_path = os.path.join(project_dir, request.file_path)

    # Create directory if needed
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Check if file exists
    if os.path.exists(file_path) and not request.overwrite:
        raise HTTPException(status_code=409, detail="File already exists")

    # Write file
    with open(file_path, 'w') as f:
        f.write(request.content)

    return {"status": "success", "path": file_path}

@app.post("/update-file")
async def update_file(request: FileRequest):
    project_dir = f"/home/ubuntu/projects/{request.project_id}"
    file_path = os.path.join(project_dir, request.file_path)

    # Create directory if needed
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write file
    with open(file_path, 'w') as f:
        f.write(request.content)

    return {"status": "success", "path": file_path}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Create `requirements.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
```

Install and run:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API
python vm_api.py
```

### 2.4 Setup as System Service

Create systemd service:

```bash
sudo nano /etc/systemd/system/vm-api.service
```

Add:
```ini
[Unit]
Description=VM API for Bolt.DIY
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vm-api
Environment="PATH=/home/ubuntu/vm-api/venv/bin"
ExecStart=/home/ubuntu/vm-api/venv/bin/python vm_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable vm-api
sudo systemctl start vm-api
sudo systemctl status vm-api
```

### 2.5 Configure Firewall

```bash
# Allow SSH and API port
sudo ufw allow 22
sudo ufw allow 8000
sudo ufw enable
```

## Step 3: Modal.com Setup

### 3.1 Create Modal Account

1. Sign up at [modal.com](https://modal.com)
2. Install Modal CLI:
   ```bash
   pip install modal
   ```

### 3.2 Authenticate Modal

```bash
modal token new
# Follow the browser authentication flow
```

### 3.3 Create Modal Secrets

```bash
# Create secrets for your backend
modal secret create backend-api-secrets \
  OPENROUTER_API_KEY=your_key \
  AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

## Step 4: Local Development Setup

### 4.1 Clone Repository

```bash
git clone https://github.com/yourusername/bolt.diy.git
cd bolt.diy
```

### 4.2 Configure Environment

Create `.env` file:
```env
# LLM Configuration
OPENROUTER_API_KEY=your_openrouter_key_here
GROQ_API_KEY=your_groq_key_here  # Optional

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER=codebase-projects

# VM Configuration
VM_API_BASE_URL=http://YOUR_VM_IP:8000

# Modal Configuration
MODAL_APP_NAME=backend-api
MODAL_SECRET_NAME=backend-api-secrets

# Other Settings
SECRET_KEY=generate_a_random_secret_key_here
ENVIRONMENT=development
PORT=8000
```

### 4.3 Install Dependencies

Backend:
```bash
cd backend/api_server
pip install -r requirements.txt
```

Frontend:
```bash
cd ../../frontend
npm install
```

### 4.4 Test Configuration

Test Azure connection:
```python
# test_azure.py
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# List containers
for container in blob_service_client.list_containers():
    print(f"Container: {container.name}")
```

Test VM API:
```bash
curl http://YOUR_VM_IP:8000/health
# Should return: {"status":"healthy"}
```

## Step 5: Running the System

### 5.1 Start Backend API

```bash
cd backend/api_server
python app.py
# API runs on http://localhost:8000
```

### 5.2 Start Frontend

```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5173
```

### 5.3 Verify Everything Works

1. Open http://localhost:5173 in your browser
2. Try creating a simple project
3. Check Azure Storage for uploaded files
4. Run a terminal command to verify VM integration

## Step 6: Production Deployment

### 6.1 Deploy Backend to Cloud

#### Option A: Deploy to Azure App Service
```bash
az webapp up --name bolt-diy-api --runtime "PYTHON:3.9"
```

#### Option B: Deploy to Google Cloud Run
```bash
gcloud run deploy bolt-diy-api --source . --region us-central1
```

### 6.2 Deploy Frontend

#### Option A: Netlify
```bash
cd frontend
npm run build
netlify deploy --prod --dir=dist
```

#### Option B: Vercel
```bash
cd frontend
npm run build
vercel --prod
```

## Troubleshooting

### Common Issues

1. **Azure Connection Error**
   - Verify connection string is correct
   - Check firewall rules on storage account
   - Ensure containers exist

2. **VM API Not Accessible**
   - Check VM firewall settings
   - Verify VM public IP is correct
   - Ensure service is running: `sudo systemctl status vm-api`

3. **Modal Deployment Fails**
   - Check Modal authentication: `modal token info`
   - Verify secrets are created: `modal secret list`
   - Check Modal logs: `modal app logs`

4. **LLM API Errors**
   - Verify API keys are correct
   - Check API rate limits
   - Try fallback to different provider

### Logging

Enable detailed logging:
```python
# In app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check logs:
```bash
# VM API logs
journalctl -u vm-api -f

# Backend logs
tail -f backend.log

# Azure Storage logs
# Check Azure Portal > Storage Account > Monitoring > Logs
```

## Security Checklist

- [ ] All API keys in environment variables
- [ ] VM firewall configured correctly
- [ ] Azure Storage access keys rotated regularly
- [ ] HTTPS enabled for production
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] Secrets never logged
- [ ] Regular security updates on VM

## Performance Optimization

1. **Enable Caching**
   - Redis for frequently accessed data
   - CDN for static assets

2. **Optimize Azure Storage**
   - Use Azure CDN
   - Enable compression
   - Batch operations when possible

3. **Scale VM Resources**
   - Monitor CPU/Memory usage
   - Upgrade instance size if needed
   - Consider load balancing for multiple VMs

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Rotate API keys quarterly
- Clean up old projects from storage
- Monitor usage and costs
- Backup critical data

### Monitoring Setup
```bash
# Install monitoring tools
sudo apt install htop nethogs iotop -y

# Set up alerts for:
# - High CPU usage
# - Low disk space
# - API errors
# - Unusual traffic patterns
```

## Support Resources

- GitHub Issues: Report bugs and request features
- Documentation: `/backend/llm_docs/`
- Community Discord: [Join our Discord]
- Email Support: support@bolt-diy.com

## Next Steps

1. Test the complete flow with a sample project
2. Customize the boilerplate templates
3. Add your own LLM prompts and tools
4. Set up monitoring and alerts
5. Deploy to production