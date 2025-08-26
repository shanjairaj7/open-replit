# Streaming API File Tracking & Bulk File Retrieval API Documentation

## Overview

The streaming API tracks all files created or updated during a chat session. A bulk file content retrieval API allows fetching the actual content of these files efficiently.

## 1. File Tracking in Streaming Response

### How It Works

During streaming chat sessions (`POST /chat/stream`), the backend automatically tracks:
- **Files Created**: New files added during the session
- **Files Updated**: Existing files modified during the session

### Final Stream Response Structure

At the end of a streaming session, the final message includes file tracking data:

```json
{
  "type": "text",
  "content": "✅ Conversation completed successfully",
  "final_result": {
    // ... other completion data
  },
  "project_id": "your-project-id",
  "files_changed": {
    "files_created": [
      "frontend/src/TodoList.jsx",
      "backend/routes/tasks.py",
      "frontend/src/components/TaskItem.jsx"
    ],
    "files_updated": [
      "frontend/src/App.tsx",
      "backend/app.py",
      "frontend/package.json"
    ],
    "total_files": 6,
    "session_summary": "Created 3 new files, updated 3 existing files"
  }
}
```

### Files Changed Object

| Field | Type | Description |
|-------|------|-------------|
| `files_created` | `string[]` | Array of file paths that were created during the session |
| `files_updated` | `string[]` | Array of file paths that were updated during the session |
| `total_files` | `number` | Total count of files changed (created + updated) |
| `session_summary` | `string` | Human-readable summary of the changes |

## 2. Bulk File Content Retrieval API

### Endpoint

```
POST /projects/{project_id}/files/bulk
```

### Request Format

