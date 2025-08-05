#!/usr/bin/env python3
"""
Complete Monorepo Testing Suite
Tests all phases of the monorepo implementation with real use cases
"""
import requests
import json
import sys
import time
from typing import Dict, Any

# VPS Configuration
VPS_URL = "http://206.189.229.208:8000"
PROJECT_ID = "task-manager-app"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_test(test_name: str):
    print(f"\n{Colors.CYAN}📋 {test_name}{Colors.END}")
    print("-" * 50)

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def make_request(method: str, url: str, data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
    """Make HTTP request with error handling"""
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=timeout)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, timeout=timeout)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, timeout=timeout)
        
        return {
            'status_code': response.status_code,
            'success': response.status_code < 400,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'url': url
        }
    except requests.exceptions.Timeout:
        return {'status_code': 408, 'success': False, 'data': 'Request timeout', 'url': url}
    except requests.exceptions.RequestException as e:
        return {'status_code': 500, 'success': False, 'data': str(e), 'url': url}
    except json.JSONDecodeError:
        return {'status_code': response.status_code, 'success': response.status_code < 400, 'data': response.text, 'url': url}

def test_api_status():
    """Test 1: Check API Status"""
    print_test("API Status Check")
    
    response = make_request('GET', f"{VPS_URL}/")
    
    if response['success']:
        data = response['data']
        print_success(f"API running: {data.get('message', 'Unknown')}")
        print_info(f"Frontend boilerplate exists: {data.get('frontend_boilerplate_exists', False)}")
        print_info(f"Backend boilerplate exists: {data.get('backend_boilerplate_exists', False)}")
        
        if not data.get('frontend_boilerplate_exists') or not data.get('backend_boilerplate_exists'):
            print_error("⚠️ Some boilerplates missing!")
            return False
        return True
    else:
        print_error(f"API not responding: {response['status_code']} - {response['data']}")
        return False

def test_project_creation():
    """Test 2: Create Task Manager Monorepo Project"""
    print_test("Create Task Manager Monorepo Project")
    
    # Task Manager App Files
    project_files = {
        "frontend/src/components/TaskList.tsx": '''import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Task {
  id: number;
  title: string;
  completed: boolean;
}

export const TaskList = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch("/api/tasks");
      const data = await response.json();
      setTasks(data.tasks);
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = async (id: number) => {
    try {
      await fetch(`/api/tasks/${id}/toggle`, { method: "POST" });
      fetchTasks();
    } catch (error) {
      console.error("Failed to toggle task:", error);
    }
  };

  if (loading) return <div>Loading tasks...</div>;

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Task Manager</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {tasks.map((task) => (
            <div key={task.id} className="flex items-center justify-between p-2 border rounded">
              <span className={task.completed ? "line-through text-gray-500" : ""}>
                {task.title}
              </span>
              <Button 
                onClick={() => toggleTask(task.id)}
                variant={task.completed ? "outline" : "default"}
                size="sm"
              >
                {task.completed ? "Undo" : "Complete"}
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};''',
        "backend/services/task_service.py": '''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# In-memory storage (replace with database in real app)
tasks_db = [
    {"id": 1, "title": "Setup project structure", "completed": True, "created_at": "2025-01-01T10:00:00"},
    {"id": 2, "title": "Create task API endpoints", "completed": False, "created_at": "2025-01-01T11:00:00"},
    {"id": 3, "title": "Build React frontend", "completed": False, "created_at": "2025-01-01T12:00:00"},
]

class Task(BaseModel):
    id: int
    title: str
    completed: bool
    created_at: str

class CreateTaskRequest(BaseModel):
    title: str

class TaskListResponse(BaseModel):
    tasks: List[Task]
    total: int

@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks():
    """Get all tasks"""
    return TaskListResponse(
        tasks=tasks_db,
        total=len(tasks_db)
    )

@router.post("/tasks", response_model=Task)
async def create_task(request: CreateTaskRequest):
    """Create a new task"""
    new_id = max([task["id"] for task in tasks_db], default=0) + 1
    new_task = {
        "id": new_id,
        "title": request.title,
        "completed": False,
        "created_at": datetime.now().isoformat()
    }
    tasks_db.append(new_task)
    return Task(**new_task)

@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int):
    """Toggle task completion status"""
    for task in tasks_db:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            return {"message": "Task toggled successfully", "task": task}
    raise HTTPException(status_code=404, detail="Task not found")

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """Delete a task"""
    global tasks_db
    tasks_db = [task for task in tasks_db if task["id"] != task_id]
    return {"message": "Task deleted successfully"}'''
    }
    
    # Create project
    response = make_request('POST', f"{VPS_URL}/api/projects", {
        "project_id": PROJECT_ID,
        "files": project_files
    })
    
    if response['success']:
        data = response['data']
        project_info = data.get('project', {})
        print_success(f"Project created: {project_info.get('id')}")
        print_info(f"Type: {project_info.get('type')}")
        print_info(f"Frontend path: {project_info.get('structure', {}).get('frontend', 'N/A')}")
        print_info(f"Backend path: {project_info.get('structure', {}).get('backend', 'N/A')}")
        return True
    else:
        print_error(f"Project creation failed: {response['status_code']} - {response['data']}")
        return False

