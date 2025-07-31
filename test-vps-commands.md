# VPS API Test Commands

## Test API Status
```bash
curl http://165.22.42.162:8000
```

## Create Test Project
```bash
curl -X POST http://165.22.42.162:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-project",
    "files": {
      "src/App.tsx": "import React from \"react\";\n\nfunction App() {\n  return (\n    <div className=\"App\">\n      <h1>Hello VPS World!</h1>\n      <p>This is a test project running on VPS</p>\n    </div>\n  );\n}\n\nexport default App;"
    }
  }'
```

## List All Projects
```bash
curl http://165.22.42.162:8000/api/projects
```

## Start Development Server
```bash
curl -X POST http://165.22.42.162:8000/api/projects/test-project/start-preview
```

## Access Preview
After starting the dev server, access the preview at:
- http://165.22.42.162:3001 (or whatever port is returned)

## Update a File
```bash
curl -X PUT http://165.22.42.162:8000/api/projects/test-project/files/src/App.tsx \
  -H "Content-Type: application/json" \
  -d '{
    "content": "import React from \"react\";\n\nfunction App() {\n  return (\n    <div className=\"App\">\n      <h1>Updated VPS Project!</h1>\n      <p>This file was updated via API</p>\n      <p>Hot Module Replacement should work!</p>\n    </div>\n  );\n}\n\nexport default App;"
  }'
```

## Get Project Files
```bash
curl http://165.22.42.162:8000/api/projects/test-project/files
```

## Read Specific File
```bash
curl http://165.22.42.162:8000/api/projects/test-project/files/src/App.tsx
```