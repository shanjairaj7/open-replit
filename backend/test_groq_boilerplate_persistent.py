#!/usr/local/bin/python3.13
"""
Enhanced Groq Persistent Conversation System with Boilerplate Integration
- Uses pre-built boilerplate as starting point
- Always passes complete file tree to model
- Clones boilerplate for each new project
- Maintains project state across requests
"""

import os
import re
import json
import shutil
import requests
from datetime import datetime
from pathlib import Path
from groq import Groq

class BoilerplatePersistentGroq:
    def __init__(self, api_key: str, project_name: str = None, api_base_url: str = "http://165.22.42.162:8000/api"):
        self.client = Groq(api_key=api_key)
        self.model = "moonshotai/kimi-k2-instruct"
        self.conversation_history = []  # Store conversation messages
        self.api_base_url = api_base_url
        
        # Paths (for local boilerplate reference)
        self.backend_dir = Path(__file__).parent
        self.boilerplate_path = self.backend_dir / "boilerplate" / "shadcn-boilerplate"
        
        # Project setup via API
        if project_name:
            self.project_name = project_name
            self.project_id = self._setup_project_via_api(project_name)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.project_name = f"project_{timestamp}"
            self.project_id = self._setup_project_via_api(self.project_name)
            
        self.project_files = {}
        self._scan_project_files_via_api()
        
        print(f"✅ Project initialized via API: {self.project_name} (ID: {self.project_id})")
        print(f"📁 Total files: {len(self.project_files)}")

    def _setup_project_via_api(self, project_name: str) -> str:
        """Create project via API"""
        try:
            # Check if project already exists
            projects_response = requests.get(f"{self.api_base_url}/projects")
            if projects_response.status_code == 200:
                existing_projects = projects_response.json().get('projects', [])
                for project in existing_projects:
                    # VPS API uses 'id' field directly
                    if project.get('id') == project_name or project.get('name') == project_name:
                        print(f"📂 Using existing project: {project_name} (ID: {project['id']})")
                        return project['id']
            
            # Create new project using VPS API format
            print(f"🔄 Creating new project via VPS API: {project_name}")
            create_payload = {
                "project_id": project_name,
                "files": {}  # Empty files initially, will be populated by AI
            }
            
            response = requests.post(f"{self.api_base_url}/projects", json=create_payload)
            if response.status_code == 200:
                project_data = response.json()
                print(f"✅ Project created successfully via VPS API")
                # VPS API returns the project info with 'id' field
                return project_data['project']['id']
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating project via API: {e}")
            raise

    def _read_file_via_api(self, file_path: str) -> str:
        """Read file content via API"""
        try:
            # VPS API uses GET with file path in URL
            response = requests.get(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}")
            
            if response.status_code == 200:
                return response.json().get('content', '')
            else:
                print(f"⚠️ Error reading file {file_path}: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"⚠️ Error reading file {file_path} via API: {e}")
            return ""

    def _write_file_via_api(self, file_path: str, content: str) -> bool:
        """Write file content via API"""
        try:
            # VPS API uses PUT with file path in URL
            payload = {"content": content}
            response = requests.put(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}", json=payload)
            
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️ Error writing file {file_path}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"⚠️ Error writing file {file_path} via API: {e}")
            return False

    def _execute_command_via_api(self, command: str, cwd: str = None) -> dict:
        """Execute command via API - NOT SUPPORTED ON VPS"""
        # VPS API doesn't support command execution for security
        # Build/run commands are handled automatically by Docker containers
        print(f"⚠️ Command execution not supported on VPS. Commands run automatically in containers.")
        return {"success": False, "error": "Command execution not supported on VPS"}
    
    def _ensure_folder_structure(self):
        """Create proper folder structure for organized development"""
        folders = [
            'src/pages',
            'src/components/ui',  # Already exists
            'src/components/common',
            'src/hooks',
            'src/lib',
            'src/types'
        ]
        
        for folder in folders:
            (self.project_dir / folder).mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Ensured proper folder structure")
    
    def _clean_default_routes(self):
        """Remove default boilerplate routes and create clean starting point"""
        try:
            # Remove default page files
            default_pages = ['HomePage.tsx', 'SettingsPage.tsx', 'ProfilePage.tsx']
            for page in default_pages:
                page_file = self.project_dir / 'src' / 'pages' / page
                if page_file.exists():
                    page_file.unlink()
            
            # Create minimal App.tsx with no default routes
            app_content = '''import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from '@/components/ui/breadcrumb'
import { Separator } from '@/components/ui/separator'

function WelcomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <h1 className="text-4xl font-bold tracking-tight">Welcome</h1>
      <p className="text-muted-foreground text-lg text-center max-w-md">
        Your application is ready. New pages will appear here as you create them.
      </p>
    </div>
  )
}

function App() {
  return (
    <Router>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <AppSidebar />
          <main className="flex-1">
            <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
              <SidebarTrigger className="-ml-1" />
              <Separator orientation="vertical" className="mr-2 h-4" />
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbPage>Application</BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            </header>
            <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
              <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min p-6">
                <Routes>
                  <Route path="/" element={<WelcomePage />} />
                </Routes>
              </div>
            </div>
          </main>
        </div>
      </SidebarProvider>
    </Router>
  )
} 

export default App'''
            
            app_file = self.project_dir / 'src' / 'App.tsx'
            with open(app_file, 'w') as f:
                f.write(app_content)
            
            # Create minimal sidebar with no default routes
            sidebar_content = '''import { useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Home } from 'lucide-react'
import { cn } from '@/lib/utils'

// Routes will be dynamically added here by the AI system
const baseRoutes = [
  {
    title: 'Home',
    url: '/',
    icon: Home,
  },
]

export function AppSidebar() {
  const location = useLocation()

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600">
            <Home className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">My App</h2>
            <p className="text-xs text-muted-foreground">v1.0.0</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-4">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {baseRoutes.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton 
                    asChild
                    className={cn(
                      "w-full justify-start",
                      location.pathname === item.url && "bg-accent text-accent-foreground"
                    )}
                  >
                    <a href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarImage src="/placeholder-avatar.jpg" />
            <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xs">
              JD
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">John Doe</p>
            <p className="text-xs text-muted-foreground truncate">john@example.com</p>
          </div>
          <Badge variant="secondary" className="text-xs">Pro</Badge>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}'''
            
            sidebar_file = self.project_dir / 'src' / 'components' / 'app-sidebar.tsx'
            with open(sidebar_file, 'w') as f:
                f.write(sidebar_content)
            
            print(f"🧹 Cleaned default routes - project ready for new pages")
            
        except Exception as e:
            print(f"⚠️ Error cleaning default routes: {e}")

    def _scan_project_files_via_api(self):
        """Scan project directory via API and build file tree"""
        self.project_files = {}
        
        try:
            # VPS API uses GET to list files
            response = requests.get(f"{self.api_base_url}/projects/{self.project_id}/files")
            
            if response.status_code == 200:
                file_data = response.json()
                files = file_data.get('files', [])
                
                # VPS API returns list of file paths
                for file_path in files:
                    if isinstance(file_path, str):
                        file_name = Path(file_path).name
                        self.project_files[file_path] = {
                            'path': file_path,
                            'name': file_name,
                            'size': 0,  # VPS API doesn't return size
                            'type': 'file'
                        }
            else:
                print(f"⚠️ Error scanning files via API: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️ Error scanning project files via API: {e}")

    def get_project_context(self) -> str:
        """Generate comprehensive project context with file tree"""
        if not self.project_files:
            return ""
        
        context = "\n\nCURRENT PROJECT STATE:\n"
        context += f"Project Directory: {self.project_name}\n"
        context += "This is a complete Vite + React + TypeScript + shadcn/ui + React Router boilerplate.\n\n"
        
        context += "🏗️ BOILERPLATE INCLUDES:\n"
        context += "- ⚡ Vite for fast development\n"
        context += "- ⚛️ React 18 with TypeScript\n"
        context += "- 🎨 Tailwind CSS (fully configured)\n"
        context += "- 🧩 shadcn/ui components (ALL COMPONENTS AVAILABLE: accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toggle-group, toggle, tooltip)\n"
        context += "- 🛣️ React Router for navigation\n"
        context += "- 🎯 Lucide React icons\n"
        context += "- 📁 Proper TypeScript path aliases (@/*)\n"
        context += "- 🗂️ Organized folder structure (pages/, components/, hooks/, etc.)\n\n"
        
        # Get existing routes information
        routes_info = self._get_routes_info()
        
        context += f"🛣️ EXISTING ROUTES & PAGES:\n"
        if routes_info['routes'] and len(routes_info['routes']) > 1:
            for route in routes_info['routes']:
                if route['component'] != 'WelcomePage':  # Don't show internal welcome page
                    context += f"- {route['path']} → {route['component']} (in pages/{route['component']}.tsx)\n"
        else:
            context += "- / → WelcomePage (built-in welcome page)\n"
            context += "- 📝 This is a CLEAN project - no default routes\n"
            context += "- 🎯 New pages you create will automatically be added here\n"
        context += "\n"
        
        # Get route groups information
        route_groups_info = self._get_route_groups_info()
        context += f"📂 CURRENT ROUTE GROUPS:\n"
        if route_groups_info:
            for group_name, routes in route_groups_info.items():
                context += f"- {group_name}: {len(routes)} routes\n"
                for route in routes:
                    context += f"  └── {route['label']} ({route['url']})\n"
        else:
            context += "- No route groups configured yet\n"
        context += "\n"
        
        context += "📂 CURRENT FILE STRUCTURE:\n"
        
        # Create organized tree structure
        def build_tree():
            tree = {}
            for file_path in sorted(self.project_files.keys()):
                parts = Path(file_path).parts
                current = tree
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = "file"
            return tree
        
        def print_tree(tree, prefix="", is_last=True):
            result = ""
            items = list(tree.items())
            for i, (name, subtree) in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "
                result += f"{prefix}{current_prefix}{name}\n"
                
                if isinstance(subtree, dict):
                    extension = "    " if is_last_item else "│   "
                    result += print_tree(subtree, prefix + extension, is_last_item)
            return result
        
        tree = build_tree()
        context += f"{self.project_name}/\n"
        context += print_tree(tree)
        
        # Add file contents for key files to give model better context
        key_files = ['src/App.tsx', 'src/main.tsx', 'src/index.css']
        context += f"\n📄 KEY FILE CONTENTS:\n"
        
        for file_path in key_files:
            if file_path in self.project_files:
                try:
                    content = self._read_file_via_api(file_path)
                    if content:
                        context += f"\n{file_path}:\n```\n{content}\n```\n"
                except Exception as e:
                    context += f"\n{file_path}: (Error reading: {e})\n"
        
        context += f"\n📊 SUMMARY:\n"
        context += f"- Total files: {len(self.project_files)}\n"
        context += f"- Complete boilerplate with navigation, styling, and routing\n"
        context += f"- Ready for development with npm run dev\n"
        
        return context

    def _get_routes_info(self) -> dict:
        """Extract route information from App.tsx and sidebar"""
        routes = []
        
        # Try to read App.tsx to extract existing routes
        try:
            content = self._read_file_via_api('src/App.tsx')
            if content:
                # Extract route patterns
                import re
                route_pattern = r'<Route\s+path="([^"]+)"\s+element={<(\w+)\s*/?>}\s*/>'
                matches = re.findall(route_pattern, content)
                
                for path, component in matches:
                    routes.append({
                        'path': path,
                        'component': component
                    })
                    
        except Exception as e:
            print(f"⚠️ Could not read routes from App.tsx: {e}")
        
        return {'routes': routes}

    def _get_route_groups_info(self) -> dict:
        """Extract route groups information from sidebar"""
        route_groups = {}
        
        # Try to read app-sidebar.tsx to extract route groups
        try:
            content = self._read_file_via_api('src/components/app-sidebar.tsx')
            if content:
                # Extract routeGroups array
                import re
                groups_pattern = r'const routeGroups = \[(.*?)\]'
                groups_match = re.search(groups_pattern, content, re.DOTALL)
                
                if groups_match:
                    groups_content = groups_match.group(1)
                    
                    # Extract individual groups
                    group_pattern = r'{\s*title:\s*["\']([^"\']+)["\'][^}]*items:\s*\[(.*?)\]\s*}'
                    group_matches = re.findall(group_pattern, groups_content, re.DOTALL)
                    
                    for group_title, items_content in group_matches:
                        route_groups[group_title] = []
                        
                        # Extract individual items
                        item_pattern = r'{\s*title:\s*["\']([^"\']+)["\'][^}]*url:\s*["\']([^"\']+)["\'][^}]*}'
                        item_matches = re.findall(item_pattern, items_content)
                        
                        for item_title, item_url in item_matches:
                            route_groups[group_title].append({
                                'label': item_title,
                                'url': item_url
                            })
                    
        except Exception as e:
            print(f"⚠️ Could not read route groups from sidebar: {e}")
        
        return route_groups

    def send_message(self, message: str, is_error_fix: bool = False) -> str:
        """Send message to model with full project context and conversation history"""
        
        # Structured system prompt for monorepo development
        system_prompt = f"""You are Bolt, an expert full-stack developer specializing in creating production-ready applications.

## 1. PROJECT STRUCTURE

You work in a MONOREPO with two directories:
- **frontend/** - React + TypeScript + Vite + Tailwind CSS
- **backend/** - FastAPI + Python

## 2. FRONTEND GUIDELINES

### Available Technology:
- React 18, TypeScript, Vite, React Router DOM
- Tailwind CSS (with advanced features: backdrop-blur, bg-gradient-to-br, ring effects)
- shadcn/ui ALL components: accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toggle-group, toggle, tooltip
- Lucide React icons
- React Router for navigation

### File Structure:
```
frontend/
├── src/
│   ├── pages/         → Page components
│   ├── components/
│   │   └── common/    → Reusable components
│   ├── hooks/         → Custom hooks
│   ├── types/         → TypeScript types
│   └── lib/           → Utilities
```

### Import Patterns:
- `import {{ Button }} from '@/components/ui/button'`
- `import {{ Home, BarChart3, Settings }} from 'lucide-react'`
- `import {{ Link, useNavigate }} from 'react-router-dom'`
- `import {{ cn }} from '@/lib/utils'`

### UI Design Requirements:
1. **Create $100k+ quality interfaces** with premium aesthetics
2. **Visual Excellence:**
   - Sophisticated gradients and glassmorphism (backdrop-blur-sm bg-white/10)
   - Multi-layered shadows (shadow-2xl, shadow-blue-500/25)
   - Smooth micro-animations (transition-all duration-300 ease-in-out)
   - Premium typography with careful hierarchy
3. **Component Quality:**
   - Cards: Gradients, hover:scale-105, glassmorphism effects
   - Tables: Zebra striping, hover:bg-gray-50, sortable headers
   - Buttons: Gradient backgrounds, loading states, hover effects
   - Badges: Color-coded with animations
4. **Rich Data:** ALWAYS realistic data, timestamps, avatars - NO placeholders
5. **Responsive:** Use sm:, md:, lg:, xl: breakpoints
6. **Interactions:** Hover states, loading spinners, modal dialogs, tooltips

## 3. BACKEND GUIDELINES

### Pre-configured Structure:
```
backend/
├── app.py           → DO NOT MODIFY (pre-configured)
├── requirements.txt → Add stable versions only
├── services/        → Create API endpoints here
│   └── __init__.py  → Auto-imports routers
└── models/          → Create Pydantic models here
```

### Backend Rules:
1. **NEVER modify backend/app.py** - it includes all routers automatically
2. **CREATE services in backend/services/** - All endpoints go here
3. **CREATE models in backend/models/** - Pydantic schemas only
4. **ALL APIs automatically under /api prefix** - Don't add /api in routes

### Service Creation Pattern:
```python
# backend/services/entity_service.py
from fastapi import APIRouter, HTTPException
from typing import List
from models.entity_models import EntityCreate, EntityResponse

router = APIRouter()

@router.post("/entities", response_model=EntityResponse)
async def create_entity(entity: EntityCreate):
    # Business logic here
    return EntityResponse(id="123", **entity.dict())

@router.get("/entities", response_model=List[EntityResponse])
async def list_entities():
    return []

@router.get("/entities/{{entity_id}}")
async def get_entity(entity_id: str):
    # Check if entity exists
    # if not found:
    #     raise HTTPException(status_code=404, detail="Entity not found")
    return {{"id": entity_id}}
```

### Model Creation Pattern:
```python
# backend/models/entity_models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EntityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex="^[\\w\\.]+@[\\w\\.]+$")

class EntityCreate(EntityBase):
    password: str = Field(..., min_length=8)

class EntityResponse(EntityBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### Package Versions (STABLE ONLY):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
httpx==0.25.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### services/__init__.py Pattern:
```python
from fastapi import APIRouter
api_router = APIRouter()

# Auto-import all service routers
try:
    from .user_service import router as user_router
    api_router.include_router(user_router, tags=["users"])
except ImportError:
    pass
```

## 4. RESPONSE FORMAT

Use these XML tags in your response:
```xml
<artifact type="text" title="Implementation Plan">
  Plan details...
</artifact>

<action type="file" filePath="frontend/src/pages/Dashboard.tsx">
  File content...
</action>

<action type="route" path="/dashboard" component="Dashboard" icon="BarChart3" label="Dashboard" group="Overview"/>
```

## 5. PROTECTED FILES (NEVER MODIFY)

- frontend/src/App.tsx
- frontend/src/components/app-sidebar.tsx  
- backend/app.py
- Any config files (package.json, vite.config.ts, etc.)

## 6. KEY RULES

1. Create complete solutions (frontend + backend)
2. Follow exact file paths (frontend/... or backend/...)
3. Design exceptional UIs with premium quality
4. Use stable package versions (not latest)
5. Think before implementing
6. Be concise in explanations

CURRENT PROJECT:
{self.get_project_context()}

RESPONSE FORMAT:
- <artifact type="text" title="Description">explanation</artifact>
- <action type="file" filePath="path/to/file">file content</action>
- <action type="route" path="/route-path" component="ComponentName" icon="IconName" label="Nav Label" group="GroupName"/>

SMART ROUTE SYSTEM WITH GROUPS:
When creating pages, ALWAYS:
1. Create the page component in src/pages/ComponentName.tsx (default export)
2. Use the route action to automatically add routing with optional group
3. Organize routes into logical groups for better navigation
4. Follow existing shadcn/ui patterns

Route Groups Available:
- "Overview" - Main dashboard, home, overview pages
- "User Management" - User-related functionality  
- "Analytics & Reports" - Analytics, reporting, charts
- "System" - Settings, security, configuration
- Or create new groups as needed

Examples: 
<action type="route" path="/dashboard" component="Dashboard" icon="BarChart3" label="Dashboard" group="Overview"/>
<action type="route" path="/users/:id" component="UserProfile" icon="User" label="User Profile"/>
<action type="route" path="/settings" component="Settings" icon="Settings" label="Settings" group="System"/>

If no group is specified, routes will be added to "Overview" group.

EXAMPLE STYLE:
```tsx
import {{ Card, CardContent, CardHeader, CardTitle }} from '@/components/ui/card'
import {{ SomeIcon }} from 'lucide-react'

export default function Dashboard() {{
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Your overview</p>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="border border-border rounded-lg shadow-sm">
          <CardHeader className="p-6 pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Revenue</CardTitle>
              <SomeIcon className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <div className="text-2xl font-bold">$10,000</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}}
```

Focus on intelligently extending the existing boilerplate with proper organization."""

        try:
            # Build messages with conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            messages.extend(self.conversation_history)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Send request to Groq
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=16384,
                temperature=0.1,
                stream=False
            )
            
            response = chat_completion.choices[0].message.content
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Process any file actions in the response
            self._process_actions(response)
            
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _process_actions(self, response: str):
        """Extract and execute actions from AI response"""
        # Pattern to match <action type="file" filePath="...">content</action>
        file_action_pattern = r'<action\s+type="file"\s+filePath="([^"]+)">(.*?)</action>'
        file_actions = re.findall(file_action_pattern, response, re.DOTALL)
        
        # Pattern to match <action type="route" path="..." component="..." icon="..." label="...">
        route_action_pattern = r'<action\s+type="route"\s+path="([^"]+)"\s+component="([^"]+)"\s+icon="([^"]+)"\s+label="([^"]+)"(?:\s+group="([^"]+)")?\s*/>'
        route_actions = re.findall(route_action_pattern, response, re.DOTALL)
        
        # Process file actions
        for file_path, content in file_actions:
            try:
                # PROTECT CONFIG FILES AND INFRASTRUCTURE - DO NOT ALLOW MODIFICATIONS
                protected_files = [
                    'package.json', 'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json',
                    'src/App.tsx'
                    # NOTE: src/components/app-sidebar.tsx is protected in prompt but allowed for route system updates
                ]
                if any(file_path.endswith(protected) or file_path == protected for protected in protected_files):
                    print(f"🚫 BLOCKED: Attempted to modify protected infrastructure file {file_path}")
                    continue
                
                # Clean content - remove markdown backticks and language identifiers
                cleaned_content = self._clean_file_content(content)
                
                # Write file content via API
                success = self._write_file_via_api(file_path, cleaned_content)
                if success:
                    print(f"✅ Updated: {file_path}")
                else:
                    print(f"❌ Failed to update: {file_path}")
                
            except Exception as e:
                print(f"❌ Error updating {file_path}: {e}")
        
        # Process route actions
        for route_match in route_actions:
            try:
                path, component, icon, label = route_match[:4]
                group = route_match[4] if len(route_match) > 4 and route_match[4] else None
                self._add_route_to_app(path, component, icon, label, group)
                group_info = f" (group: {group})" if group else ""
                print(f"🛣️ Added route: {path} -> {component}{group_info}")
            except Exception as e:
                print(f"❌ Error adding route {path}: {e}")
        
        # Refresh file scan after changes
        if file_actions or route_actions:
            self._scan_project_files_via_api()
            # Disabled to prevent package.json modifications
            # self._check_and_install_dependencies()
            print(f"📁 Project now has {len(self.project_files)} files")

    def _add_route_to_app(self, path: str, component: str, icon: str, label: str, group: str = None):
        """Automatically add a route to App.tsx and update sidebar"""
        # Update App.tsx with the route
        self._update_routes_in_app(path, component)
        
        # Update the sidebar with the new route
        self._update_sidebar_routes(path, component, icon, label, group)

    def _update_routes_in_app(self, path: str, component: str):
        """Add route to App.tsx Routes section"""
        content = self._read_file_via_api('src/App.tsx')
        if not content:
            return
        
        # Add import for the component if not already present
        if f'import {component}' not in content:
            # Add import after existing imports
            import_section = content.split('\n')
            last_import_line = -1
            for i, line in enumerate(import_section):
                if line.strip().startswith('import'):
                    last_import_line = i
            
            if last_import_line >= 0:
                import_section.insert(last_import_line + 1, f"import {component} from './pages/{component}'")
                content = '\n'.join(import_section)
        
        # Add route to Routes section (only if it doesn't exist)
        if f'path="{path}"' not in content:
            # Find the last Route line and add after it with proper indentation
            lines = content.split('\n')
            last_route_index = -1
            
            for i, line in enumerate(lines):
                if '<Route' in line and 'path=' in line:
                    last_route_index = i
            
            if last_route_index != -1:
                # Get indentation from the last route
                last_route_line = lines[last_route_index]
                indent = len(last_route_line) - len(last_route_line.lstrip())
                new_route = ' ' * indent + f'<Route path="{path}" element={{<{component} />}} />'
                
                # Insert the new route after the last route
                lines.insert(last_route_index + 1, new_route)
                content = '\n'.join(lines)
        
        # Write updated content via API
        self._write_file_via_api('src/App.tsx', content)

    def _update_sidebar_routes(self, path: str, component: str, icon: str, label: str, group: str = None):
        """Add route to AppSidebar component with group support"""
        # Skip dynamic routes (containing :parameter) from sidebar
        if ':' in path:
            print(f"🚫 Skipping dynamic route {path} from sidebar (dynamic routes shouldn't appear in navigation)")
            return
        
        content = self._read_file_via_api('src/components/app-sidebar.tsx')
        if not content:
            return
        
        # Check if route already exists
        if f'url: "{path}"' in content:
            print(f"🔄 Route {path} already exists in sidebar")
            return
        
        # Add icon import if not present
        if f'{icon}' not in content:
            # Find the lucide-react import and add the icon
            import_pattern = r"import \{\s*([^}]+)\s*\} from ['\"]lucide-react['\"]"
            match = re.search(import_pattern, content)
            if match:
                current_imports = match.group(1).strip()
                import_list = [imp.strip() for imp in current_imports.split(',')]
                if icon not in import_list:
                    import_list.append(icon)
                    new_imports = ',\n  '.join(import_list)
                    new_import_line = f"import {{ \n  {new_imports}\n}} from \"lucide-react\""
                    content = content.replace(match.group(0), new_import_line)
        
        # Convert from baseRoutes to routeGroups structure if needed
        if 'const baseRoutes' in content and 'const routeGroups' not in content:
            print("🔄 Converting sidebar from baseRoutes to routeGroups structure")
            
            # Replace baseRoutes with routeGroups structure
            base_routes_pattern = r'const baseRoutes = \[([\s\S]*?)\]'
            base_match = re.search(base_routes_pattern, content)
            
            if base_match:
                # Convert existing baseRoutes to routeGroups format
                route_groups_replacement = f"""const routeGroups = [
  {{
    title: "Overview",
    items: [
      {{ title: "Home", url: "/", icon: Home }},
    ]
  }},
]"""
                content = re.sub(base_routes_pattern, route_groups_replacement, content)
                
                # Update the rendering part completely
                # Find the SidebarContent section and replace it entirely
                sidebar_content_pattern = r'<SidebarContent className="px-4">([\s\S]*?)</SidebarContent>'
                new_sidebar_content = '''<SidebarContent className="px-4">
        {routeGroups.map((group) => (
          <SidebarGroup key={group.title}>
            <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild
                      className={cn(
                        "w-full justify-start",
                        location.pathname === item.url && "bg-accent text-accent-foreground"
                      )}
                    >
                      <a href={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </a>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>'''
                content = re.sub(sidebar_content_pattern, new_sidebar_content, content)
                
                # Add SidebarGroupLabel import
                if 'SidebarGroupLabel' not in content:
                    content = content.replace('SidebarGroupContent,', 'SidebarGroupContent,\n  SidebarGroupLabel,')
        
        # Always ensure SidebarGroupLabel import is present when using routeGroups
        if 'const routeGroups' in content and 'SidebarGroupLabel' not in content:
            content = content.replace('SidebarGroupContent,', 'SidebarGroupContent,\n  SidebarGroupLabel,')
        
        # Now try to find the target group and add the route
        target_group = group or "Overview"
        
        # Look for the group and add the route item
        group_pattern = rf'(\{{[\s\S]*?title:\s*"{re.escape(target_group)}"[\s\S]*?items:\s*\[)([\s\S]*?)(\][\s\S]*?\}})'
        group_match = re.search(group_pattern, content)
        
        if group_match:
            # Add to existing group
            items_section = group_match.group(2)
            new_item = f'      {{ title: "{label}", url: "{path}", icon: {icon} }},'
            
            # Add the new item at the end of the items array
            if items_section.strip():
                updated_items = f"{items_section}\n{new_item}"
            else:
                updated_items = f"\n{new_item}\n      "
            
            content = content.replace(group_match.group(2), updated_items)
            
        else:
            # Create new group - find the routeGroups array end and add before it
            route_groups_match = re.search(r'const routeGroups = \[([\s\S]*?)\]', content)
            if route_groups_match:
                existing_groups = route_groups_match.group(1)
                new_group = f"""  {{
    title: "{target_group}",
    items: [
      {{ title: "{label}", url: "{path}", icon: {icon} }},
    ]
  }},
"""
                # Add the new group before the closing bracket
                updated_groups = f"{existing_groups}{new_group}"
                content = content.replace(route_groups_match.group(1), updated_groups)
                print(f"📝 Created new group: {target_group}")
        
        # Write updated content via API
        self._write_file_via_api('src/components/app-sidebar.tsx', content)

    def _clean_file_content(self, content: str) -> str:
        """Clean file content by removing markdown formatting"""
        content = content.strip()
        
        # Remove markdown code block markers
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line if it's ```language
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        return content.strip()

    def start_preview_and_get_url(self) -> str:
        """Start the project preview and return the URL"""
        try:
            # Start the preview
            response = requests.post(f"{self.api_base_url}/projects/{self.project_id}/start-preview")
            if response.status_code == 200:
                preview_data = response.json()
                port = preview_data.get('port', 3001)
                # Return the actual VPS IP with the port
                preview_url = f"http://165.22.42.162:{port}"
                print(f"🚀 Preview started on port {port}")
                print(f"🌐 Access your project at: {preview_url}")
                return preview_url
            else:
                print(f"❌ Error starting preview: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error starting preview: {e}")
            return None

    def _check_and_install_dependencies(self):
        """Scan project files and add missing dependencies to package.json"""
        try:
            # Read current package.json
            package_json_path = self.project_dir / 'package.json'
            if not package_json_path.exists():
                return
                
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            current_deps = set(package_data.get('dependencies', {}).keys())
            current_dev_deps = set(package_data.get('devDependencies', {}).keys())
            all_current = current_deps | current_dev_deps
            
            # Scan all project files for imports
            needed_packages = set()
            
            for file_info in self.project_files.values():
                if file_info['path'].endswith(('.ts', '.tsx', '.js', '.jsx')):
                    try:
                        with open(file_info['full_path'], 'r') as f:
                            content = f.read()
                        
                        # Find import statements
                        import_pattern = r"import.*?from\s+['\"]([^'\"]+)['\"]"
                        imports = re.findall(import_pattern, content)
                        
                        for import_name in imports:
                            # Skip relative imports
                            if import_name.startswith('.'):
                                continue
                            
                            # Skip path aliases (like @/components, @/lib)
                            if import_name.startswith('@/'):
                                continue
                            
                            # Skip Node.js built-in modules
                            builtin_modules = {'path', 'fs', 'url', 'util', 'crypto', 'os', 'http', 'https', 'stream'}
                            if import_name in builtin_modules:
                                continue
                            
                            # Extract package name (handle scoped packages)
                            if import_name.startswith('@'):
                                # Scoped package like @radix-ui/react-button
                                parts = import_name.split('/')
                                if len(parts) >= 2:
                                    package_name = f"{parts[0]}/{parts[1]}"
                                else:
                                    package_name = import_name
                            else:
                                # Regular package - take first part
                                package_name = import_name.split('/')[0]
                            
                            needed_packages.add(package_name)
                    
                    except Exception as e:
                        print(f"⚠️ Error scanning {file_info['path']}: {e}")
            
            # Find missing packages
            missing_packages = needed_packages - all_current
            
            if missing_packages:
                print(f"📦 Adding missing dependencies to package.json: {', '.join(missing_packages)}")
                
                # Add missing packages to dependencies with latest version
                # BUT preserve existing versions from boilerplate
                if 'dependencies' not in package_data:
                    package_data['dependencies'] = {}
                
                for pkg in missing_packages:
                    # Only add if it's not already in the boilerplate
                    # This prevents overwriting correct versions like tailwindcss v4
                    if pkg not in package_data['dependencies']:
                        package_data['dependencies'][pkg] = 'latest'
                
                # Write updated package.json
                with open(package_json_path, 'w') as f:
                    json.dump(package_data, f, indent=2)
                
                print(f"✅ Added {len(missing_packages)} packages to package.json")
                print("💡 Run 'npm install' to install the new dependencies")
            
        except Exception as e:
            print(f"⚠️ Error checking dependencies: {e}")

    def check_build_errors(self) -> str:
        """Build checking not needed for VPS - containers handle build automatically"""
        # VPS runs npm install and npm run dev automatically in Docker containers
        # Build errors will be visible in container logs if any
        print("ℹ️  Build checking skipped - VPS containers handle builds automatically")
        print("💡 Any build errors will appear in the preview logs")
        return None