```json
{
  "project_id": "your-project-id",
  "file_paths": [
    "frontend/src/TodoList.jsx",
    "backend/routes/tasks.py",
    "frontend/src/App.tsx"
  ]
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | `string` | Yes | Project identifier (must match URL parameter) |
| `file_paths` | `string[]` | Yes | Array of file paths to retrieve content for |

### Response Format

#### Complete Response Example

```json
{
  "status": "partial",
  "project_id": "horizon-541-0f2e2",
  "files": [
    {
      "file_path": "frontend/package.json",
      "content": "{\n  \"name\": \"my-app\",\n  \"version\": \"1.0.0\",\n  \"dependencies\": {\n    \"react\": \"^18.0.0\",\n    \"react-dom\": \"^18.0.0\"\n  },\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vite build\"\n  }\n}",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "frontend/src/App.tsx",
      "content": "import React from 'react';\nimport './App.css';\n\nfunction App() {\n  return (\n    <div className=\"App\">\n      <header className=\"App-header\">\n        <h1>My Application</h1>\n      </header>\n    </div>\n  );\n}\n\nexport default App;",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "frontend/src/components/TodoList.jsx",
      "content": "import React, { useState } from 'react';\n\nconst TodoList = () => {\n  const [todos, setTodos] = useState([]);\n  const [inputValue, setInputValue] = useState('');\n\n  const addTodo = () => {\n    if (inputValue.trim()) {\n      setTodos([...todos, { id: Date.now(), text: inputValue, completed: false }]);\n      setInputValue('');\n    }\n  };\n\n  return (\n    <div className=\"todo-list\">\n      <h2>Todo List</h2>\n      <div className=\"todo-input\">\n        <input\n          type=\"text\"\n          value={inputValue}\n          onChange={(e) => setInputValue(e.target.value)}\n          placeholder=\"Add a new todo...\"\n        />\n        <button onClick={addTodo}>Add</button>\n      </div>\n      <ul>\n        {todos.map(todo => (\n          <li key={todo.id}>\n            {todo.text}\n          </li>\n        ))}\n      </ul>\n    </div>\n  );\n};\n\nexport default TodoList;",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "backend/app.py",
      "content": "\"\"\"\nFastAPI Backend Application\n\"\"\"\n\nimport os\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom routes import api_router\n\napp = FastAPI(\n    title=\"My Backend API\",\n    version=\"1.0.0\",\n    description=\"Auto-generated FastAPI backend\"\n)\n\n# CORS configuration\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=[\"*\"],\n    allow_credentials=True,\n    allow_methods=[\"*\"],\n    allow_headers=[\"*\"],\n)\n\n@app.get(\"/\")\ndef read_root():\n    return {\n        \"status\": \"Backend running\",\n        \"version\": \"1.0.0\"\n    }\n\n@app.get(\"/health\")\ndef health_check():\n    return {\n        \"status\": \"healthy\",\n        \"service\": \"Backend API\"\n    }\n\n# Include API routes\napp.include_router(api_router)\n\nif __name__ == \"__main__\":\n    import uvicorn\n    uvicorn.run(app, host=\"0.0.0.0\", port=8000)",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "backend/requirements.txt",
      "content": "fastapi==0.104.1\nuvicorn==0.24.0\npydantic==2.5.0\nsqlalchemy==2.0.23\npython-multipart==0.0.6\npython-dotenv==1.0.0\npasslib==1.7.4\npython-jose==3.3.0\nbcrypt==4.0.1\ncryptography==41.0.7",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "README.md",
      "content": "# My Project\n\nThis is an auto-generated full-stack application.\n\n## Frontend\n\nReact application with TypeScript.\n\n## Backend\n\nFastAPI backend with Python.\n\n## Getting Started\n\n### Frontend\n```bash\ncd frontend\nnpm install\nnpm run dev\n```\n\n### Backend\n```bash\ncd backend\npip install -r requirements.txt\npython app.py\n```",
      "error": null,
      "exists": true,
      "success": true
    },
    {
      "file_path": "frontend/src/nonexistent.js",
      "content": null,
      "error": "File not found",
      "exists": false,
      "success": false
    }
  ],
  "total_files": 7,
  "successful_files": 6,
  "failed_files": 1
}
```

#### File Structure Breakdown

The bulk API returns files from different project locations with their complete paths and content:

**Frontend Files** (React/TypeScript/JavaScript)
```json
{
  "file_path": "frontend/package.json",
  "content": "{\n  \"name\": \"my-app\",\n  \"version\": \"1.0.0\",\n  \"dependencies\": {\n    \"react\": \"^18.0.0\"\n  }\n}",
  "success": true
}
```

**Frontend Source Code** (nested in directories)
```json
{
  "file_path": "frontend/src/App.tsx",
  "content": "import React from 'react';\n\nfunction App() {\n  return <div>Hello World</div>;\n}",
  "success": true
}
```

**Deep Nested Components**
```json
{
  "file_path": "frontend/src/components/ui/Button.tsx",
  "content": "interface ButtonProps {\n  children: React.ReactNode;\n}\n\nexport const Button = ({ children }: ButtonProps) => {\n  return <button>{children}</button>;\n};",
  "success": true
}
```

**Backend Files** (Python/FastAPI)
```json
{
  "file_path": "backend/app.py",
  "content": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'message': 'Hello World'}",
  "success": true
}
```

**Backend Route Files** (organized in directories)
```json
{
  "file_path": "backend/routes/auth.py",
  "content": "from fastapi import APIRouter\n\nrouter = APIRouter(prefix='/auth')\n\n@router.post('/login')\ndef login():\n    return {'token': 'example'}",
  "success": true
}
```

**Configuration Files** (project root)
```json
{
  "file_path": "README.md",
  "content": "# My Project\n\nFull-stack application with React frontend and FastAPI backend.",
  "success": true
}
```

**Binary/Image Files** (handled as text when possible)
```json
{
  "file_path": "frontend/public/logo.svg",
  "content": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\">\n  <circle cx=\"50\" cy=\"50\" r=\"40\" fill=\"blue\"/>\n</svg>",
  "success": true
}
```

**Failed File Retrieval**
```json
{
  "file_path": "frontend/src/deleted-component.tsx",
  "content": null,
  "error": "File not found",
  "exists": false,
  "success": false
}
```

#### Directory Structure Examples

The API can retrieve files from any directory depth within a project:

**Root Level Files:**
- `README.md`
- `.gitignore`
- `package.json` (if project has root package.json)

**Frontend Directory Structure:**
- `frontend/package.json`
- `frontend/index.html`
- `frontend/vite.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/index.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/ui/Button.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/stores/userStore.ts`
- `frontend/public/favicon.ico`
- `frontend/public/assets/logo.png`

**Backend Directory Structure:**
- `backend/app.py`
- `backend/requirements.txt`
- `backend/routes/__init__.py`
- `backend/routes/auth.py`
- `backend/routes/users.py`
- `backend/models/user.py`
- `backend/utils/database.py`
- `backend/config/settings.py`

#### Content Handling by File Type

**JavaScript/TypeScript Files** (`.js`, `.ts`, `.jsx`, `.tsx`)
- Full source code with proper line breaks (`\n`)
- Preserves all formatting, indentation, and comments
- Handles imports, exports, and complex syntax

**JSON Files** (`.json`)
- Complete JSON structure with proper formatting
- Preserves nested objects and arrays
- Maintains proper escaping of quotes and special characters

**Python Files** (`.py`)
- Full Python source code with proper indentation
- Preserves docstrings, comments, and formatting
- Handles multi-line strings and complex structures

**Markdown Files** (`.md`)
- Complete markdown content with formatting
- Preserves headers, links, code blocks, and styling
- Line breaks maintained with `\n`

**Configuration Files** (`.env`, `.toml`, `.yaml`, `.yml`)
- Full configuration content
- Preserves comments and structure
- Environment variables and settings intact

**CSS/SCSS Files** (`.css`, `.scss`)
- Complete stylesheets with selectors and rules
- Preserves comments and formatting
- Media queries and complex CSS maintained

### Response Fields

#### Root Level

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"success"`, `"partial"`, or `"error"` |
| `project_id` | `string` | Project identifier |
| `files` | `FileContent[]` | Array of file content objects |
| `total_files` | `number` | Total number of files requested |
| `successful_files` | `number` | Number of files successfully retrieved |
| `failed_files` | `number` | Number of files that failed to retrieve |

