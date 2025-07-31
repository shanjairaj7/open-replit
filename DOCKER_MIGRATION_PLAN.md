# Docker Migration Plan: Boilerplate System

## Overview
Transform the current Python-based boilerplate system into a containerized solution with FastAPI for creating and managing React projects.

## Current System Analysis
- **Current**: Python script runs locally, creates projects in local filesystem
- **Target**: Dockerized system with API endpoints for project management
- **Benefits**: Isolated environments, scalable, API-driven, consistent across different machines

## Architecture Design

### 1. Docker Container Structure
```
docker-container/
├── Dockerfile
├── docker-compose.yml
├── app/
│   ├── main.py (FastAPI app)
│   ├── models/
│   ├── api/
│   ├── services/
│   └── utils/
├── boilerplate/
│   └── shadcn-boilerplate/ (React template)
├── workspace/
│   └── projects/ (Generated projects)
└── requirements.txt
```

### 2. FastAPI Endpoints

#### Project Management
- `POST /projects` - Create new project from boilerplate
- `GET /projects` - List all projects
- `GET /projects/{project_id}` - Get project details
- `DELETE /projects/{project_id}` - Delete project

#### File Operations
- `GET /projects/{project_id}/files` - List project files
- `GET /projects/{project_id}/files/{file_path}` - Read file content
- `PUT /projects/{project_id}/files/{file_path}` - Create/update file
- `DELETE /projects/{project_id}/files/{file_path}` - Delete file

#### Build & Development
- `POST /projects/{project_id}/build` - Run npm build
- `POST /projects/{project_id}/install` - Run npm install
- `POST /projects/{project_id}/dev` - Start dev server
- `POST /projects/{project_id}/command` - Execute custom terminal command

#### AI Integration
- `POST /projects/{project_id}/generate` - Generate code using Groq AI
- `GET /projects/{project_id}/status` - Get project build status

### 3. Service Layer Architecture

#### ProjectService
- Clone boilerplate template
- Manage project lifecycle
- Handle file operations
- Track project metadata

#### BuildService
- Execute npm commands
- Handle build processes
- Manage development servers
- Stream command output

#### AIService
- Integrate with Groq API
- Process user requests
- Generate and update files
- Handle error fixing loops

## Implementation Phases

### Phase 1: Docker Setup ✓
1. Create Dockerfile with Node.js + Python environment
2. Set up docker-compose with volume mounting
3. Configure boilerplate copying mechanism
4. Test container builds and runs

### Phase 2: FastAPI Foundation
1. Create FastAPI application structure
2. Implement basic project CRUD endpoints
3. Add file manipulation endpoints
4. Set up proper error handling and logging

### Phase 3: Build System Integration
1. Implement command execution endpoints
2. Add npm install/build/dev functionality
3. Create process management for dev servers
4. Add real-time command output streaming

### Phase 4: AI Integration
1. Port existing Groq integration
2. Implement project generation endpoint
3. Add automated error fixing
4. Create conversation history management

### Phase 5: Advanced Features
1. WebSocket support for real-time updates
2. Project templates management
3. Multi-project development servers
4. Export/import functionality

## Docker Configuration

### Base Image Strategy
- Use `node:20-alpine` as base for lightweight container
- Install Python 3.11+ for AI integration
- Include git for version control operations

### Volume Management
```yaml
volumes:
  - ./workspace:/app/workspace  # Generated projects
  - ./boilerplate:/app/boilerplate  # Template source
  - node_modules:/app/node_modules  # Shared dependencies
```

### Environment Variables
```env
GROQ_API_KEY=<api_key>
NODE_ENV=development
WORKSPACE_PATH=/app/workspace
BOILERPLATE_PATH=/app/boilerplate
PORT=8000
```

### Networking
- FastAPI runs on port 8000
- Development servers use dynamic ports (3000-3999)
- Hot reloading through volume mounts

## Security Considerations
1. **File System Isolation**: Projects contained within workspace directory
2. **Command Sanitization**: Whitelist allowed npm/node commands
3. **Resource Limits**: CPU/memory limits for containers
4. **API Authentication**: JWT tokens for API access (future)
5. **Network Security**: Internal docker network for services

## Development Workflow

### Local Development
1. `docker-compose up -d` - Start services
2. `curl -X POST http://localhost:8000/projects -d '{request}'` - Create project
3. `curl http://localhost:8000/projects/{id}/dev` - Start dev server
4. Access project at dynamically assigned port

### Production Deployment
1. Multi-stage Docker build for optimization
2. External volume mounting for persistence
3. Load balancer for multiple instances
4. Health checks and monitoring

## Migration Steps

### Step 1: Container Setup
- [x] Create Dockerfile
- [x] Set up docker-compose
- [x] Configure boilerplate copying
- [x] Test basic container functionality

### Step 2: API Development
- [ ] FastAPI project structure
- [ ] Project management endpoints
- [ ] File operation endpoints
- [ ] Command execution system

### Step 3: Integration Testing
- [ ] End-to-end project creation
- [ ] Build system validation
- [ ] AI integration testing
- [ ] Performance optimization

### Step 4: Production Readiness
- [ ] Security hardening
- [ ] Monitoring setup
- [ ] Documentation
- [ ] Deployment automation

## Benefits of New Architecture

### Scalability
- Multiple projects in isolated containers
- Horizontal scaling of API instances
- Resource allocation per project

### Consistency
- Same environment across all deployments
- Reproducible builds and development
- Version-controlled boilerplate updates

### API-First Design
- Integration with web interfaces
- Support for multiple clients
- Real-time collaboration features

### Maintenance
- Centralized boilerplate management
- Automated updates and patches
- Simplified deployment process

## Next Steps
1. ✅ Create Docker setup
2. Implement FastAPI foundation
3. Port existing Python logic to services
4. Add comprehensive API testing
5. Deploy and validate system

---
*This plan will be updated as implementation progresses*