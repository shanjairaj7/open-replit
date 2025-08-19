#!/usr/bin/env python3
"""
Test diff parser integration with the local API
Tests actual file updates through the API using the backend boilerplate
"""
import os
import sys
import json
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diff_parser import DiffParser

# API configuration
API_BASE_URL = "http://localhost:8000"
PROJECT_ID = "todo-app-backend-user-0818-090839"  # Use existing project with auth files

def print_test_header(test_name):
    """Print a formatted test header"""
    print(f"\n{'='*60}")
    print(f" TEST: {test_name}")
    print(f"{'='*60}")

def print_result(success, message):
    """Print test result with color"""
    if success:
        print(f"✅ PASS: {message}")
    else:
        print(f"❌ FAIL: {message}")

def create_project_via_api(project_id, template="backend-boilerplate"):
    """Create a project through the API"""
    url = f"{API_BASE_URL}/api/projects"
    payload = {
        "projectId": project_id,
        "template": template
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json(), True
        else:
            print(f"Failed to create project {project_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return None, False
    except Exception as e:
        print(f"Error creating project: {e}")
        return None, False

def delete_project_via_api(project_id):
    """Delete a project through the API"""
    url = f"{API_BASE_URL}/api/projects/{project_id}"
    try:
        response = requests.delete(url)
        return response.status_code == 200
    except Exception as e:
        print(f"Error deleting project: {e}")
        return False

def read_file_via_api(project_id, file_path):
    """Read a file through the API"""
    url = f"{API_BASE_URL}/api/projects/{project_id}/files/{file_path}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('content', ''), True
        else:
            print(f"Failed to read {file_path}: {response.status_code}")
            return None, False
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, False

def update_file_via_api(project_id, file_path, content):
    """Update a file through the API"""
    url = f"{API_BASE_URL}/api/projects/{project_id}/files/{file_path}"
    try:
        response = requests.put(url, json={"content": content})
        if response.status_code == 200:
            return response.json(), True
        else:
            print(f"Failed to update {file_path}: {response.status_code}")
            print(f"Response: {response.text}")
            return None, False
    except Exception as e:
        print(f"Error updating file: {e}")
        return None, False

def test_auth_service_update():
    """Test updating the auth service file in backend boilerplate"""
    print_test_header("Auth Service Update via API")
    
    file_path = "backend/services/auth_service.py"
    
    # Read the current auth service file
    content, success = read_file_via_api(PROJECT_ID, file_path)
    if not success:
        print_result(False, f"Could not read {file_path}")
        return
    
    print(f"📖 Read {file_path}: {len(content)} characters")
    
    # Prepare update with search/replace
    update_content = """<diff>
------- SEARCH
router = APIRouter(prefix="/auth", tags=["authentication"])
=======
router = APIRouter(prefix="/auth/v2", tags=["authentication", "users"])
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
=======
    if not current_user.is_active:
        raise HTTPException(
            status_code=403, 
            detail="User account is inactive. Please contact support."
        )
+++++++ REPLACE
</diff>"""
    
    # Apply the diff parser
    final_content, successes, failures = DiffParser.process_update_file(content, update_content)
    
    print(f"📝 Diff processing results:")
    print(f"   Successes: {len(successes)}")
    for s in successes:
        print(f"     ✓ {s}")
    print(f"   Failures: {len(failures)}")
    for f in failures:
        print(f"     ✗ {f}")
    
    if len(successes) > 0:
        # Update the file via API
        result, success = update_file_via_api(PROJECT_ID, file_path, final_content)
        
        if success:
            print_result(True, "File updated successfully via API")
            
            # Verify the changes
            updated_content, read_success = read_file_via_api(PROJECT_ID, file_path)
            if read_success:
                has_v2 = "/auth/v2" in updated_content
                has_403 = "status_code=403" in updated_content
                print_result(has_v2, "Router prefix changed to /auth/v2")
                print_result(has_403, "Error code changed to 403")
        else:
            print_result(False, "Failed to update file via API")
    else:
        print_result(False, "No successful replacements to apply")

def test_model_update():
    """Test updating a model file"""
    print_test_header("Model File Update via API")
    
    file_path = "backend/models/auth_models.py"
    
    # Read the current model file
    content, success = read_file_via_api(PROJECT_ID, file_path)
    if not success:
        print_result(False, f"Could not read {file_path}")
        return
    
    print(f"📖 Read {file_path}: {len(content)} characters")
    
    # Add a new field to UserUpdate model
    update_content = """<diff>
------- SEARCH
class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
=======
class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\\+?[1-9]\\d{1,14}$')
    bio: Optional[str] = Field(None, max_length=500)
+++++++ REPLACE
</diff>"""
    
    # Apply the diff parser
    final_content, successes, failures = DiffParser.process_update_file(content, update_content)
    
    print(f"📝 Diff processing results:")
    print(f"   Successes: {len(successes)}")
    print(f"   Failures: {len(failures)}")
    
    if len(successes) > 0:
        # Update the file via API
        result, success = update_file_via_api(PROJECT_ID, file_path, final_content)
        
        if success:
            print_result(True, "Model file updated successfully")
            
            # Verify the changes
            updated_content, read_success = read_file_via_api(PROJECT_ID, file_path)
            if read_success:
                has_phone = "phone: Optional[str]" in updated_content
                has_bio = "bio: Optional[str]" in updated_content
                print_result(has_phone, "Phone field added to UserUpdate")
                print_result(has_bio, "Bio field added to UserUpdate")
        else:
            print_result(False, "Failed to update model file")
    else:
        print_result(False, "No successful replacements")

def test_failed_search():
    """Test handling of failed searches"""
    print_test_header("Failed Search Handling")
    
    file_path = "backend/app.py"
    
    # Read the app.py file
    content, success = read_file_via_api(PROJECT_ID, file_path)
    if not success:
        print_result(False, f"Could not read {file_path}")
        return
    
    print(f"📖 Read {file_path}: {len(content)} characters")
    
    # Try to update non-existent code
    update_content = """<diff>
------- SEARCH
def non_existent_function():
    return "This doesn't exist"
=======
def new_function():
    return "New code"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
app = FastAPI(title="Project Backend", version="1.0.0")
=======
app = FastAPI(
    title="Enhanced Backend API",
    version="2.0.0",
    description="Updated API with authentication"
)
+++++++ REPLACE
</diff>"""
    
    # Apply the diff parser
    final_content, successes, failures = DiffParser.process_update_file(content, update_content)
    
    print(f"📝 Diff processing results:")
    print(f"   Successes: {len(successes)}")
    for s in successes:
        print(f"     ✓ {s}")
    print(f"   Failures: {len(failures)}")
    for f in failures:
        print(f"     ✗ {f}")
    
    # Should have 1 success and 1 failure
    mixed_result = len(successes) == 1 and len(failures) == 1
    print_result(mixed_result, "Mixed success/failure handled correctly")
    
    if len(successes) > 0:
        # Apply only the successful changes
        result, success = update_file_via_api(PROJECT_ID, file_path, final_content)
        
        if success:
            print_result(True, "Partial update applied successfully")
            
            # Verify the successful change
            updated_content, read_success = read_file_via_api(PROJECT_ID, file_path)
            if read_success:
                has_enhanced = "Enhanced Backend API" in updated_content
                print_result(has_enhanced, "Successful change applied, failed search ignored")

def test_multiple_blocks():
    """Test multiple search/replace blocks in one update"""
    print_test_header("Multiple Block Updates")
    
    # Create a test file
    test_file_path = "backend/test_multi_update.py"
    initial_content = """# Test file for multiple updates
import os
import sys

DEBUG = False

class TestClass:
    def __init__(self):
        self.value = 1
    
    def method_a(self):
        return "A"
    
    def method_b(self):
        return "B"

def main():
    obj = TestClass()
    print(obj.method_a())
    print(obj.method_b())
"""
    
    # Create the file
    result, success = update_file_via_api(PROJECT_ID, test_file_path, initial_content)
    if not success:
        print_result(False, "Could not create test file")
        return
    
    print(f"📝 Created test file: {test_file_path}")
    
    # Apply multiple updates
    update_content = """<diff>
------- SEARCH
DEBUG = False
=======
DEBUG = True  # Enable debug mode
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    def __init__(self):
        self.value = 1
=======
    def __init__(self):
        self.value = 42  # Answer to everything
        self.name = "TestObject"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    def method_a(self):
        return "A"
=======
    def method_a(self):
        if DEBUG:
            print("Method A called")
        return "Enhanced A"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
def main():
    obj = TestClass()
    print(obj.method_a())
    print(obj.method_b())
=======
def main():
    obj = TestClass()
    print(f"Object name: {obj.name}")
    print(f"Method A: {obj.method_a()}")
    print(f"Method B: {obj.method_b()}")
    print(f"Debug mode: {DEBUG}")
+++++++ REPLACE
</diff>"""
    
    # Read current content
    content, _ = read_file_via_api(PROJECT_ID, test_file_path)
    
    # Apply the diff parser
    final_content, successes, failures = DiffParser.process_update_file(content, update_content)
    
    print(f"📝 Diff processing results:")
    print(f"   Successes: {len(successes)}")
    for s in successes:
        print(f"     ✓ {s}")
    print(f"   Failures: {len(failures)}")
    
    all_success = len(successes) == 4 and len(failures) == 0
    print_result(all_success, "All 4 blocks processed successfully")
    
    if len(successes) > 0:
        # Update the file
        result, success = update_file_via_api(PROJECT_ID, test_file_path, final_content)
        
        if success:
            print_result(True, "Multiple updates applied successfully")
            
            # Verify all changes
            updated_content, _ = read_file_via_api(PROJECT_ID, test_file_path)
            checks = [
                ("DEBUG = True" in updated_content, "DEBUG flag updated"),
                ("self.value = 42" in updated_content, "Value changed to 42"),
                ("self.name = \"TestObject\"" in updated_content, "Name property added"),
                ("Enhanced A" in updated_content, "Method A enhanced"),
                ("Object name:" in updated_content, "Main function updated")
            ]
            
            for check, message in checks:
                print_result(check, message)

def main():
    """Run all API integration tests"""
    print("\n" + "="*60)
    print(" DIFF PARSER API INTEGRATION TEST")
    print("="*60)
    print(f"\n📡 Testing with API at: {API_BASE_URL}")
    print(f"📦 Using project: {PROJECT_ID}")
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print("\n❌ API is not running at {API_BASE_URL}")
            print("Please start the local API first:")
            print("  cd projects-api && python local-api.py")
            return
    except:
        print(f"\n❌ Cannot connect to API at {API_BASE_URL}")
        print("Please start the local API first:")
        print("  cd projects-api && python local-api.py")
        return
    
    print("✅ API is running")
    
    # Use existing project with authentication files
    print(f"\n📦 Using existing project: {PROJECT_ID}")
    
    # Run tests
    test_auth_service_update()
    test_model_update()
    test_failed_search()
    test_multiple_blocks()
    
    print("\n" + "="*60)
    print(" API INTEGRATION TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()