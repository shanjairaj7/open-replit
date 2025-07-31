#!/usr/bin/env python3
"""
Test script to verify monorepo project creation works on VPS
"""
import requests
import json
import sys

VPS_URL = "http://206.189.229.208:8000"

def test_monorepo_creation():
    """Test creating a monorepo project with frontend and backend"""
    
    # Test 1: Check API status
    print("1. Checking API status...")
    response = requests.get(f"{VPS_URL}/")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API running: {data['message']}")
        print(f"   Frontend boilerplate exists: {data['frontend_boilerplate_exists']}")
        print(f"   Backend boilerplate exists: {data['backend_boilerplate_exists']}")
        
        if not data['frontend_boilerplate_exists'] or not data['backend_boilerplate_exists']:
            print("❌ Boilerplates missing - cannot proceed")
            return False
    else:
        print(f"❌ API not responding: {response.status_code}")
        return False
    
    # Test 2: Create a test project
    print("\n2. Creating test monorepo project...")
    project_data = {
        "project_id": "test-monorepo",
        "files": {
            "frontend/src/App.tsx": '''
import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Test Monorepo Frontend</h1>
      <p>This is the frontend part</p>
    </div>
  );
}

export default App;
            ''',
            "backend/services/test_service.py": '''
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class TestResponse(BaseModel):
    message: str
    service: str

@router.get("/test", response_model=TestResponse)
async def test_endpoint():
    return TestResponse(
        message="Hello from backend!",
        service="test-service"
    )
            '''
        }
    }
    
    response = requests.post(f"{VPS_URL}/api/projects", json=project_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Project created: {data['project']['id']}")
        print(f"   Type: {data['project']['type']}")
        print(f"   Frontend path: {data['project']['structure']['frontend']}")
        print(f"   Backend path: {data['project']['structure']['backend']}")
    else:
        print(f"❌ Project creation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    # Test 3: Check project files
    print("\n3. Checking project structure...")
    response = requests.get(f"{VPS_URL}/api/projects/test-monorepo/files")
    
    if response.status_code == 200:
        data = response.json()
        files = data['files']
        
        # Check for frontend files
        frontend_files = [f for f in files if f.startswith('frontend/')]
        backend_files = [f for f in files if f.startswith('backend/')]
        
        print(f"✅ Found {len(frontend_files)} frontend files")
        print(f"✅ Found {len(backend_files)} backend files")
        
        # Show some example files
        for file in frontend_files[:5]:
            print(f"   📁 {file}")
        print("   ...")
        for file in backend_files[:5]:
            print(f"   📁 {file}")
    else:
        print(f"❌ Could not list files: {response.status_code}")
        return False
    
    # Test 4: Read a specific file
    print("\n4. Testing file reading...")
    response = requests.get(f"{VPS_URL}/api/projects/test-monorepo/files/frontend/src/App.tsx")
    
    if response.status_code == 200:
        data = response.json()
        content = data['content']
        print("✅ Can read frontend file:")
        print(f"   First 100 chars: {content[:100]}...")
    else:
        print(f"❌ Could not read frontend file: {response.status_code}")
    
    response = requests.get(f"{VPS_URL}/api/projects/test-monorepo/files/backend/services/test_service.py")
    
    if response.status_code == 200:
        data = response.json()
        content = data['content']
        print("✅ Can read backend file:")
        print(f"   First 100 chars: {content[:100]}...")
    else:
        print(f"❌ Could not read backend file: {response.status_code}")
    
    print("\n✅ Monorepo creation test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_monorepo_creation()
    sys.exit(0 if success else 1)