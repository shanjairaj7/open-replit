#!/usr/bin/env python3
"""
Test script to verify the complete error feedback system
"""

import requests
import json
import time

API_BASE = "http://206.189.229.208:8000/api"
TEST_PROJECT = "error-feedback-test-" + str(int(time.time()))

def test_create_project_with_errors():
    """Test creating a project with files that have errors"""
    print("🧪 Testing Error Feedback System")
    print("=" * 50)
    
    # 1. Create a test project
    test_project_name = TEST_PROJECT
    print(f"\n1️⃣ Creating test project: {test_project_name}")
    
    create_payload = {
        "name": test_project_name,
        "request": "Test project for error feedback"
    }
    
    response = requests.post(f"{API_BASE}/projects", json=create_payload)
    if response.status_code != 200:
        print(f"❌ Failed to create project: {response.text}")
        return
    
    project_data = response.json()
    project_id = project_data['project']['id']
    print(f"✅ Project created: {project_id}")
    
    # Check for initial errors (should be none)
    if 'python_errors' in project_data['project']:
        print(f"⚠️ Python errors on creation: {project_data['project']['python_errors']}")
    if 'typescript_errors' in project_data['project']:
        print(f"⚠️ TypeScript errors on creation: {project_data['project']['typescript_errors']}")
    
    # 2. Create a Python file with syntax errors
    print(f"\n2️⃣ Creating Python file with syntax errors...")
    
    python_content = """
def broken_function(
    # Missing closing parenthesis
    print("This will cause a syntax error"
    
import nonexistent_module

class BrokenClass:
    def __init__(self:
        # Another syntax error
        pass
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/backend/broken_file.py",
        json={"content": python_content}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File created: backend/broken_file.py")
        
        if result.get('python_errors'):
            print(f"🐍 Python errors detected:")
            print(result['python_errors'])
        else:
            print("❌ No Python errors detected (should have found syntax errors!)")
            
        if result.get('python_check_status', {}).get('executed'):
            print(f"🔍 Python check status: {result['python_check_status']}")
    else:
        print(f"❌ Failed to create Python file: {response.text}")
    
    # 3. Create a TypeScript file with type errors
    print(f"\n3️⃣ Creating TypeScript file with type errors...")
    
    typescript_content = """
// TypeScript file with errors
interface User {
    name: string;
    age: number;
}

const user: User = {
    name: "John",
    age: "thirty", // Type error: string is not assignable to number
    email: "john@example.com" // Error: Object literal may only specify known properties
};

function add(a: number, b: number): number {
    return a + b + "result"; // Type error: Type 'string' is not assignable to type 'number'
}

// Missing import
const component = <Button>Click me</Button>; // Error: Cannot find name 'Button'

// Undefined variable
console.log(undefinedVariable); // Error: Cannot find name 'undefinedVariable'

export default user;
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/frontend/src/broken_component.tsx",
        json={"content": typescript_content}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File created: frontend/src/broken_component.tsx")
        
        if result.get('typescript_errors'):
            print(f"📘 TypeScript errors detected:")
            print(result['typescript_errors'])
        else:
            print("❌ No TypeScript errors detected (should have found type errors!)")
            
        if result.get('typescript_check_status', {}).get('executed'):
            print(f"🔍 TypeScript check status: {result['typescript_check_status']}")
    else:
        print(f"❌ Failed to create TypeScript file: {response.text}")
    
    # 4. Create a valid file to ensure no false positives
    print(f"\n4️⃣ Creating valid TypeScript file...")
    
    valid_content = """
// Valid TypeScript file
export interface Todo {
    id: number;
    title: string;
    completed: boolean;
}

export const createTodo = (title: string): Todo => {
    return {
        id: Date.now(),
        title,
        completed: false
    };
};

export default createTodo;
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/frontend/src/valid_component.ts",
        json={"content": valid_content}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File created: frontend/src/valid_component.ts")
        
        if result.get('typescript_errors'):
            print(f"⚠️ TypeScript errors in valid file (unexpected!):")
            print(result['typescript_errors'])
        else:
            print("✅ No TypeScript errors in valid file (as expected)")
    
    # 5. Test updating an existing file
    print(f"\n5️⃣ Updating Python file to fix errors...")
    
    fixed_python = """
# Fixed Python file
def working_function():
    print("This is now valid Python")
    
import os  # Valid import

class WorkingClass:
    def __init__(self):
        pass
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/backend/broken_file.py",
        json={"content": fixed_python}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File updated: backend/broken_file.py")
        
        if result.get('python_errors'):
            print(f"⚠️ Python errors still present:")
            print(result['python_errors'])
        else:
            print("✅ No Python errors after fix (as expected)")
    
    print(f"\n✅ Error feedback system test completed!")
    print(f"📋 Test project: {project_id}")

if __name__ == "__main__":
    test_create_project_with_errors()