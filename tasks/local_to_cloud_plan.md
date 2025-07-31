# Local to Cloud Migration Plan

## 1. Docker System Setup

### 1.1 Directory Structure
```
/app
├── boilerplate/              # Shared boilerplate volume
│   └── shadcn-boilerplate/   # Base template for projects
├── projects/                 # Project storage volume
│   └── {project_name}/       # Individual project clones
```

### 1.2 Dockerfile Modifications
```dockerfile
# Add boilerplate volume and dependencies
FROM node:18-alpine

# Create app directory
WORKDIR /app

# Install Python dependencies
RUN apk add --no-cache python3 py3-pip
RUN pip install fastapi uvicorn requests

# Create volumes
VOLUME /app/boilerplate
VOLUME /app/projects

# Copy boilerplate template
COPY backend/boilerplate /app/boilerplate/shadcn-boilerplate

# Expose API port
EXPOSE 3000
```

### 1.3 docker-compose.yaml
```yaml
version: '3.8'

services:
  boilerplate:
    build: .
    volumes:
      - boilerplate_data:/app/boilerplate
    command: ["sh", "-c", "echo 'Boilerplate storage ready' && sleep infinity"]

  api:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - boilerplate_data:/app/boilerplate
      - projects_data:/app/projects
    command: ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "3000"]
    depends_on:
      - boilerplate

volumes:
  boilerplate_data:
  projects_data:
```

## 2. FastAPI Implementation

### 2.1 api.py
```python
from fastapi import FastAPI, HTTPException
import os
import shutil
import subprocess
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Models
class ProjectCreate(BaseModel):
    name: str

@app.post("/projects")
def create_project(project: ProjectCreate):
    """Create a new project by cloning boilerplate"""
    boilerplate_dir = "/app/boilerplate/shadcn-boilerplate"
    project_dir = f"/app/projects/{project.name}"
    
    if not os.path.exists(boilerplate_dir):
        raise HTTPException(status_code=404, detail="Boilerplate not found")
    
    if os.path.exists(project_dir):
        raise HTTPException(status_code=400, detail="Project already exists")
    
    try:
        shutil.copytree(boilerplate_dir, project_dir, ignore=shutil.ignore_patterns('node_modules', 'dist', '.git'))
        return {"status": "success", "project_dir": project_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
def list_projects():
    """List all available projects"""
    try:
        projects = os.listdir("/app/projects")
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 3. Python Script Modifications

### 3.1 test_groq_boilerplate_persistent.py (API Integration)
```python
import requests

class BoilerplatePersistentGroq:
    def __init__(self, api_key: str, project_name: str = None):
        self.api_base = "http://api:3000"
        # ... rest of initialization

    def _setup_project(self):
        """Create project via API"""
        response = requests.post(
            f"{self.api_base}/projects",
            json={"name": self.project_dir.name}
        )
        if response.status_code != 200:
            raise Exception(f"Project creation failed: {response.text}")
        print(f"✅ Project created at {self.project_dir.name}")

    def _update_file(self, file_path, content):
        """Update file via API"""
        response = requests.put(
            f"{self.api_base}/files/{self.project_dir.name}",
            json={"path": file_path, "content": content}
        )
        if response.status_code != 200:
            raise Exception(f"File update failed: {response.text}")
        print(f"✅ Updated {file_path}")
```

## 4. Implementation Steps

1. First, let's create the tasks directory and plan file
2. Next, I'll modify the Docker configuration
3. Then create the FastAPI service
4. Finally, update the Python script to use the API
