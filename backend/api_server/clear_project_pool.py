#!/usr/bin/env python3
"""
Clear Project Pool Script
Removes all cached projects to force fresh clones with latest boilerplate
"""

import sys
import shutil
from pathlib import Path
from cloud_storage import get_cloud_storage
from project_pool_manager import get_pool_manager

def clear_project_pool():
    """Clear the entire project pool and cached boilerplates"""
    
    print("🗑️ Clearing project pool...")
    
    # Clear cached boilerplates
    cache_dir = Path("/tmp/boilerplate_cache")
    if cache_dir.exists():
        print(f"🗑️ Removing cached boilerplates: {cache_dir}")
        shutil.rmtree(cache_dir)
        print("✅ Cached boilerplates removed")
    
    # Clear Azure storage pool metadata
    try:
        cloud_storage = get_cloud_storage()
        if cloud_storage:
            # Delete the system pool metadata
            success = cloud_storage.delete_file("system", "project_pool.json")
            if success:
                print("✅ Pool metadata cleared from Azure storage")
            else:
                print("⚠️ Pool metadata not found or already cleared")
    except Exception as e:
        print(f"⚠️ Could not clear pool metadata: {e}")
    
    print("✅ Project pool cleared! Next project allocation will use fresh boilerplates.")

if __name__ == "__main__":
    clear_project_pool()