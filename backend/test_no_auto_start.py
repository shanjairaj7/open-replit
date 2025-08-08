#!/usr/bin/env python3
"""
Test script to verify that projects setup environment without starting services
"""

import sys
import os
import requests
import json
import time

# Add backend path for imports
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from test_groq_local import BoilerplatePersistentGroq

def test_no_auto_start():
    """Test that environment setup doesn't automatically start services"""
    print("🧪 TESTING NO AUTO-START BEHAVIOR")
    print("=" * 60)
    
    # Initialize the system
    system = BoilerplatePersistentGroq(
        api_key="test",
        project_name="test-no-auto-start",
        api_base_url="http://localhost:8000/api"
    )
    
    test_project_id = system.project_id
    print(f"🎯 Testing with project: {test_project_id}")
    
    # Test 1: Call the new setup_project_environment method
    print("\n1️⃣ TESTING ENVIRONMENT SETUP (should NOT start services)")
    print("-" * 50)
    
    try:
        setup_success = system.setup_project_environment()
        if setup_success:
            print("✅ Environment setup completed successfully")
        else:
            print("❌ Environment setup failed")
    except Exception as e:
        print(f"❌ Environment setup failed with exception: {e}")
    
    # Test 2: Check if any services are actually running
    print("\n2️⃣ CHECKING IF SERVICES ARE RUNNING (should be NONE)")
    print("-" * 50)
    
    try:
        # Check project status
        status_url = f"{system.api_base_url}/projects/{test_project_id}"
        response = requests.get(status_url)
        
        if response.status_code == 200:
            status = response.json()
            container_status = status.get('container_status', 'unknown')
            frontend_port = status.get('frontend_port')
            backend_port = status.get('backend_port')
            
            print(f"📊 Project Status Check:")
            print(f"   Container Status: {container_status}")
            print(f"   Frontend Port: {frontend_port}")
            print(f"   Backend Port: {backend_port}")
            
            if container_status == 'running':
                print("❌ FAILED: Services are running when they shouldn't be!")
                print("   This means auto-start is still happening")
            else:
                print("✅ PASSED: No services are running (as expected)")
                print("   Environment setup worked correctly")
                
        else:
            print(f"❌ Could not check project status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
    
    # Test 3: Test the new API endpoint directly
    print("\n3️⃣ TESTING NEW API ENDPOINT DIRECTLY")
    print("-" * 50)
    
    try:
        # Create a fresh project for this test
        fresh_project_id = "fresh-test-setup"
        
        # First delete if exists
        try:
            delete_response = requests.delete(f"{system.api_base_url}/projects/{fresh_project_id}")
            print(f"Cleanup: {delete_response.status_code}")
        except:
            pass
        
        # Create project
        create_data = {
            "project_id": fresh_project_id,
            "files": {
                "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                "frontend/package.json": '{"name": "test", "dependencies": {"react": "^18.0.0"}}'
            }
        }
        
        create_response = requests.post(f"{system.api_base_url}/projects", json=create_data)
        if create_response.status_code == 200:
            print("✅ Fresh project created")
            
            # Wait a moment
            time.sleep(2)
            
            # Call setup-environment endpoint
            setup_url = f"{system.api_base_url}/projects/{fresh_project_id}/setup-environment"
            setup_response = requests.post(setup_url)
            
            if setup_response.status_code == 200:
                setup_result = setup_response.json()
                print("✅ Setup endpoint worked:")
                print(f"   Status: {setup_result.get('status')}")
                print(f"   Backend Ready: {setup_result.get('backend_ready')}")
                print(f"   Frontend Ready: {setup_result.get('frontend_ready')}")
                
                # Check if services started (they shouldn't have)
                status_response = requests.get(f"{system.api_base_url}/projects/{fresh_project_id}")
                if status_response.status_code == 200:
                    final_status = status_response.json()
                    if final_status.get('container_status') == 'running':
                        print("❌ FAILED: Services started automatically!")
                    else:
                        print("✅ PASSED: No services started automatically")
                        
            else:
                print(f"❌ Setup endpoint failed: {setup_response.status_code} - {setup_response.text}")
        else:
            print(f"❌ Could not create fresh project: {create_response.status_code}")
            
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 NO AUTO-START TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_no_auto_start()