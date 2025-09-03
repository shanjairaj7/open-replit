# LLM Agent Backend API Endpoints

## Base URL
```
http://llm-agent-api.eastus.cloudapp.azure.com:8000
```

## 1. Project Sync
Sync a project from Azure storage to local cache.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/sync" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "force_refresh": false
}'
```

**Response:**
```json
{
    "project_id": "horizon-374-ef62c",
    "status": "synced",
    "local_path": "projects/horizon-374-ef62c",
    "has_frontend": true,
    "has_backend": true,
    "total_files": 74
}
```

## 2. Execute Terminal Commands

### Frontend Commands
```bash
# Install npm packages
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "npm install",
    "working_dir": "frontend"
}'

# Build frontend
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "npm run build",
    "working_dir": "frontend"
}'

# Run development server
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "npm run dev",
    "working_dir": "frontend"
}'
```

### Backend Commands
```bash
# Install Python packages
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "pip install -r requirements.txt",
    "working_dir": "backend"
}'

# Run backend server
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "python app.py",
    "working_dir": "backend"
}'

# Run tests
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "pytest",
    "working_dir": "backend"
}'
```

### Root Directory Commands
```bash
# List all files
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "ls -la",
    "working_dir": null
}'

# Git operations
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "git status",
    "working_dir": null
}'
```

**Response Format:**
```json
{
    "stdout": "command output here",
    "stderr": "error output if any",
    "return_code": 0,
    "working_directory": "projects/horizon-374-ef62c/frontend"
}
```

## 3. File Operations

### Read File
```bash
# Read frontend file
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/read" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "package.json",
    "working_dir": "frontend"
}'

# Read backend file
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/read" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "app.py",
    "working_dir": "backend"
}'

# Read from nested directories
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/read" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "src/components/Button.tsx",
    "working_dir": "frontend"
}'
```

**Response Format:**
```json
{
    "content": "file content here",
    "error": null,
    "exists": true,
    "size": 1739,
    "working_directory": "projects/horizon-374-ef62c/frontend",
    "file_path": "package.json",
    "last_modified": 1725349920.0,
    "is_binary": false
}
```

## 4. Project Information

### Get Project Info
```bash
curl "http://llm-agent-api.eastus.cloudapp.azure.com:8000/projects/horizon-374-ef62c/info"
```

**Response:**
```json
{
    "project_id": "horizon-374-ef62c",
    "cached": true,
    "has_frontend": true,
    "has_backend": true,
    "structure": {
        "frontend": ["package.json", "src", "public", "..."],
        "backend": ["app.py", "requirements.txt", "routes", "..."]
    }
}
```

## 5. Codebase Search (To Be Implemented)

### Search in Files
```bash
# Search for a term across all files
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/search" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "query": "useState",
    "working_dir": "frontend"
}'

# Search with regex
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/search" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "pattern": "function\\s+\\w+\\s*\\(",
    "regex": true,
    "working_dir": "frontend"
}'

# Search in specific file types
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/search" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "query": "import",
    "file_pattern": "*.py",
    "working_dir": "backend"
}'
```

**Proposed Response Format:**
```json
{
    "results": [
        {
            "file": "src/components/App.tsx",
            "line": 5,
            "content": "import { useState } from 'react';",
            "matches": ["useState"]
        }
    ],
    "total_matches": 15,
    "files_searched": 23
}
```

## 6. Health Check

```bash
curl "http://llm-agent-api.eastus.cloudapp.azure.com:8000/health"
```

**Response:**
```json
{
    "status": "healthy",
    "queue": "connected",
    "azure_storage": "connected"
}
```

## Common Parameters

### Project ID
- **Required**: Yes
- **Format**: String matching project folder name in Azure storage
- **Example**: `"horizon-374-ef62c"`

### Working Directory
- **Required**: No (defaults to project root)
- **Options**: `"frontend"`, `"backend"`, `null`
- **Purpose**: Specifies which subdirectory to operate in

### Command
- **Required**: Yes (for execute endpoint)
- **Format**: Any valid shell command
- **Examples**: `"npm install"`, `"python app.py"`, `"ls -la"`

### File Path
- **Required**: Yes (for file operations)
- **Format**: Relative path from working directory
- **Examples**: `"package.json"`, `"src/App.tsx"`, `"routes/auth.py"`

## Error Handling

All endpoints return appropriate HTTP status codes:
- **200**: Success
- **404**: Project or file not found
- **500**: Server error
- **408**: Request timeout (after 120 seconds)

Error response format:
```json
{
    "error": "Error message describing what went wrong"
}
```

## Performance Notes

- **Concurrent Requests**: System handles multiple requests simultaneously
- **Worker Pool**: 5 workers process jobs in parallel
- **Caching**: Projects cached locally after first download
- **Timeout**: Default 120 seconds for long operations
- **Node.js**: v20.19.4 installed for modern package support
- **Python**: v3.10 available for backend operations