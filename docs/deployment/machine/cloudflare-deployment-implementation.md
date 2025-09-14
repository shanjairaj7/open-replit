# Cloudflare Pages On-Demand Frontend Deployment

## Overview

Implementation plan for adding on-demand Cloudflare Pages deployment functionality to the VM Central API. This will allow deploying project frontends to Cloudflare's global edge network through a simple API call.

## System Integration

### Current VM API Structure
- **Base API**: FastAPI server at `http://llm-agent-api.eastus.cloudapp.azure.com:8000`
- **Project Management**: Projects cached locally in `/projects/{project_id}/frontend/`
- **Job Queue**: Azure Queue Storage for async task processing
- **Worker Pool**: 5 background workers processing deployment tasks

### Deployment Architecture
```
API Request → Job Queue → Worker Process → Wrangler CLI → Cloudflare Pages
```

## Implementation Plan

### 1. API Endpoint Design

**New Endpoint**: `POST /deploy/cloudflare`

**Request Model**:
```python
class CloudflareDeployRequest(BaseModel):
    project_id: str
    project_name: str  # Cloudflare project name (must be unique)
    environment: Optional[str] = "production"  # or "staging"
    env_vars: Optional[Dict[str, str]] = {}  # Environment variables
    force_rebuild: Optional[bool] = False
```

**Response Format**:
```json
{
  "status": "success",
  "deployment_url": "https://project-name.pages.dev",
  "preview_url": "https://abc123.project-name.pages.dev",
  "build_id": "deployment-uuid",
  "logs": "Build and deployment logs"
}
```

### 2. VM Configuration Requirements

**Environment Variables** (to be set on VM):
```bash
CLOUDFLARE_API_TOKEN=your-global-api-token
CLOUDFLARE_ACCOUNT_ID=your-account-id
```

**Dependencies Installation**:
```bash
# Node.js and npm (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Wrangler CLI (globally)
npm install -g wrangler
```

### 3. Worker Implementation

**New Job Type**: `deploy_cloudflare`

**Worker Process Logic**:
1. Verify project exists locally in `/projects/{project_id}/frontend/`
2. Create temporary build directory
3. Copy frontend files to temp directory  
4. Generate/update `.env` file with provided environment variables
5. Run build process (if package.json exists)
6. Execute Wrangler deployment command
7. Parse deployment response for URLs
8. Clean up temporary files
9. Return deployment status and URLs

### 4. Wrangler Integration

**Deployment Command Pattern**:
```python
# Basic deployment
subprocess.run([
    'npx', 'wrangler', 'pages', 'deploy', './build',
    '--project-name', project_name,
    '--branch', environment
], env=deployment_env)

# With compatibility date
subprocess.run([
    'npx', 'wrangler', 'pages', 'deploy', './build',
    '--project-name', project_name,
    '--compatibility-date', '2024-01-01'
], env=deployment_env)
```

**Environment Setup**:
```python
deployment_env = os.environ.copy()
deployment_env.update({
    'CLOUDFLARE_API_TOKEN': cf_api_token,
    'CLOUDFLARE_ACCOUNT_ID': cf_account_id,
    'NODE_ENV': 'production'
})
```

### 5. Environment Variables Management

**Frontend Environment File Generation**:
```python
def create_env_file(project_path: str, env_vars: Dict[str, str]):
    """Create .env file for frontend build"""
    env_content = []
    
    # Add default variables
    env_content.append("NODE_ENV=production")
    
    # Add custom variables
    for key, value in env_vars.items():
        # Ensure React variables start with REACT_APP_
        if not key.startswith(('REACT_APP_', 'VITE_', 'NEXT_PUBLIC_')):
            key = f"REACT_APP_{key}"
        env_content.append(f"{key}={value}")
    
    env_file_path = os.path.join(project_path, '.env.production')
    with open(env_file_path, 'w') as f:
        f.write('\n'.join(env_content))
```

### 6. Build Process Integration

**Smart Build Detection**:
```python
def detect_build_command(project_path: str) -> List[str]:
    """Detect appropriate build command based on project structure"""
    package_json_path = os.path.join(project_path, 'package.json')
    
    if os.path.exists(package_json_path):
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        # Check for build script
        scripts = package_data.get('scripts', {})
        if 'build' in scripts:
            return ['npm', 'run', 'build']
        elif 'vite' in package_data.get('devDependencies', {}):
            return ['npx', 'vite', 'build']
    
    # Default: assume static files
    return []  # No build needed
```

### 7. Error Handling

**Common Error Scenarios**:
- Project not found locally
- Build process failure
- Cloudflare API authentication issues
- Wrangler CLI not available
- Deployment quota exceeded

**Error Response Format**:
```json
{
  "status": "error",
  "error_type": "build_failed",
  "message": "Frontend build process failed",
  "logs": "Build error logs...",
  "suggestions": [
    "Check package.json build script",
    "Verify environment variables",
    "Review build logs for syntax errors"
  ]
}
```

### 8. Security Considerations

**API Token Security**:
- Store Cloudflare API token as environment variable on VM
- Never log API tokens in deployment logs
- Use least-privilege API token with Pages-only permissions

**Project Isolation**:
- Each deployment runs in isolated temporary directory
- Clean up all temporary files after deployment
- Prevent access to other projects during deployment

### 9. Testing Strategy

**Test Cases**:
1. Deploy React app with build process
2. Deploy static HTML/CSS/JS files
3. Deploy with custom environment variables
4. Handle deployment failures gracefully
5. Test with different project structures (Vite, Next.js, etc.)

**Test Endpoint**: `POST /deploy/cloudflare/test`
- Deploy test project to verify configuration
- Return deployment status without affecting production

### 10. Implementation Steps

1. **Phase 1**: Add API endpoint and request models
2. **Phase 2**: Implement basic worker job processing  
3. **Phase 3**: Add Wrangler CLI integration
4. **Phase 4**: Implement environment variable handling
5. **Phase 5**: Add build process detection and execution
6. **Phase 6**: Comprehensive error handling and logging
7. **Phase 7**: Testing and optimization

### 11. Cost and Limitations

**Cloudflare Pages Limits** (Free Tier):
- 500 builds per month
- 20,000 files per deployment
- 25 MB file size limit
- 1 concurrent build

**VM Resource Usage**:
- Node.js builds consume CPU and memory
- Temporary disk space needed for build artifacts
- Network bandwidth for uploading to Cloudflare

### 12. Future Enhancements

- **Custom Domains**: Support for custom domain configuration
- **Deployment History**: Track and manage previous deployments
- **Rollback Functionality**: Ability to revert to previous deployments
- **Build Caching**: Cache node_modules and build artifacts
- **Multi-Environment**: Support for dev, staging, production environments
- **Webhooks**: Trigger deployments from external events

## Configuration Example

**VM Setup Script**:
```bash
#!/bin/bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Wrangler globally
npm install -g wrangler

# Set environment variables
echo "export CLOUDFLARE_API_TOKEN=your-token" >> ~/.bashrc
echo "export CLOUDFLARE_ACCOUNT_ID=your-account-id" >> ~/.bashrc
source ~/.bashrc

# Verify installation
wrangler --version
```

**Usage Example**:
```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/deploy/cloudflare" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-react-app-001",
    "project_name": "my-awesome-app",
    "environment": "production",
    "env_vars": {
      "API_URL": "https://api.myapp.com",
      "FEATURE_FLAG_NEW_UI": "true"
    }
  }'
```

This implementation provides a robust, scalable solution for on-demand frontend deployment to Cloudflare Pages through the existing VM infrastructure.