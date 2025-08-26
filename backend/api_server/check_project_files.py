#!/usr/bin/env python3
"""
Check what files actually exist in the project to validate our test
"""

import sys
sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')

from cloud_storage import get_cloud_storage

def check_project_files():
    """Check what files exist in the test project"""
    
    project_id = "horizon-541-0f2e2"
    
    print(f"🔍 Checking files in project: {project_id}")
    print("=" * 50)
    
    cloud_storage = get_cloud_storage()
    if not cloud_storage:
        print("❌ Cloud storage not available")
        return
    
    try:
        # List all files in the project
        all_files = cloud_storage.list_files(project_id)
        
        if all_files:
            print(f"📁 Found {len(all_files)} files in project:")
            print("-" * 30)
            
            for i, file_path in enumerate(sorted(all_files), 1):
                print(f"{i:2d}. {file_path}")
                
            print(f"\n🎯 Test files we tried to access:")
            test_files = [
                "frontend/src/App.jsx",
                "frontend/src/TodoList.jsx", 
                "backend/app.py",
                "backend/requirements.txt",
                "nonexistent/file.txt",
                "frontend/package.json"
            ]
            
            for test_file in test_files:
                exists = test_file in all_files
                status_icon = "✅" if exists else "❌"
                print(f"   {status_icon} {test_file}")
                
        else:
            print("❌ No files found in project or project doesn't exist")
            
    except Exception as e:
        print(f"💥 Error checking project files: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_project_files()