#### FileContent Object

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `string` | Path of the file relative to project root |
| `content` | `string \| null` | File content as string, `null` if retrieval failed |
| `error` | `string \| null` | Error message if retrieval failed, `null` if successful |
| `exists` | `boolean` | Whether the file exists in the project |
| `success` | `boolean` | Whether the file content was successfully retrieved |

### Status Values

| Status | Description |
|--------|-------------|
| `"success"` | All requested files were successfully retrieved |
| `"partial"` | Some files were retrieved, some failed |
| `"error"` | No files could be retrieved |

## 3. Usage Flow

1. **Start Streaming Session**: Make a `POST /chat/stream` request
2. **Process Stream**: Handle streaming responses as normal
3. **Detect Completion**: Look for the final message containing `files_changed`
4. **Extract File Paths**: Get `files_created` and `files_updated` arrays
5. **Bulk Retrieve**: Use the bulk API to get actual file contents
6. **Log Contents**: Log the retrieved file contents as required

## 4. File Path Format

- All file paths are relative to the project root
- Examples: `frontend/src/App.tsx`, `backend/routes/auth.py`, `package.json`
- Paths use forward slashes regardless of operating system

## 5. Error Handling

The API handles various error scenarios:

- **File Not Found**: Returns `exists: false` and `error: "File not found"`
- **Access Denied**: Returns `exists: true` but `success: false` with appropriate error
- **Project Not Found**: Returns HTTP 404
- **Invalid Request**: Returns HTTP 400 with error details

## 6. Performance Notes

- The bulk API is more efficient than individual file requests
- Large files may take longer to retrieve
- The API has no built-in file size limits, but cloud storage limits apply
- Multiple file requests are processed concurrently for better performance