#!/usr/bin/env python3
"""
Test Python error checking integration with VPS API
"""

import requests
import json

def test_python_error_checking():
    """Test that Python errors are detected and returned"""
    api_base = "http://206.189.229.208:8000/api"
    
    # Test project creation with Python errors
    print("🧪 Testing Python error checking integration...")
    
    # Create a test project with a backend file that has Pydantic regex error
    test_project_id = "python-error-test-project"
    
    # First delete if exists
    try:
        requests.delete(f"{api_base}/projects/{test_project_id}")
    except:
        pass
    
    # Create project with problematic Python file
    create_payload = {
        "project_id": test_project_id,
        "files": {
            "backend/models/test_model.py": '''from pydantic import BaseModel, Field
from typing import Optional

class TestModel(BaseModel):
    # This should trigger an error
    email: str = Field(regex=r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$")
    name: str = Field(..., min_length=1)
'''
        }
    }
    
    print(f"📤 Creating project with Python errors...")
    response = requests.post(f"{api_base}/projects", json=create_payload)
    
    if response.status_code == 200:
        project_data = response.json()
        print(f"✅ Project created successfully")
        
        # Check if Python errors were detected
        python_errors = project_data['project'].get('python_errors', '')
        if python_errors:
            print(f"🎯 SUCCESS: Python errors detected during creation:")
            print(python_errors)
        else:
            print(f"❌ FAIL: No Python errors detected (expected to find Pydantic regex error)")
    else:
        print(f"❌ Project creation failed: {response.status_code} - {response.text}")
        return
    
    # Test file update with Python errors
    print(f"\n📝 Testing file update with Python errors...")
    
    update_payload = {
        "content": '''from pydantic import BaseModel, Field

class UpdatedModel(BaseModel):
    # Another regex error
    phone: str = Field(regex=r"^\\+?[1-9]\\d{1,14}$")
    address: str
'''
    }
    
    response = requests.put(
        f"{api_base}/projects/{test_project_id}/files/backend/models/updated_model.py", 
        json=update_payload
    )
    
    if response.status_code == 200:
        update_result = response.json()
        print(f"✅ File updated successfully")
        
        # Check if Python errors were detected
        python_errors = update_result.get('python_errors', '')
        if python_errors:
            print(f"🎯 SUCCESS: Python errors detected during update:")
            print(python_errors)
        else:
            print(f"❌ FAIL: No Python errors detected in update (expected to find Pydantic regex error)")
    else:
        print(f"❌ File update failed: {response.status_code} - {response.text}")
    
    # Clean up
    print(f"\n🧹 Cleaning up test project...")
    try:
        requests.delete(f"{api_base}/projects/{test_project_id}")
        print(f"✅ Test project deleted")
    except:
        print(f"⚠️ Could not delete test project")

if __name__ == "__main__":
    test_python_error_checking()