#!/usr/bin/env python3
"""
Test script for new service action tags
Tests the new start_backend, start_frontend, restart_backend, restart_frontend actions
"""

import sys
import os
import requests
import json

# Add backend path for imports
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from test_groq_local import BoilerplatePersistentGroq

def test_service_actions():
    """Test the new service management action tags"""
    print("🧪 TESTING SERVICE ACTION TAGS")
    print("=" * 60)
    
    # Initialize the system with a test project
    system = BoilerplatePersistentGroq(
        api_key="test",
        project_name="test-service-actions",
        api_base_url="http://localhost:8000/api"
    )
    
    # Set a test project ID (use existing project if available)
    test_project_id = "want-crm-web-application-0808-163038"  # Use the latest project we know exists
    system.project_id = test_project_id
    
    print(f"🎯 Testing with project: {test_project_id}")
    print(f"🔗 API Base URL: {system.api_base_url}")
    
    # Test 1: Start Backend Service
    print("\n1️⃣ TESTING START_BACKEND ACTION")
    print("-" * 40)
    
    try:
        start_backend_action = {"type": "start_backend"}
        result = system._handle_start_backend_interrupt(start_backend_action)
        
        if result:
            print(f"✅ Start backend test PASSED")
            print(f"   Backend Port: {result.get('backend_port')}")
            print(f"   API URL: {result.get('api_url')}")
        else:
            print(f"❌ Start backend test FAILED - No result returned")
            
    except Exception as e:
        print(f"❌ Start backend test FAILED with exception: {e}")
    
    # Test 2: Start Frontend Service
    print("\n2️⃣ TESTING START_FRONTEND ACTION")
    print("-" * 40)
    
    try:
        start_frontend_action = {"type": "start_frontend"}
        result = system._handle_start_frontend_interrupt(start_frontend_action)
        
        if result:
            print(f"✅ Start frontend test PASSED")
            print(f"   Frontend Port: {result.get('frontend_port')}")
            print(f"   Frontend URL: {result.get('frontend_url')}")
        else:
            print(f"❌ Start frontend test FAILED - No result returned")
            
    except Exception as e:
        print(f"❌ Start frontend test FAILED with exception: {e}")
    
    # Test 3: Restart Backend Service
    print("\n3️⃣ TESTING RESTART_BACKEND ACTION")
    print("-" * 40)
    
    try:
        restart_backend_action = {"type": "restart_backend"}
        result = system._handle_restart_backend_interrupt(restart_backend_action)
        
        if result:
            print(f"✅ Restart backend test PASSED")
            print(f"   Backend Port: {result.get('backend_port')}")
            print(f"   API URL: {result.get('api_url')}")
        else:
            print(f"❌ Restart backend test FAILED - No result returned")
            
    except Exception as e:
        print(f"❌ Restart backend test FAILED with exception: {e}")
    
    # Test 4: Restart Frontend Service
    print("\n4️⃣ TESTING RESTART_FRONTEND ACTION")
    print("-" * 40)
    
    try:
        restart_frontend_action = {"type": "restart_frontend"}
        result = system._handle_restart_frontend_interrupt(restart_frontend_action)
        
        if result:
            print(f"✅ Restart frontend test PASSED")
            print(f"   Frontend Port: {result.get('frontend_port')}")
            print(f"   Frontend URL: {result.get('frontend_url')}")
        else:
            print(f"❌ Restart frontend test FAILED - No result returned")
            
    except Exception as e:
        print(f"❌ Restart frontend test FAILED with exception: {e}")
    
    # Test 5: Check Project Status
    print("\n5️⃣ CHECKING FINAL PROJECT STATUS")
    print("-" * 40)
    
    try:
        # Check project status via API
        status_url = f"{system.api_base_url}/projects/{test_project_id}"
        response = requests.get(status_url)
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Project status check PASSED")
            print(f"   Container Status: {status.get('container_status')}")
            print(f"   Frontend Port: {status.get('frontend_port')}")
            print(f"   Backend Port: {status.get('backend_port')}")
            
            if status.get('container_status') == 'running':
                print(f"🎉 SERVICES ARE RUNNING!")
                print(f"   🌐 Frontend: http://localhost:{status.get('frontend_port')}")
                print(f"   🚀 Backend: http://localhost:{status.get('backend_port')}")
                print(f"   📡 API: http://localhost:{status.get('backend_port')}/api")
            else:
                print(f"⚠️ Services are not running")
        else:
            print(f"❌ Project status check FAILED: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Project status check FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 SERVICE ACTION TESTS COMPLETED")
    print("=" * 60)

def test_api_endpoints_directly():
    """Test the new API endpoints directly"""
    print("\n🔧 TESTING API ENDPOINTS DIRECTLY")
    print("=" * 60)
    
    test_project_id = "want-crm-web-application-0808-163038"
    base_url = "http://localhost:8000/api"
    
    endpoints_to_test = [
        ("start-backend", "POST"),
        ("start-frontend", "POST"), 
        ("restart-backend", "POST"),
        ("restart-frontend", "POST")
    ]
    
    for endpoint, method in endpoints_to_test:
        print(f"\n🌐 Testing {method} /api/projects/{test_project_id}/{endpoint}")
        
        try:
            url = f"{base_url}/projects/{test_project_id}/{endpoint}"
            response = requests.post(url, timeout=30)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ SUCCESS: {json.dumps(result, indent=2)}")
            else:
                print(f"   ❌ FAILED: {response.text}")
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")

if __name__ == "__main__":
    print("🚀 STARTING SERVICE ACTION TAG TESTS")
    print()
    
    # Test via handler methods
    test_service_actions()
    
    # Test via API endpoints directly
    test_api_endpoints_directly()
    
    print("\n🎯 All tests completed!")