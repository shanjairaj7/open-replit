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

