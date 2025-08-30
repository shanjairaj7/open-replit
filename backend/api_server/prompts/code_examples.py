json_db = """
from json_db import db, get_db, JsonDBSession
from fastapi import Depends

# CRUD patterns using JsonDB
def create_item(data: dict):
    return db.insert('table_name', data)  # Auto-generates ID and timestamp

def get_item(item_id: int):
    return db.find_one('table_name', id=item_id)

def update_item(item_id: int, updates: dict):
    return db.update_one('table_name', {'id': item_id}, updates)

# FastAPI endpoint pattern
@router.post("/items")
def create_item_endpoint(data: ItemCreate, db_session: JsonDBSession = Depends(get_db)):
    if db_session.db.exists("items", name=data.name):
        raise HTTPException(status_code=400, detail="Item already exists")
    return db_session.db.insert("items", data.dict())
"""

toast_error_handling = """
// Frontend API calls with proper error handling
import { toast } from 'sonner'

try {
  const response = await fetch('/api/endpoint')
  if (response.status === 200) {
    const data = await response.json()
    toast.success('Operation successful')
    return data
  } else if (response.status === 400) {
    const error = await response.json()
    toast.error(error.detail || 'Validation failed')
  }
} catch (error) {
  toast.error('Network error - please check connection')
}
"""

tailwind_design_system = """
@import "tailwindcss";

@theme {
  --color-primary: hsl(220 14% 96%);     /* Actual HSL values */
  --color-background: hsl(0 0% 100%);   /* NOT bg-background */
  --font-sans: Inter, system-ui, sans-serif;
}
"""

json_database_initialization = """
# EXACTLY how to initialize JSON databases in app.py for Modal deployment:

# Step 1: Add this function to app.py (import json_db first)
from json_db import create_tables

def initialize_json_databases():
    '''
    Initialize all JSON database tables for this application
    MUST be called inside @modal.asgi_app() function after volume mount
    '''
    # List all the tables your app needs
    table_names = [
        "users",      # For authentication
        "todos",      # Example: todo app
        "projects",   # Example: project management
        "contacts",   # Example: CRM app
        # Add your specific app tables here
    ]
    
    # Create tables using the json_db.py create_tables function
    create_tables(table_names)
    print(f"✅ JSON database initialized with tables: {table_names}")

# Step 2: Call it INSIDE @modal.asgi_app() function like this:
@modal.asgi_app()
def fastapi_app():
    # ... existing FastAPI setup code ...
    
    # CRITICAL: Initialize database AFTER volume is mounted
    initialize_json_databases()
    
    # ... rest of FastAPI setup ...
    return app
"""

json_database_complete_example = """
# Complete Working Example from backend-boilerplate-clone:
@modal.asgi_app()
def fastapi_app():
    # Import dependencies inside function for Modal compatibility
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from routes import api_router
    from json_db import create_tables  # Import create_tables function
    
    # Initialize JSON database with your app's tables
    def initialize_json_databases():
        table_names = ["users", "todos", "projects"]  # Your app's tables
        create_tables(table_names)
        print(f"✅ JSON database initialized: {table_names}")
    
    # Call database initialization
    initialize_json_databases()
    
    # Create FastAPI app
    app = FastAPI(title=APP_TITLE, version="1.0.0")
    
    # ... rest of setup ...
    return app
"""

modal_deployment_errors = """
# ❌ WRONG - This will fail during Modal deployment:
from json_db import create_tables
create_tables(["users"])  # Module-level call fails

# ✅ CORRECT - This works:
@modal.asgi_app()
def fastapi_app():
    from json_db import create_tables
    
    def initialize_json_databases():
        create_tables(["users"])  # Called after volume mount
    
    initialize_json_databases()  # Inside function only
"""

import_management_examples = """
# Modal deployment import patterns - CRITICAL FOR SUCCESS

# ❌ WRONG - These will cause "No module named 'backend'" errors:
from backend.models import User
from backend.routes.auth import router
from ..models import User  # Relative imports

# ✅ CORRECT - Import from project root (backend/ is the working directory):
from models import User
from models.user import User  
from routes.auth import router
from json_db import db, create_tables

# Working directory context in Modal:
# - Modal sets /root as container working directory
# - Your backend/ code is copied to /root/
# - Python treats /root/ as the import root
# - So 'backend' is NOT in the path, import directly from modules

# Example file structure in Modal container:
# /root/
# ├── app.py          → from routes import api_router ✅
# ├── json_db.py      → from json_db import create_tables ✅
# ├── routes/
# │   ├── __init__.py
# │   └── auth.py     → from models.user import User ✅
# └── models/
#     ├── __init__.py
#     └── user.py
"""