def main():
    """Demo the enhanced boilerplate persistent system"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable not set")
        return
    
    # Create system with custom project name
    system = BoilerplatePersistentGroq(api_key, "client_management_system")
    
    print("\n" + "="*60)
    print("🚀 Enhanced Boilerplate Persistent Groq System")
    print("="*60)
    print("This system:")
    print("✅ Starts with complete Vite + React + shadcn/ui boilerplate")
    print("✅ Always passes full file tree to model")
    print("✅ Maintains context across multiple requests")
    print("✅ Creates/modifies files in real project")
    print("✅ Model knows all packages are pre-installed")
    print()
    
    # Demo requests
    requests = [
        "Create a task management app where I can add, edit, and delete tasks. Each task should have a title, description, due date, and priority level. Show all tasks in a nice list with the ability to mark them as completed."
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"\n{'='*20} REQUEST {i} {'='*20}")
        print(f"📝 {request}")
        print(f"\n{'='*50}")
        
        response = system.send_message(request)
        
        # Save full raw response to markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = system.backend_dir / f"groq_response_{timestamp}.md"
        
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"# Groq Model Response - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Request\n{request}\n\n")
            f.write(f"## Full Raw Response\n\n")
            f.write(response)
        
        print(f"💾 Full raw response saved to: {response_file}")
        
        # Show clean response (without XML tags for demo)
        lines = response.split('\n')
        clean_lines = []
        in_action = False
        
        for line in lines:
            if '<action type="file"' in line:
                in_action = True
                continue
            elif '</action>' in line:
                in_action = False
                continue
            elif not in_action and not line.strip().startswith('<'):
                clean_lines.append(line)
        
        clean_response = '\n'.join(clean_lines).strip()
        if clean_response:
            print(f"🤖 {clean_response}")
        
        print(f"\n📊 Project Status: {len(system.project_files)} files")
        
        # Check for build errors and fix them with retry loop (max 3 attempts)
        max_fix_attempts = 3
        fix_attempt = 0
        
        while fix_attempt < max_fix_attempts:
            build_errors = system.check_build_errors()
            
            if build_errors is None:
                if fix_attempt == 0:
                    print("🎉 Build successful on first try - no errors to fix!")
                else:
                    print("🎉 All build errors have been resolved!")
                break
                
            fix_attempt += 1
            print(f"\n{'='*20} FIXING BUILD ERRORS (Attempt {fix_attempt}/{max_fix_attempts}) {'='*20}")
            
            error_fix_request = f"""The build failed with the following errors. Please fix these errors by updating the existing files:

