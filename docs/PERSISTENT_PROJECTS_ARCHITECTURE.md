# Persistent Multi-Project Architecture

## Overview
Single VPS hosting multiple persistent project codebases with isolated dev environments.

## Components

### 1. VPS Setup (Ubuntu 22.04)
```bash
# Initial setup
sudo apt update
sudo apt install docker.io docker-compose nginx certbot python3-certbot-nginx

# Directory structure
mkdir -p /opt/codebase-platform/{projects,api,nginx,scripts}
```

### 2. API Service (FastAPI)
```python
# /opt/codebase-platform/api/main.py
from fastapi import FastAPI, HTTPException
import docker
import aiofiles
import asyncio
from pathlib import Path

app = FastAPI()
docker_client = docker.from_env()

class ProjectManager:
    def __init__(self):
        self.base_path = Path("/opt/codebase-platform/projects")
        self.port_range = list(range(3000, 4000))
        self.used_ports = set()
    
    async def create_project(self, project_id: str, files: dict):
        project_path = self.base_path / project_id
        project_path.mkdir(exist_ok=True)
        
        # Write files
        for file_path, content in files.items():
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
        
        # Start container
        port = self._get_free_port()
        container = docker_client.containers.run(
            "node:18-alpine",
            command="sh -c 'npm install && npm run dev'",
            volumes={str(project_path): {'bind': '/app', 'mode': 'rw'}},
            working_dir="/app",
            ports={5173: port},
            environment={"PORT": "5173"},
            detach=True,
            name=f"project-{project_id}",
            restart_policy={"Name": "unless-stopped"}
        )
        
        # Update nginx
        await self._update_nginx(project_id, port)
        
        return {
            "project_id": project_id,
            "url": f"https://{project_id}.yourdomain.com",
            "port": port,
            "container_id": container.id
        }
    
    async def update_file(self, project_id: str, file_path: str, content: str):
        full_path = self.base_path / project_id / file_path
        async with aiofiles.open(full_path, 'w') as f:
            await f.write(content)
        # HMR will auto-reload
    
    async def _update_nginx(self, project_id: str, port: int):
        nginx_config = f"""
        server {{
            listen 80;
            server_name {project_id}.yourdomain.com;
            
            location / {{
                proxy_pass http://localhost:{port};
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection 'upgrade';
                proxy_set_header Host $host;
                proxy_cache_bypass $http_upgrade;
            }}
        }}
        """
        
        config_path = f"/etc/nginx/sites-enabled/{project_id}.conf"
        async with aiofiles.open(config_path, 'w') as f:
            await f.write(nginx_config)
        
        await asyncio.create_subprocess_shell("nginx -s reload")

@app.post("/projects")
async def create_project(project_data: dict):
    manager = ProjectManager()
    return await manager.create_project(
        project_data["project_id"],
        project_data["files"]
    )

@app.put("/projects/{project_id}/files/{file_path:path}")
async def update_file(project_id: str, file_path: str, content: dict):
    manager = ProjectManager()
    await manager.update_file(project_id, file_path, content["content"])
    return {"status": "updated"}
```

### 3. Docker Compose
```yaml
# /opt/codebase-platform/docker-compose.yml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    volumes:
      - ./projects:/opt/codebase-platform/projects
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
    restart: unless-stopped

  # Projects will be dynamically created as separate containers
```

### 4. Persistent Storage
```bash
# Backup script
#!/bin/bash
# /opt/codebase-platform/scripts/backup.sh

BACKUP_DIR="/backups/projects"
PROJECT_DIR="/opt/codebase-platform/projects"

# Daily backup
tar -czf "$BACKUP_DIR/projects-$(date +%Y%m%d).tar.gz" "$PROJECT_DIR"

# Keep last 30 days
find "$BACKUP_DIR" -name "projects-*.tar.gz" -mtime +30 -delete
```

### 5. Monitoring & Management
```python
# /opt/codebase-platform/api/monitor.py
@app.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    try:
        container = docker_client.containers.get(f"project-{project_id}")
        return {
            "status": container.status,
            "stats": container.stats(stream=False),
            "logs": container.logs(tail=100).decode()
        }
    except docker.errors.NotFound:
        raise HTTPException(404, "Project not found")

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    # Stop container
    try:
        container = docker_client.containers.get(f"project-{project_id}")
        container.remove(force=True)
    except docker.errors.NotFound:
        pass
    
    # Remove files (archive instead of delete)
    project_path = Path(f"/opt/codebase-platform/projects/{project_id}")
    archive_path = Path(f"/opt/codebase-platform/archives/{project_id}")
    shutil.move(str(project_path), str(archive_path))
    
    # Remove nginx config
    os.remove(f"/etc/nginx/sites-enabled/{project_id}.conf")
    await asyncio.create_subprocess_shell("nginx -s reload")
```

## Benefits

1. **Persistent Storage**: Projects stored on VPS filesystem
2. **Isolation**: Each project in its own Docker container
3. **Scalability**: Can handle 100+ projects on single VPS
4. **Hot Reload**: File changes trigger instant updates
5. **Easy Backup**: Simple filesystem backups
6. **Cost Effective**: ~$20-40/month for decent VPS

## Access Pattern

- API: `https://api.yourdomain.com`
- Project 1: `https://project1.yourdomain.com`
- Project 2: `https://project2.yourdomain.com`

## Resource Requirements

- **VPS**: 4 vCPU, 8GB RAM, 100GB SSD
- **Bandwidth**: ~10TB/month
- **Concurrent Projects**: ~50-100 depending on activity