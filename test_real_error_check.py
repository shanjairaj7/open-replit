#!/usr/bin/env python3

# Test the actual _run_python_error_check function from local-api.py
import sys
import os
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/projects-api')

# Import all dependencies needed by local-api
from pathlib import Path
import json
import subprocess
import tempfile
import re

# Import the function
import importlib.util
spec = importlib.util.spec_from_file_location("local_api", "/Users/shanjairaj/Documents/forks/bolt.diy/projects-api/local-api.py")
local_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_api)

LocalProjectManager = local_api.LocalProjectManager

# Test the real function
project_manager = LocalProjectManager()
project_id = "want-crm-web-application-0808-152839"

print(f"🧪 Testing REAL _run_python_error_check function on project: {project_id}")
print("="*70)

result = project_manager._run_python_error_check(project_id)

print(f"✅ Success: {result['status']['success']}")
print(f"📋 Status: {result['status']}")
print(f"🔍 Errors:")
print(result['errors'])