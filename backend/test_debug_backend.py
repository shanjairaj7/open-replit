#!/usr/bin/env python3
"""
Debug the backend startup issue
"""
import requests

fresh_project_id = "test-debug-backend"
base_url = "http://localhost:8000/api"

# Create project with simple backend
create_data = {
    "project_id": fresh_project_id,
    "files": {
        "backend/app.py": '''from fastapi import FastAPI

app = FastAPI(title="Test Backend")

@app.get("/")
def read_root():
    return {"message": "Hello from backend!"}
''',
        "backend/requirements.txt": """fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.10.0
python-multipart>=0.0.12
pyflakes>=3.2.0
mypy>=1.11.2
python-dotenv>=1.0.0"""
    }
}

try:
    # Cleanup
    requests.delete(f"{base_url}/projects/{fresh_project_id}")
    
    # Create project
    create_response = requests.post(f"{base_url}/projects", json=create_data)
    print(f"Create: {create_response.status_code}")
    
    # Setup
    setup_response = requests.post(f"{base_url}/projects/{fresh_project_id}/setup-environment")
    print(f"Setup: {setup_response.status_code}")
    if setup_response.status_code != 200:
        print(f"Setup error: {setup_response.text}")
    
    # Start backend with error details
    start_response = requests.post(f"{base_url}/projects/{fresh_project_id}/start-backend")
    print(f"Start: {start_response.status_code}")
    if start_response.status_code != 200:
        print(f"Start error: {start_response.text}")
    else:
        print(f"Success: {start_response.json()}")
        
except Exception as e:
    print(f"Exception: {e}")