def test_project_structure():
    """Test 3: Verify Project Structure"""
    print_test("Verify Project Structure")
    
    response = make_request('GET', f"{VPS_URL}/api/projects/{PROJECT_ID}/files")
    
    if response['success']:
        data = response['data']
        files = data.get('files', [])
        
        frontend_files = [f for f in files if f.startswith('frontend/')]
        backend_files = [f for f in files if f.startswith('backend/')]
        
        print_success(f"Found {len(frontend_files)} frontend files")
        print_success(f"Found {len(backend_files)} backend files")
        
        # Check for specific files
        custom_files = {
            'frontend/src/components/TaskList.tsx': 'Frontend TaskList component',
            'backend/services/task_service.py': 'Backend task service',
            'frontend/src/components/ui/button.tsx': 'shadcn/ui Button component',
            'backend/services/health_service.py': 'Backend health service'
        }
        
        for file_path, description in custom_files.items():
            if file_path in files:
                print_success(f"✓ {description}")
            else:
                print_error(f"✗ Missing: {description}")
        
        return len(frontend_files) > 0 and len(backend_files) > 0
    else:
        print_error(f"Could not list files: {response['status_code']} - {response['data']}")
        return False

def test_file_operations():
    """Test 4: File CRUD Operations"""
    print_test("File CRUD Operations")
    
    # Test 1: Read frontend component
    response = make_request('GET', f"{VPS_URL}/api/projects/{PROJECT_ID}/files/frontend/src/components/TaskList.tsx")
    if response['success']:
        content = response['data'].get('content', '')
        if 'TaskList' in content and 'React' in content:
            print_success("✓ Can read custom frontend component")
        else:
            print_error("✗ Frontend component content incorrect")
    else:
        print_error(f"✗ Could not read frontend file: {response['status_code']}")
    
    # Test 2: Read backend service
    response = make_request('GET', f"{VPS_URL}/api/projects/{PROJECT_ID}/files/backend/services/task_service.py")
    if response['success']:
        content = response['data'].get('content', '')
        if ('fastapi' in content.lower() or 'FastAPI' in content) and 'tasks' in content:
            print_success("✓ Can read custom backend service")
        else:
            print_error("✗ Backend service content incorrect")
            print_info(f"Content preview: {content[:200]}...")
    else:
        print_error(f"✗ Could not read backend file: {response['status_code']}")
    
    # Test 3: Create new file
    new_component = '''import React from "react";
import { Alert, AlertDescription } from "./ui/alert";

export const StatusAlert = ({ message, type = "info" }) => {
  return (
    <Alert className={`mb-4 ${type === 'error' ? 'border-red-500' : 'border-blue-500'}`}>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
};'''
    
    response = make_request('PUT', f"{VPS_URL}/api/projects/{PROJECT_ID}/files/frontend/src/components/StatusAlert.tsx", {
        "content": new_component
    })
    
    if response['success']:
        print_success("✓ Can create new frontend file")
    else:
        print_error(f"✗ Could not create new file: {response['status_code']}")
    
    # Test 4: Update existing file
    updated_app = '''import React from "react";
import { TaskList } from "./components/TaskList";
import { StatusAlert } from "./components/StatusAlert";
import "./App.css";

function App() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-900">
          Task Management App
        </h1>
        <StatusAlert message="Welcome to the Task Manager!" type="info" />
        <TaskList />
      </div>
    </div>
  );
}

export default App;'''
    
    response = make_request('PUT', f"{VPS_URL}/api/projects/{PROJECT_ID}/files/frontend/src/App.tsx", {
        "content": updated_app
    })
    
    if response['success']:
        print_success("✓ Can update existing frontend file")
        return True
    else:
        print_error(f"✗ Could not update file: {response['status_code']}")
        return False

