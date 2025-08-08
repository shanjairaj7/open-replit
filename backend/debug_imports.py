#!/usr/bin/env python3
"""
Debug what imports are being detected
"""
import requests
import ast

fresh_project_id = "debug-imports-test"
base_url = "http://localhost:8000/api"

# Create project with simple backend - same as failing test
create_data = {
    "project_id": fresh_project_id,
    "files": {
        "backend/app.py": '''from fastapi import FastAPI

app = FastAPI(title="Test Backend")

@app.get("/")
def read_root():
    return {"message": "Hello from backend!"}
''',
        "backend/requirements.txt": "fastapi>=0.115.0\nuvicorn[standard]>=0.32.0"
    }
}

try:
    # Cleanup
    requests.delete(f"{base_url}/projects/{fresh_project_id}")
    
    # Create project
    create_response = requests.post(f"{base_url}/projects", json=create_data)
    print(f"✅ Create: {create_response.status_code}")
    
    # Now let's manually check what imports would be detected
    app_py_content = '''from fastapi import FastAPI

app = FastAPI(title="Test Backend")

@app.get("/")
def read_root():
    return {"message": "Hello from backend!"}
'''
    
    # Parse the AST to see what imports it finds
    tree = ast.parse(app_py_content)
    imports = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                imports.add(module)
    
    print(f"📋 Imports detected in app.py: {sorted(imports)}")
    
    # Now check what files are actually created in the project
    files_response = requests.get(f"{base_url}/projects/{fresh_project_id}/files")
    if files_response.status_code == 200:
        files_data = files_response.json()
        print(f"📁 Files in project: {files_data.get('files', [])}")
    
    # Try setup to see the detailed error
    setup_response = requests.post(f"{base_url}/projects/{fresh_project_id}/setup-environment")
    print(f"📦 Setup: {setup_response.status_code}")
    
finally:
    # Cleanup
    try:
        requests.delete(f"{base_url}/projects/{fresh_project_id}")
    except:
        pass