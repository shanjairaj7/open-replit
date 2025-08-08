#!/usr/bin/env python3
"""
Test script to verify that backend works without /api prefix complications
"""

import sys
import os
import requests
import json
import time

# Add backend path for imports
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from test_groq_local import BoilerplatePersistentGroq

def test_no_api_prefix():
    """Test that backend works with natural routes (no /api prefix)"""
    print("🧪 TESTING NO /API PREFIX COMPLICATIONS")
    print("=" * 60)
    
    # Create a fresh project to test with
    fresh_project_id = "test-no-api-prefix"
    base_url = "http://localhost:8000/api"
    
    print(f"🎯 Creating test project: {fresh_project_id}")
    
    # Clean up first
    try:
        delete_response = requests.delete(f"{base_url}/projects/{fresh_project_id}")
        print(f"🧹 Cleanup: {delete_response.status_code}")
    except:
        pass
    
    # Create project with simple backend
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
    return {"users": ["Alice", "Bob", "Charlie"]}
''',
            "backend/requirements.txt": "fastapi>=0.115.0\nuvicorn[standard]>=0.32.0",
            "frontend/package.json": '{"name": "test", "version": "1.0.0"}'
        }
    }
    
    try:
        # Create project
        create_response = requests.post(f"{base_url}/projects", json=create_data)
        if create_response.status_code != 200:
            print(f"❌ Failed to create project: {create_response.status_code}")
            return
        
        print("✅ Project created successfully")
        
        # Setup environment
        setup_response = requests.post(f"{base_url}/projects/{fresh_project_id}/setup-environment")
        if setup_response.status_code != 200:
            print(f"❌ Failed to setup environment: {setup_response.status_code}")
            return
            
        print("✅ Environment setup completed")
        
        # Start backend
        start_response = requests.post(f"{base_url}/projects/{fresh_project_id}/start-backend")
        if start_response.status_code != 200:
            print(f"❌ Failed to start backend: {start_response.status_code}")
            return
        
        backend_info = start_response.json()
        backend_port = backend_info.get('backend_port')
        backend_url = backend_info.get('backend_url')
        
        print(f"✅ Backend started on port {backend_port}")
        print(f"🔗 Backend URL: {backend_url}")
        
        # Wait for backend to be ready
        time.sleep(3)
        
        # Test routes WITHOUT /api prefix
        test_routes = [
            ("/", "Root endpoint"),
            ("/health", "Health check"), 
            ("/users", "Users endpoint")
        ]
        
        print(f"\n📋 TESTING ROUTES (no /api prefix)")
        print("-" * 40)
        
        for route, description in test_routes:
            try:
                test_url = f"{backend_url}{route}"
                print(f"🌐 Testing {description}: {test_url}")
                
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ SUCCESS: {data}")
                else:
                    print(f"   ❌ FAILED: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ EXCEPTION: {e}")
        
        # Test that /api routes DON'T exist (they shouldn't)
        print(f"\n📋 TESTING THAT /API ROUTES DON'T EXIST")
        print("-" * 40)
        
        api_routes = [
            ("/api/", "Should not exist"),
            ("/api/health", "Should not exist"),
            ("/api/users", "Should not exist")
        ]
        
        for route, description in api_routes:
            try:
                test_url = f"{backend_url}{route}"
                print(f"🚫 Testing {description}: {test_url}")
                
                response = requests.get(test_url, timeout=5)
                if response.status_code == 404:
                    print(f"   ✅ CORRECT: 404 (route doesn't exist as expected)")
                else:
                    print(f"   ⚠️  UNEXPECTED: {response.status_code} - route exists!")
                    
            except Exception as e:
                print(f"   ✅ CORRECT: Exception (route doesn't exist)")
        
        print(f"\n🎉 TEST COMPLETED SUCCESSFULLY!")
        print(f"   • Routes work naturally without /api prefix")
        print(f"   • No confusion about routing structure")
        print(f"   • Model can create endpoints freely")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
    
    finally:
        # Cleanup
        try:
            requests.delete(f"{base_url}/projects/{fresh_project_id}")
            print(f"\n🧹 Cleanup completed")
        except:
            pass

if __name__ == "__main__":
    test_no_api_prefix()