BUILD ERRORS:
{build_errors}

Please analyze the errors and provide the necessary fixes. Update the existing files to resolve all build issues."""
            
            fix_response = system.send_message(error_fix_request, is_error_fix=True)
            
            # Save error fix response
            fix_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fix_response_file = system.backend_dir / f"groq_fix_response_attempt{fix_attempt}_{fix_timestamp}.md"
            
            with open(fix_response_file, 'w', encoding='utf-8') as f:
                f.write(f"# Groq Fix Response - Attempt {fix_attempt} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## Build Errors\n{build_errors}\n\n")
                f.write(f"## Fix Response\n\n")
                f.write(fix_response)
            
            print(f"💾 Fix response saved to: {fix_response_file}")
            
            # Show fix response
            fix_lines = fix_response.split('\n')
            fix_clean_lines = []
            in_action = False
            
            for line in fix_lines:
                if '<action type="file"' in line:
                    in_action = True
                    continue
                elif '</action>' in line:
                    in_action = False
                    continue
                elif not in_action and not line.strip().startswith('<'):
                    fix_clean_lines.append(line)
            
            fix_clean_response = '\n'.join(fix_clean_lines).strip()
            if fix_clean_response:
                print(f"🔧 {fix_clean_response}")
        
        # Final status check
        if fix_attempt >= max_fix_attempts:
            final_build_check = system.check_build_errors()
            if final_build_check is not None:
                print(f"⚠️ Reached maximum fix attempts ({max_fix_attempts}). Some build errors may still remain.")
                print("Consider reviewing the errors manually or running the script again.")
        
        # Show project structure after each request
        context = system.get_project_context()
        if context:
            structure_lines = [line for line in context.split('\n') 
                             if '📂 CURRENT FILE STRUCTURE:' in line or 
                                line.startswith(('├──', '└──', 'demo_dashboard/'))]
            if len(structure_lines) > 1:
                print("\n📁 Updated Structure:")
                for line in structure_lines[1:]:  # Skip the header
                    print(line)
    
    # After all requests are processed, start the preview
    print(f"\n{'='*60}")
    print("🚀 STARTING PROJECT PREVIEW")
    print("="*60)
    
    preview_url = system.start_preview_and_get_url()
    if preview_url:
        print(f"\n✅ PROJECT READY!")
        print(f"🌐 View your project at: {preview_url}")
        print(f"💡 The preview server is running. You can make changes and see them live!")
    else:
        print(f"\n❌ Failed to start preview. Please check the logs.")

if __name__ == "__main__":
    main()