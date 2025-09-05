# LLM Agent Backend API Endpoints

## Base URL
```
http://llm-agent-api.eastus.cloudapp.azure.com:8000
```

## Service Management
- **API Service**: Managed by systemd - `sudo systemctl status llm-api.service`
- **Worker Service**: Managed by systemd - `sudo systemctl status llm-workers.service`
- **Auto-restart**: Services automatically restart on failure

## 1. Health Check
Check API and infrastructure health status.

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

## 2. Project Sync
Sync a project from Azure storage to local cache.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/sync" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "force_refresh": false
}'
```

**Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID from Azure storage
    "force_refresh": false        // Optional: Force re-download even if cached (default: false)
}
```

**Response:**
```json
{
    "project_id": "horizon-374-ef62c",
    "status": "synced",
    "local_path": "projects/horizon-374-ef62c",
    "has_frontend": true,
    "has_backend": true,
    "total_files": 19022
}
```

## 3. File Operations

### 3.1 Create File ✅ WORKING
Create a new file in a project.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/create" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "test.txt",
    "content": "Hello World!",
    "working_dir": null,
    "overwrite": true
}'
```

**Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID
    "file_path": "string",        // Required: Path relative to working_dir
    "content": "string",          // Required: File content
    "working_dir": "string|null", // Optional: "frontend", "backend", or null for root
    "overwrite": false            // Optional: Allow overwriting existing file (default: false)
}
```

**Response:**
```json
{
    "success": true,
    "error": null,
    "working_directory": "projects/horizon-374-ef62c",
    "file_path": "test.txt",
    "size": 12,
    "last_modified": 1756899766.4909053
}
```

### 3.2 Read File ✅ WORKING
Read a file from a project.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/read" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "package.json",
    "working_dir": "frontend"
}'
```

**Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID
    "file_path": "string",        // Required: Path relative to working_dir
    "working_dir": "string|null"  // Optional: "frontend", "backend", or null for root
}
```

**Response:**
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

### 3.3 Update File ✅ WORKING
Update an existing file (or create if missing).

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/update" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "test.txt",
    "content": "Updated content",
    "working_dir": null,
    "create_if_missing": true
}'
```

**Request Payload:**
```json
{
    "project_id": "string",        // Required: Project ID
    "file_path": "string",         // Required: Path relative to working_dir
    "content": "string",           // Required: New file content
    "working_dir": "string|null",  // Optional: "frontend", "backend", or null for root
    "create_if_missing": true      // Optional: Create file if it doesn't exist (default: true)
}
```

**Response:**
```json
{
    "success": true,
    "error": null,
    "working_directory": "projects/horizon-374-ef62c",
    "file_path": "test.txt",
    "size": 15,
    "last_modified": 1756900835.9414382
}
```

### 3.4 Delete File ✅ WORKING
Delete a file from a project.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/file/delete" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "file_path": "test.txt",
    "working_dir": null
}'
```

**Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID
    "file_path": "string",        // Required: Path relative to working_dir
    "working_dir": "string|null"  // Optional: "frontend", "backend", or null for root
}
```

**Response:**
```json
{
    "success": true,
    "error": null,
    "working_directory": "projects/horizon-374-ef62c",
    "file_path": "test.txt",
    "deleted": true
}
```

## 4. Execute Terminal Commands

Execute shell commands in project directories.

```bash
curl -X POST "http://llm-agent-api.eastus.cloudapp.azure.com:8000/execute" \
-H "Content-Type: application/json" \
-d '{
    "project_id": "horizon-374-ef62c",
    "command": "ls -la",
    "working_dir": null
}'
```

**Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID
    "command": "string",          // Required: Shell command to execute
    "working_dir": "string|null"  // Optional: "frontend", "backend", or null for root
}
```

**Response:**
```json
{
    "stdout": "command output here",
    "stderr": "error output if any",
    "return_code": 0,
    "working_directory": "projects/horizon-374-ef62c"
}
```

### Example Commands

**Frontend Operations:**
```bash
# Install npm packages
{
    "command": "npm install",
    "working_dir": "frontend"
}

# Build frontend
{
    "command": "npm run build",
    "working_dir": "frontend"
}

# Run development server
{
    "command": "npm run dev",
    "working_dir": "frontend"
}
```

**Backend Operations:**
```bash
# Install Python packages
{
    "command": "pip install -r requirements.txt",
    "working_dir": "backend"
}

# Run backend server
{
    "command": "python app.py",
    "working_dir": "backend"
}

# Run tests
{
    "command": "pytest",
    "working_dir": "backend"
}
```

## 5. Project Information

Get information about a cached project.

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
        "frontend": ["package.json", "src", "public", "node_modules", "..."],
        "backend": ["app.py", "requirements.txt", "routes", "..."]
    }
}
```

## 6. Codebase Search (To Be Implemented)

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
```

**Proposed Request Payload:**
```json
{
    "project_id": "string",       // Required: Project ID
    "query": "string",           // Required: Search term
    "working_dir": "string|null", // Optional: Directory to search in
    "file_pattern": "string",     // Optional: File pattern (e.g., "*.py", "*.tsx")
    "regex": false               // Optional: Use regex pattern (default: false)
}
```

**Proposed Response:**
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

**Error Response Format:**
```json
{
    "error": "Error message describing what went wrong"
}
```

**File Operation Error Examples:**
```json
// File already exists
{
    "success": false,
    "error": "File test.txt already exists and overwrite is False",
    "working_directory": "projects/horizon-374-ef62c",
    "file_path": "test.txt",
    "exists": true
}

// Project not found
{
    "success": false,
    "error": "Project directory horizon-999-xxxxx not found",
    "working_directory": "projects/horizon-999-xxxxx",
    "file_path": "test.txt"
}
```

## Performance Notes

- **Concurrent Requests**: System handles multiple requests simultaneously
- **Worker Pool**: 3 workers process jobs in parallel (reduced from 5 for 8GB VM)
- **Caching**: Projects cached locally after first download
- **Timeout**: Default 120 seconds for long operations
- **Node.js**: v20.19.4 installed for modern package support
- **Python**: v3.10 available for backend operations
- **VM Specs**: 8GB RAM Azure VM (Standard B2s)
- **Response Time**: ~1-2 seconds for file operations when healthy

## API Documentation

- **Swagger UI**: http://llm-agent-api.eastus.cloudapp.azure.com:8000/docs
- **OpenAPI JSON**: http://llm-agent-api.eastus.cloudapp.azure.com:8000/openapi.json
- **ReDoc**: http://llm-agent-api.eastus.cloudapp.azure.com:8000/redoc

## Implementation Status

| Endpoint | Status | Notes |
|----------|--------|-------|
| Health Check | ✅ Working | Returns queue and storage status |
| Project Sync | ✅ Working | Downloads from Azure blob storage |
| File Create | ✅ Working | With overwrite protection |
| File Read | ✅ Working | Detects binary files |
| File Update | ✅ Working | Can create if missing |
| File Delete | ✅ Working | Returns deletion status |
| Execute Commands | ⚠️ Testing | May timeout on long operations |
| Project Info | ✅ Working | Shows cached project structure |
| Codebase Search | ❌ Not Implemented | Planned for future |
