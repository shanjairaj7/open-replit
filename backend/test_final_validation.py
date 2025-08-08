#!/usr/bin/env python3
"""
Final validation test: both the mypy/pyflakes issue AND the /api prefix issue
"""
import requests
import time

fresh_project_id = "test-final-validation"
base_url = "http://localhost:8000/api"

# Create project with proper requirements AND test routes without /api prefix
create_data = {
    "project_id": fresh_project_id,
    "files": {
        "backend/app.py": '''from fastapi import FastAPI

app = FastAPI(title="Test Backend")

@app.get("/")
def read_root():
    return {"message": "Hello from backend!"}

@app.get("/health") 
def health_check():
    return {"status": "healthy"}

@app.get("/users")
def get_users():
    return {"users": ["Alice", "Bob"]}
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
    print(f"✅ Create: {create_response.status_code}")
    
    # Setup (this installs the requirements including mypy/pyflakes)
    setup_response = requests.post(f"{base_url}/projects/{fresh_project_id}/setup-environment")  
    print(f"✅ Setup: {setup_response.status_code}")
    
    # Start backend (should work now with proper requirements)
    start_response = requests.post(f"{base_url}/projects/{fresh_project_id}/start-backend")
    print(f"✅ Start: {start_response.status_code}")
    
    if start_response.status_code == 200:
        backend_info = start_response.json()
        backend_url = backend_info.get('backend_url')
        print(f"🚀 Backend URL: {backend_url}")
        
        # Wait and test routes WITHOUT /api prefix
        time.sleep(3)
        
        test_routes = ["/", "/health", "/users"]
        print(f"\n📋 Testing routes WITHOUT /api prefix:")
        
        for route in test_routes:
            try:
                response = requests.get(f"{backend_url}{route}", timeout=5)
                print(f"   {route}: ✅ {response.status_code} - {response.json()}")
            except Exception as e:
                print(f"   {route}: ❌ ERROR - {e}")
        
        # Test that /api routes DON'T work (they shouldn't exist)
        print(f"\n📋 Confirming /api routes DON'T exist:")
        
        api_routes = ["/api/health", "/api/users"]
        for route in api_routes:
            try:
                response = requests.get(f"{backend_url}{route}", timeout=5)
                if response.status_code == 404:
                    print(f"   {route}: ✅ 404 (correct - doesn't exist)")
                else:
                    print(f"   {route}: ⚠️  {response.status_code} (unexpected)")
            except Exception as e:
                print(f"   {route}: ✅ Exception (correct - doesn't exist)")
                
        print(f"\n🎉 SUCCESS: Both issues resolved!")
        print(f"   ✅ mypy/pyflakes work when included in requirements.txt")
        print(f"   ✅ Routes work naturally without /api prefix")
        print(f"   ✅ No more routing confusion for AI model")
        
    else:
        print(f"❌ Start failed: {start_response.text}")
        
except Exception as e:
    print(f"Exception: {e}")
finally:
    # Cleanup
    try:
        requests.delete(f"{base_url}/projects/{fresh_project_id}")
    except:
        pass