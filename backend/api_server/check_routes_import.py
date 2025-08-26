#!/usr/bin/env python3
"""
Check if the routes module is properly structured
"""

import sys
sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')

from cloud_storage import get_cloud_storage

def check_routes_import():
    """Check the routes module structure"""
    
    project_id = "horizon-627-1228c"
    
    print(f"🔍 Checking routes structure for: {project_id}")
    print("=" * 50)
    
    cloud_storage = get_cloud_storage()
    
    # Check routes/__init__.py
    try:
        routes_init = cloud_storage.download_file(project_id, "backend/routes/__init__.py")
        if routes_init:
            print(f"📄 routes/__init__.py content:")
            print("-" * 30)
            print(routes_init)
            print("-" * 30)
        else:
            print("❌ routes/__init__.py not found or empty")
    except Exception as e:
        print(f"❌ Error reading routes/__init__.py: {e}")

if __name__ == "__main__":
    check_routes_import()