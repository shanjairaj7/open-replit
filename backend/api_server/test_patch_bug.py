#!/usr/bin/env python3

"""
Test script to replicate the V4A patch bug that caused the horizon-419-11d64 failure
"""

import tempfile
import os
from pathlib import Path
from apply_patch import process_patch, open_file, write_file, remove_file

def test_problematic_patch():
    """Reproduce the exact patch that caused the bug"""
    
    # Create a test file that simulates the original app.py
    test_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import api_router  # Import auto-discovery router registry
from json_db import initialize_json_databases

# Initialize JSON databases AFTER volume is mounted
print("🗄️ Initializing JSON databases...")
initialize_json_databases()

# Create FastAPI app with dynamic configuration
app = FastAPI(
    title="Auto-generated FastAPI backend",
    description="Backend with auto-discovery routes",
    version="1.0.0"
)
"""
    
    # This is the exact problematic patch from the conversation
    problematic_patch = """*** Begin Patch
*** Update File: backend/app.py
@@ -78,9 +78,6 @@
     from fastapi import FastAPI
     from fastapi.middleware.cors import CORSMiddleware
     from routes import api_router  # Import auto-discovery router registry
-    from json_db import initialize_json_databases
-
-    # Initialize JSON databases AFTER volume is mounted
-    print("🗄️ Initializing JSON databases...")
-    initialize_json_databases()
     
     # Create FastAPI app with dynamic configuration
     app = FastAPI(
*** End Patch"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the test file
        test_file_path = os.path.join(temp_dir, 'app.py')
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        print("Original file content:")
        with open(test_file_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
        print()
        
        # Custom file handlers that work with temp directory
        def temp_open_file(path: str) -> str:
            # Convert backend/app.py to absolute path
            if path.startswith('backend/'):
                path = os.path.join(temp_dir, path[8:])  # Remove 'backend/' prefix
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        
        def temp_write_file(path: str, content: str) -> None:
            # Convert backend/app.py to absolute path
            if path.startswith('backend/'):
                path = os.path.join(temp_dir, path[8:])  # Remove 'backend/' prefix
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        def temp_remove_file(path: str) -> None:
            # Convert backend/app.py to absolute path
            if path.startswith('backend/'):
                path = os.path.join(temp_dir, path[8:])  # Remove 'backend/' prefix
            if os.path.exists(path):
                os.remove(path)
        
        print("Applying problematic patch...")
        try:
            result = process_patch(problematic_patch, temp_open_file, temp_write_file, temp_remove_file)
            print(f"Patch result: {result}")
        except Exception as e:
            print(f"Patch failed with error: {e}")
            print(f"Error type: {type(e).__name__}")
        
        print("\nFile content after patch attempt:")
        with open(test_file_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line.rstrip()}")

if __name__ == "__main__":
    test_problematic_patch()