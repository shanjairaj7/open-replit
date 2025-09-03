terminal_command_codebase_search = """
Codebase Search Commands

### Rule 1: Use rg (ripgrep) for fast pattern-based searches

When to use: Finding functions, variables, imports, specific code patterns, or text across
files.

*Basic Command Structure:*

rg "pattern" --type filetype -n -C 2

Examples:

A. Find Error Handling Patterns:
# Find all try-catch blocks with context
rg "try\s*\{.*catch\s*\(" --type js --type ts -n -C 3

# Find specific error types being thrown
rg "throw\s+new\s+(\w+Error)" --type js --type ts -n -C 2

B. Find Function Definitions:
# Find all async functions
rg "async\s+function\s+(\w+)" --type js --type ts -n -C 2

# Find React component definitions
rg "(const|function)\s+(\w+)\s*=.*=>" --type tsx --type jsx -n -C 2

Rule 2: Use find + xargs + grep for file-based searches with complex conditions

When to use: Searching within specific file types, directories, or when you need to combine
multiple conditions.

Basic Command Structure:

find . -name "*.ext" | xargs grep -n "pattern"

Examples:

A. Debug Import/Export Issues:
# Find all imports of a specific module across TypeScript files
find ./src -name "*.ts" -o -name "*.tsx" | xargs grep -n "import.*from.*['\"]\./.*auth"

# Find unused exports (exports that aren't imported anywhere)
find ./src -name "*.ts" | xargs grep -n "export.*function.*getUserById"

B. Find API Endpoints and Route Handlers:
# Find all API route definitions in backend
find ./backend -name "*.py" -o -name "*.js" | xargs grep -n "@app\.\(get\|post\|put\|delete\)"

# Find database query patterns
find ./backend -name "*.py" | xargs grep -n "\.\(select\|insert\|update\|delete\)\("

Quick Reference Flags:

ripgrep (rg) flags:
- -n: Show line numbers
- -C 2: Show 2 lines of context before/after
- --type js: Search only JavaScript files
- -i: Case insensitive search
- -w: Match whole words only

grep flags:
- -n: Show line numbers
- -r: Recursive search
- -i: Case insensitive
- -l: Show only filenames with matches

These two methods give you speed (ripgrep) and flexibility (find+grep) to handle 90% of
codebase search needs efficiently.
"""

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

# FastAPI endpoint pattern - SAFE CODE approach
@router.post("/items")
async def create_item_endpoint(request: Request):
    data = await request.json()
    if db.exists("items", name=data.get("name")):
        raise HTTPException(status_code=400, detail="Item already exists")
    return db.insert("items", data)
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
/* Tailwind v4 CSS-First Example */

@import "tailwindcss";

@theme {
  /* Define colors as HSL values */
  --color-primary: hsl(220 14% 96%);
  --color-background: hsl(0 0% 100%);
  --color-foreground: hsl(222 84% 5%);
  --color-border: hsl(214 32% 91%);
  --font-sans: Inter, system-ui, sans-serif;
}

/* Custom utilities for complex patterns only */
.app-gradient {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-foreground) 100%);
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
# SAFE CODE: Complete Working FastAPI + JsonDB Example

# 1. Route File (backend/routes/contacts.py) - SAFE PATTERNS ONLY:
from fastapi import APIRouter, Request, HTTPException
from json_db import db  # Direct import - NO JsonDBSession!
from datetime import datetime

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.post("/")
async def create_contact(request: Request):
    \"\"\"SAFE PATTERN: async + request.json() + direct db\"\"\"
    data = await request.json()

    # Simple validation - only check required fields
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Name is required")

    # Create contact with optional fields
    contact = {
        "name": data["name"],
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "company": data.get("company", ""),
        "notes": data.get("notes", ""),
        "created_at": datetime.now().isoformat()
    }

    # Direct db access - NO dependency injection
    result = db.insert("contacts", contact)

    # Return clean dict
    return {
        "id": result,
        "name": contact["name"],
        "email": contact["email"]
    }

@router.get("/")
def get_contacts():
    \"\"\"SAFE PATTERN: Direct db access\"\"\"
    contacts = db.find_all("contacts")
    return contacts

@router.get("/{contact_id}")
def get_contact(contact_id: int):
    \"\"\"SAFE PATTERN: Simple path parameter\"\"\"
    contact = db.find_one("contacts", id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}")
