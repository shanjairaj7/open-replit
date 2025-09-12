# Frontend & Backend Server Deployment Solutions

## Problem Statement
The current WebContainer-based frontend takes 5+ minutes to load with no caching. Need to run `npm run dev` on actual servers with public URLs for instant loading and better development experience.

## Current VM Infrastructure
- **VM**: llm-agent-api.eastus.cloudapp.azure.com (172.190.13.51)
- **Size**: Standard_B2s (2 vCPUs, 4 GB RAM)
- **Cost**: ~$30-35/month (running 24/7)
- **Subscription**: Microsoft Azure Sponsorship (c57910e6-96a8-4083-b94f-e1eb353cfb19)

## Solution Options

### Option 1: Railway.app (Recommended for Simplicity)
**Cost**: $5/month per project, auto-sleep when idle

**Implementation**:
```bash
# Each project deployment:
railway login
railway link project-name
railway up

# Automatic URLs:
# Frontend: https://project-name-frontend.up.railway.app
# Backend: https://project-name-backend.up.railway.app
```

**Benefits**:
- Instant deployment from git
- Auto-assigned public URLs  
- Hot reloading works
- Sleep when idle (cost-effective)
- Zero infrastructure management

**Costs for 10 projects**:
- Active projects: $5/month each
- Idle projects: $0/month
- Total: $25-50/month (depending on usage)

### Option 2: Current VM + Nginx Proxy
**Cost**: Current VM cost (~$30/month) + minimal

**Port Allocation**:
- FastAPI backends: 8001-8015
- Frontend dev servers: 3001-3015
- Nginx proxy: 8080 (public entry point)

**Nginx Configuration**:
```nginx
# /etc/nginx/sites-available/projects
server {
    listen 8080;
    server_name llm-agent-api.eastus.cloudapp.azure.com;

    # Project 1
    location /project-123/ {
        proxy_pass http://localhost:3001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /api/project-123/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Deployment Script**:
```bash
#!/bin/bash
# start_project.sh
PROJECT_ID=$1
FRONTEND_PORT=$2
BACKEND_PORT=$3

cd /home/azureuser/llm_agent_backend/projects/$PROJECT_ID

# Start backend
cd backend
PORT=$BACKEND_PORT uvicorn app:app --host 0.0.0.0 &

# Start frontend  
cd ../frontend
PORT=$FRONTEND_PORT npm run dev &

echo "Project $PROJECT_ID running:"
echo "Frontend: http://llm-agent-api.eastus.cloudapp.azure.com:8080/project-$PROJECT_ID/"
echo "Backend: http://llm-agent-api.eastus.cloudapp.azure.com:8080/api/project-$PROJECT_ID/"
```

**Resource Limits**:
- Current VM: 5-8 project pairs max
- Upgrade needed: Standard_D4s_v5 (4 vCPU, 16GB) for 10-15 pairs (~$100/month)

### Option 3: VM + Cloudflare Tunnel (Zero Extra Cost)
**Cost**: Current VM cost only

**Setup**:
```bash
# Install cloudflared on VM
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Create tunnel for each project
cloudflared tunnel create project-123
cloudflared tunnel route dns project-123 project-123.yourdomain.com

# Run tunnel
cloudflared tunnel --config tunnel.yml run project-123
```

**Benefits**:
- Custom domain names
- HTTPS automatic
- No port conflicts
- Zero additional cost

### Option 4: Modal.com Integration (Future-Proof)
**Cost**: ~$0.10-0.50 per project per day (only when used)

**Integration with existing codebase**:
```python
# Each project becomes a Modal app
@app.function()
@modal.web_app()
def frontend():
    # Serve built frontend
    return static_files_app

@app.function()  
@modal.asgi_app()
def backend():
    # FastAPI backend
    return fastapi_app
```

**URLs**:
- Frontend: `https://project-id--frontend.modal.run`
- Backend: `https://project-id--backend.modal.run`

## Recommended Implementation Plan

### Phase 1: Quick Win (VM + Nginx)
1. Set up nginx proxy on existing VM
2. Create project deployment scripts
3. Test with 2-3 projects
4. Monitor resource usage

### Phase 2: Scale Decision
Based on resource usage and costs:
- **If VM handles load**: Continue with VM approach
- **If VM struggles**: Upgrade VM or move to Railway
- **If costs too high**: Implement selective deployment

### Phase 3: Production Ready
1. Add SSL certificates (Let's Encrypt)
2. Implement auto-scaling logic
3. Add monitoring and logging
4. Create deployment automation

## Cost Comparison (10 Projects)

| Solution | Setup Cost | Monthly Cost | Scaling |
|----------|------------|--------------|---------|
| Railway | $0 | $25-50 | Automatic |
| VM + Nginx | $0 | $30-100 | Manual/Limited |
| VM + Cloudflare | $0 | $30 | Manual/Limited |
| Modal.com | $0 | $15-150 | Automatic |

## Next Steps
1. Check Azure sponsorship credit balance
2. Choose initial approach based on credits available
3. Implement Phase 1 solution
4. Test with sample projects
5. Monitor costs and performance

## Implementation Priority
**Immediate**: VM + Nginx (uses existing infrastructure)
**Short-term**: Railway for overflow projects
**Long-term**: Modal.com integration for production scale