def test_frontend_preview():
    """Test 5: Frontend Preview"""
    print_test("Frontend Preview Test")
    
    # Start preview
    print_info("Starting frontend preview...")
    response = make_request('POST', f"{VPS_URL}/api/projects/{PROJECT_ID}/start-preview", timeout=60)
    
    if response['success']:
        data = response['data']
        port = data.get('port')
        preview_url = data.get('preview_url', f"http://206.189.229.208:{port}")
        
        print_success(f"Preview started on port {port}")
        print_info(f"Preview URL: {preview_url}")
        
        # Wait for container to fully start
        print_info("Waiting for container to initialize...")
        time.sleep(10)
        
        # Test if preview is accessible
        try:
            preview_response = requests.get(preview_url.replace('YOUR_VPS_IP', '206.189.229.208'), timeout=10)
            if preview_response.status_code == 200:
                print_success("✓ Frontend preview is accessible")
                preview_success = True
            else:
                print_error(f"✗ Preview not accessible: {preview_response.status_code}")
                preview_success = False
        except Exception as e:
            print_error(f"✗ Could not access preview: {str(e)}")
            preview_success = False
        
        # Stop preview
        print_info("Stopping preview...")
        stop_response = make_request('POST', f"{VPS_URL}/api/projects/{PROJECT_ID}/stop-preview")
        if stop_response['success']:
            print_success("✓ Preview stopped successfully")
        
        return preview_success
    else:
        print_error(f"Could not start preview: {response['status_code']} - {response['data']}")
        return False

def test_project_management():
    """Test 6: Project Management Operations"""
    print_test("Project Management")
    
    # List all projects
    response = make_request('GET', f"{VPS_URL}/api/projects")
    if response['success']:
        data = response['data']
        projects = data.get('projects', [])
        print_success(f"Found {len(projects)} projects")
        
        # Find our project
        our_project = next((p for p in projects if p.get('id') == PROJECT_ID), None)
        if our_project:
            print_success(f"✓ Project '{PROJECT_ID}' found in list")
            print_info(f"  Status: {our_project.get('status')}")
            print_info(f"  Type: {our_project.get('type')}")
        else:
            print_error(f"✗ Project '{PROJECT_ID}' not found in list")
    
    # Get specific project details
    response = make_request('GET', f"{VPS_URL}/api/projects/{PROJECT_ID}")
    if response['success']:
        data = response['data']
        print_success("✓ Can retrieve project details")
        print_info(f"  Container status: {data.get('container_status')}")
        return True
    else:
        print_error(f"✗ Could not get project details: {response['status_code']}")
        return False

def cleanup_test_project():
    """Cleanup: Archive the test project"""
    print_test("Cleanup - Archive Test Project")
    
    response = make_request('DELETE', f"{VPS_URL}/api/projects/{PROJECT_ID}")
    
    if response['success']:
        data = response['data']
        print_success(f"Project archived successfully")
        print_info(f"Archive path: {data.get('archive_path')}")
        return True
    else:
        print_error(f"Could not archive project: {response['status_code']} - {response['data']}")
        return False

def main():
    """Run all tests"""
    print_header("MONOREPO TESTING SUITE")
    print(f"{Colors.BOLD}Testing VPS: {VPS_URL}{Colors.END}")
    print(f"{Colors.BOLD}Project ID: {PROJECT_ID}{Colors.END}")
    
    tests = [
        ("API Status Check", test_api_status),
        ("Project Creation", test_project_creation),
        ("Project Structure", test_project_structure),
        ("File Operations", test_file_operations),
        ("Frontend Preview", test_frontend_preview),
        ("Project Management", test_project_management),
        ("Cleanup", cleanup_test_project)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print_header("TEST RESULTS SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{test_name:<25} {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! Monorepo system is working perfectly!{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ {total - passed} tests failed. Check the logs above.{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())