async def update_contact(contact_id: int, request: Request):
    \"\"\"SAFE PATTERN: async + request.json() + direct db\"\"\"
    data = await request.json()

    # Check if exists
    if not db.exists("contacts", id=contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")

    # Update with timestamp
    data["updated_at"] = datetime.now().isoformat()

    success = db.update_one("contacts", {"id": contact_id}, data)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")

    return {"message": "Contact updated"}

# 2. App Setup (backend/app.py) - Database Initialization:
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI
    from routes import api_router
    from json_db import create_tables

    # Initialize JSON database
    def initialize_json_databases():
        table_names = ["users", "contacts", "tasks", "projects"]
        create_tables(table_names)
        print(f"✅ JSON database initialized: {table_names}")

    initialize_json_databases()

    app = FastAPI(title="My App", version="1.0.0")
    app.include_router(api_router)

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

todo_store_example = """
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { toast } from 'sonner';
import * as todoApi from '@/lib/api/todos';

interface Todo {
  id: number;
  title: string;
  description?: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at: string;
}

interface TodoStore {
  todos: Todo[];
  loading: boolean;
  priorityFilter: string;

  // Actions
  fetchTodos: () => Promise<void>;
  addTodo: (todoData: Partial<Todo>) => Promise<void>;
  updateTodo: (id: number, updates: Partial<Todo>) => Promise<void>;
  deleteTodo: (id: number) => Promise<void>;
  setPriorityFilter: (priority: string) => void;
}

export const useTodoStore = create<TodoStore>()(
  persist(
    (set, get) => ({
      todos: [],
      loading: false,
      priorityFilter: 'all',

      fetchTodos: async () => {
        try {
          const todos = await todoApi.getTodos(get().priorityFilter);
          set({ todos });
        } catch (error) {
          toast.error('Failed to fetch todos');
        }
      },

      addTodo: async (todoData) => {
        try {
          const newTodo = await todoApi.createTodo(todoData);
          set(state => ({ todos: [...state.todos, newTodo] }));
          toast.success('Todo added successfully!');
        } catch (error) {
          toast.error('Failed to add todo');
        }
      },

      updateTodo: async (id, updates) => {
        try {
          const updatedTodo = await todoApi.updateTodo(id, updates);
          set(state => ({
            todos: state.todos.map(todo =>
              todo.id === id ? updatedTodo : todo
            )
          }));
          toast.success('Todo updated!');
        } catch (error) {
          toast.error('Failed to update todo');
        }
      },

      deleteTodo: async (id) => {
        try {
          await todoApi.deleteTodo(id);
          set(state => ({
            todos: state.todos.filter(todo => todo.id !== id)
          }));
          toast.success('Todo deleted!');
        } catch (error) {
          toast.error('Failed to delete todo');
        }
      },

      setPriorityFilter: (priority) => {
        set({ priorityFilter: priority });
      }
    }),
    {
      name: 'todo-storage',
      partialize: (state) => ({ priorityFilter: state.priorityFilter })
    }
  )
);
"""

analytics_store_example = """
import { create } from 'zustand';
import { api } from '../lib/api';

interface AnalyticsData {
  total_contacts: number;
  total_deals: number;
  conversion_rate: number;
  monthly_trends: any[];
}

interface AnalyticsStore {
  analytics: AnalyticsData | null;
  loading: boolean;
  error: string | null;
  fetchAnalytics: () => Promise<void>;
  refreshMetrics: () => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsStore>((set, get) => ({
  analytics: null,
  loading: false,
  error: null,

  fetchAnalytics: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/analytics/overview');
      set({ analytics: response.data, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch analytics', loading: false });
    }
  },

  refreshMetrics: async () => {
    return get().fetchAnalytics();
  }
}));
"""

todo_api_example = """
import { api } from './api';

interface Todo {
  id: number;
  title: string;
  completed: boolean;
  priority: 'High' | 'Medium' | 'Low';
}

export const getTodos = async (priority?: string | null): Promise<Todo[]> => {
  const params = priority ? `?priority=${priority}` : '';
  const response = await api.get(`/todos${params}`);
  return response.data;
};

export const createTodo = async (todo: Omit<Todo, 'id'>): Promise<Todo> => {
  const response = await api.post('/todos', todo);
  return response.data;
};

export const updateTodo = async (id: number, updates: Partial<Todo>): Promise<Todo> => {
  const response = await api.patch(`/todos/${id}`, updates);
  return response.data;
};

export const deleteTodo = async (id: number): Promise<void> => {
  await api.delete(`/todos/${id}`);
};
"""

todo_list_component = """
import { useTodoStore } from '@/stores/todoStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Trash2, Check } from 'lucide-react';

export function TodoList() {
  const { todos, updateTodo, deleteTodo } = useTodoStore();

  const toggleComplete = (id: number, completed: boolean) => {
    updateTodo(id, { completed: !completed });
  };

  const getPriorityVariant = (priority: string) => {
    switch (priority) {
      case 'High': return 'destructive';
      case 'Medium': return 'default';
      case 'Low': return 'secondary';
      default: return 'default';
    }
  };

  return (
    <div className="space-y-2">
      {todos.map(todo => (
        <div key={todo.id} className={`p-4 border rounded-lg ${todo.completed ? 'opacity-50' : ''}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                size="sm"
                variant={todo.completed ? "default" : "outline"}
                onClick={() => toggleComplete(todo.id, todo.completed)}
              >
                <Check className="h-4 w-4" />
              </Button>
              <span className={todo.completed ? 'line-through' : ''}>{todo.title}</span>
              <Badge variant={getPriorityVariant(todo.priority)}>{todo.priority}</Badge>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => deleteTodo(todo.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ))}

      {todos.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No todos yet. Add your first task above!
        </div>
      )}
    </div>
  );
}
"""

todo_homepage_component = """
import { useState, useEffect } from 'react';
import { useTodoStore } from '@/stores/todoStore';
import { TodoList } from '@/components/TodoList';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus } from 'lucide-react';

export function HomePage() {
  const [newTodoTitle, setNewTodoTitle] = useState('');
  const [newTodoPriority, setNewTodoPriority] = useState('Medium');
  const { fetchTodos, addTodo, setPriorityFilter, priorityFilter } = useTodoStore();

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  const handleAddTodo = () => {
    if (newTodoTitle.trim()) {
      addTodo({
        title: newTodoTitle,
        completed: false,
        priority: newTodoPriority as 'High' | 'Medium' | 'Low'
      });
      setNewTodoTitle('');
      setNewTodoPriority('Medium');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">TaskMaster</h1>
        <p className="text-gray-600">Organize your tasks with priority-based productivity</p>
      </div>

      {/* Add Todo Form */}
      <div className="bg-white rounded-lg border p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Add New Task</h2>
        <div className="flex gap-2">
          <Input
            placeholder="What needs to be done?"
            value={newTodoTitle}
            onChange={(e) => setNewTodoTitle(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddTodo()}
            className="flex-1"
          />
          <Select value={newTodoPriority} onValueChange={setNewTodoPriority}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="High">High</SelectItem>
              <SelectItem value="Medium">Medium</SelectItem>
              <SelectItem value="Low">Low</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleAddTodo}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Priority Filter */}
      <div className="mb-6">
        <Select value={priorityFilter || 'all'} onValueChange={(value) => setPriorityFilter(value === 'all' ? null : value)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priorities</SelectItem>
            <SelectItem value="High">High Priority</SelectItem>
            <SelectItem value="Medium">Medium Priority</SelectItem>
            <SelectItem value="Low">Low Priority</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Todo List */}
      <TodoList />
    </div>
  );
}
"""

analytics_backend_example = """
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from models.user import User
from utils.auth import get_current_user
from json_db import JsonDB

router = APIRouter()

@router.get("/analytics/overview")
async def get_analytics_overview(current_user: User = Depends(get_current_user)):
    \"\"\"Get analytics overview with sales metrics and conversion rates\"\"\"
    try:
        db = JsonDB()
        contacts = db.find_all("contacts", {"user_id": current_user.id})
        deals = db.find_all("deals", {"user_id": current_user.id})

        # Calculate metrics from existing data
        total_contacts = len(contacts)
        total_deals = len(deals)
        conversion_rate = (total_deals / total_contacts * 100) if total_contacts > 0 else 0

        return {
            "total_contacts": total_contacts,
            "total_deals": total_deals,
            "conversion_rate": round(conversion_rate, 2),
            "monthly_trends": []  # Add trend calculation logic
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

analytics_chart_component = """
import React from 'react';
import { Card } from './ui/card';

interface AnalyticsChartProps {
  data: any[];
  title: string;
  type: 'line' | 'bar' | 'pie';
}

export const AnalyticsChart: React.FC<AnalyticsChartProps> = ({ data, title, type }) => {
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
        {/* Simple chart visualization - replace with recharts implementation */}
        <div className="text-sm text-gray-500">
          Chart visualization for {title}
          <br />
          Type: {type} | Data points: {data.length}
        </div>
      </div>
    </Card>
  );
};
"""

analytics_page_component = """
import React, { useEffect } from 'react';
import { useAnalyticsStore } from '../stores/analyticsStore';
import { Card } from '../components/ui/card';
import { AnalyticsChart } from '../components/AnalyticsChart';

export const AnalyticsPage: React.FC = () => {
  const { analytics, loading, error, fetchAnalytics } = useAnalyticsStore();

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading) return <div className="p-6">Loading analytics...</div>;
  if (error) return <div className="p-6 text-red-500">Error: {error}</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Analytics Dashboard</h1>

      {analytics && (
        <>
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">Total Contacts</h3>
              <p className="text-2xl font-bold">{analytics.total_contacts}</p>
            </Card>
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">Total Deals</h3>
              <p className="text-2xl font-bold">{analytics.total_deals}</p>
            </Card>
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">Conversion Rate</h3>
              <p className="text-2xl font-bold">{analytics.conversion_rate}%</p>
            </Card>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AnalyticsChart
              data={analytics.monthly_trends}
              title="Sales Trends"
              type="line"
            />
            <AnalyticsChart
              data={[]}
              title="Conversion Funnel"
              type="bar"
            />
          </div>
        </>
      )}
    </div>
  );
};
"""
