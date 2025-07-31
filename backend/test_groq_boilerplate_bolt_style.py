#!/usr/bin/env python3
"""
Enhanced Groq Persistent Conversation System with Bolt.diy Style Prompts
- Uses bolt.diy prompt structure and design philosophy
- Professional UI with rich data and interactions
- Complete boilerplate integration
"""

import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path
from groq import Groq

class BoltStyleGroq:
    def __init__(self, api_key: str, project_name: str = None):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        
        # Paths
        self.backend_dir = Path(__file__).parent
        self.boilerplate_path = self.backend_dir / "boilerplate" / "shadcn-boilerplate"
        
        # Project setup
        if project_name:
            self.project_dir = self.backend_dir / f"projects" / project_name
            self._setup_project()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.project_dir = self.backend_dir / f"projects" / f"project_{timestamp}"
            self._setup_project()
            
        self.project_files = {}
        self._scan_project_files()
        
        print(f"✅ Project initialized: {self.project_dir}")
        print(f"📁 Total files: {len(self.project_files)}")

    def _setup_project(self):
        """Clone boilerplate to create new project"""
        if not self.boilerplate_path.exists():
            raise Exception(f"Boilerplate not found at {self.boilerplate_path}")
            
        if self.project_dir.exists():
            print(f"📂 Using existing project: {self.project_dir}")
            self._ensure_folder_structure()
            return
            
        print(f"🔄 Cloning boilerplate to: {self.project_dir}")
        
        # Create projects directory
        self.project_dir.parent.mkdir(exist_ok=True)
        
        # Clone boilerplate (excluding node_modules and dist)
        shutil.copytree(
            self.boilerplate_path, 
            self.project_dir,
            ignore=shutil.ignore_patterns('node_modules', 'dist', '.git', '*.log')
        )
        
        # Ensure proper folder structure
        self._ensure_folder_structure()
        
        # Clean up default routes for fresh project
        self._clean_default_routes()
        
        print(f"✅ Project cloned successfully")
    
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

    def _scan_project_files(self):
        """Scan project directory and build file tree"""
        self.project_files = {}
        
        if not self.project_dir.exists():
            return
            
        # Include relevant file types
        extensions = {'.tsx', '.ts', '.jsx', '.js', '.json', '.css', '.html', '.md'}
        
        for file_path in self.project_dir.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix in extensions and
                'node_modules' not in str(file_path) and
                'dist' not in str(file_path) and
                '.git' not in str(file_path)):
                
                relative_path = file_path.relative_to(self.project_dir)
                self.project_files[str(relative_path)] = {
                    'path': str(relative_path),
                    'full_path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                }

    def get_project_context(self) -> str:
        """Generate project context for the model"""
        if not self.project_files:
            return ""
        
        context = "\n\nCURRENT PROJECT STATE:\n"
        context += f"Working directory: {self.project_dir.name}\n"
        context += f"Total files: {len(self.project_files)}\n"
        
        # Get existing routes
        routes_info = self._get_routes_info()
        if routes_info['routes']:
            context += "\nExisting routes:\n"
            for route in routes_info['routes']:
                if route['component'] != 'WelcomePage':
                    context += f"- {route['path']} → {route['component']}\n"
        
        return context

    def _get_routes_info(self) -> dict:
        """Extract route information from App.tsx"""
        routes = []
        
        app_file = self.project_dir / 'src' / 'App.tsx'
        if app_file.exists():
            try:
                with open(app_file, 'r') as f:
                    content = f.read()
                
                route_pattern = r'<Route\s+path="([^"]+)"\s+element={<(\w+)\s*/?>}\s*/>'
                matches = re.findall(route_pattern, content)
                
                for path, component in matches:
                    routes.append({
                        'path': path,
                        'component': component
                    })
                    
            except Exception as e:
                print(f"⚠️ Could not read routes: {e}")
        
        return {'routes': routes}

    def send_message(self, message: str) -> str:
        """Send message to model with bolt.diy style prompt"""
        
        # Bolt.diy style system prompt
        system_prompt = f"""You are Bolt, an expert AI assistant and exceptional senior software developer with vast knowledge across multiple programming languages, frameworks, and best practices.

<system_constraints>
  You are operating in a pre-configured React environment with:
  - Complete Vite + React + TypeScript + Tailwind CSS setup
  - shadcn/ui components library fully integrated
  - React Router DOM for navigation
  - All dependencies pre-installed and working
  - Project runs with 'npm run dev'
  
  The environment supports all modern web development features.
</system_constraints>

<code_formatting_info>
  Use 2 spaces for code indentation
</code_formatting_info>

<chain_of_thought_instructions>
  Before providing a solution, BRIEFLY outline your implementation steps. This helps ensure systematic thinking and clear communication. Your planning should:
  - List concrete steps you'll take
  - Identify key components needed
  - Be concise (2-4 lines maximum)
  
  Example: "I'll create an analytics dashboard by:
  1. Building stat cards with gradient backgrounds
  2. Adding a data table with rich metrics
  3. Including professional styling with shadows and hover effects"
</chain_of_thought_instructions>

<artifact_info>
  You create a SINGLE, comprehensive artifact for each project. The artifact contains all necessary steps and components, including:
  - Files to create and their contents
  - Components organized in proper folders  
  - Professional UI with production-ready design
  
  CRITICAL: Think HOLISTICALLY and COMPREHENSIVELY BEFORE creating an artifact. This means:
  - Consider ALL relevant files in the project
  - Analyze the entire project context
  - Create a complete, polished solution
</artifact_info>

<design_instructions>
  Overall Goal: Create visually stunning, unique, highly interactive, content-rich, and production-ready applications. Avoid generic templates.

  Visual Identity & Branding:
    - Establish a distinctive art direction with premium feel
    - Use premium typography with refined hierarchy and spacing
    - Incorporate sophisticated visual effects (shadows, gradients, transitions)
    - Create depth with layered elements and elevation
    - Use high-quality, optimized visual assets

  Layout & Structure:
    - Implement a systemized spacing/sizing system (8pt grid)
    - Use fluid, responsive grids adapting gracefully to all screen sizes
    - Utilize whitespace effectively for focus and balance
    - Create visual hierarchy with size, weight, and color

  User Experience (UX) & Interaction:
    - Design intuitive navigation and user journeys
    - Implement smooth, accessible microinteractions and animations
    - Use hover states, active states, and smooth transitions
    - Ensure engaging copywriting and clear data visualization

  Color & Typography:
    - Rich color system with gradients (bg-gradient-to-br from-blue-50 to-indigo-100)
    - Accent colors for emphasis (border-l-4 border-blue-500)
    - Typography scale: text-3xl font-bold → text-lg font-semibold → text-sm
    - Professional font hierarchy with varied weights

  Technical Excellence:
    - Write clean, semantic HTML with ARIA attributes
    - Ensure responsive design with Tailwind breakpoints
    - Pay meticulous attention to detail and polish
    - Always prioritize user needs and experience

  Professional Components:
    - Cards: shadow-lg, bg-gradient-to-br for depth, hover:shadow-xl transitions
    - Tables: zebra striping, sortable headers, action buttons, rich data cells
    - Headers: text-3xl font-bold with subtitles, breadcrumbs, CTAs
    - Navigation: Active states, smooth transitions, contextual icons
    - Forms: Rich inputs with floating labels, validation states, helper text
    - Stats: Progress bars, trend indicators, animated counters
    - Badges: Color-coded statuses with meaningful colors

  Content & Data Requirements:
    - ALWAYS include realistic, rich data - NO lorem ipsum or placeholders
    - Financial metrics: $1,234,567 revenue, 23.5% growth, +$125,000 MoM
    - User metrics: 10,000 active users, 89% satisfaction, 2.5min avg session
    - Performance data: 99.9% uptime, 120ms response time, 4.8/5 rating
    - Timestamps: "2 hours ago", "Last updated: 10:30 AM", "Jan 15, 2024"
    - Status indicators: Active ✓, Pending ⏳, Failed ✗, Processing ⟳
    - Activity feeds with user avatars, actions, and contextual information
    - Charts and graphs with real data points and meaningful insights
</design_instructions>

IMPORTANT: Create production-ready UI that looks like a $50k enterprise application!

PROJECT CONTEXT:{self.get_project_context()}

RESPONSE FORMAT:
When you receive a request, respond with:
1. <artifact type="text" title="Brief description">Short planning steps (2-4 lines)</artifact>
2. <action type="file" filePath="src/path/to/file.tsx">complete file content</action>
3. <action type="route" path="/route" component="ComponentName" icon="IconName" label="Nav Label"/>

FILE PLACEMENT:
- Page components → src/pages/ComponentName.tsx
- Reusable components → src/components/common/ComponentName.tsx
- UI components → src/components/ui/ (pre-installed, don't create)
- Hooks → src/hooks/useHookName.ts
- Types → src/types/types.ts
- Utils → src/lib/utils.ts

ULTRA IMPORTANT: Think first and create a complete, professional solution with rich UI and real data."""

        try:
            # Send request to Groq
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.model,
                max_tokens=8000,
                temperature=0.1,
                stream=False
            )
            
            response = chat_completion.choices[0].message.content
            
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
        route_action_pattern = r'<action\s+type="route"\s+path="([^"]+)"\s+component="([^"]+)"\s+icon="([^"]+)"\s+label="([^"]+)"\s*/>'
        route_actions = re.findall(route_action_pattern, response, re.DOTALL)
        
        # Process file actions
        for file_path, content in file_actions:
            try:
                # Clean content - remove markdown backticks
                cleaned_content = self._clean_file_content(content)
                
                # Ensure path is relative to project directory
                full_path = self.project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                print(f"✅ Updated: {file_path}")
                
            except Exception as e:
                print(f"❌ Error updating {file_path}: {e}")
        
        # Process route actions
        for path, component, icon, label in route_actions:
            try:
                self._add_route_to_app(path, component, icon, label)
                print(f"🛣️ Added route: {path} -> {component}")
            except Exception as e:
                print(f"❌ Error adding route {path}: {e}")
        
        # Refresh file scan after changes
        if file_actions or route_actions:
            self._scan_project_files()
            self._check_and_install_dependencies()
            print(f"📁 Project now has {len(self.project_files)} files")

    def _add_route_to_app(self, path: str, component: str, icon: str, label: str):
        """Automatically add a route to App.tsx and update sidebar"""
        # Update App.tsx with the route
        self._update_routes_in_app(path, component)
        
        # Update the sidebar with the new route
        self._update_sidebar_routes(path, component, icon, label)

    def _update_routes_in_app(self, path: str, component: str):
        """Add route to App.tsx Routes section"""
        app_file = self.project_dir / 'src' / 'App.tsx'
        if not app_file.exists():
            return
        
        with open(app_file, 'r') as f:
            content = f.read()
        
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
        
        # Write updated content
        with open(app_file, 'w') as f:
            f.write(content)

    def _update_sidebar_routes(self, path: str, component: str, icon: str, label: str):
        """Add route to AppSidebar component"""
        sidebar_file = self.project_dir / 'src' / 'components' / 'app-sidebar.tsx'
        if not sidebar_file.exists():
            return
        
        with open(sidebar_file, 'r') as f:
            content = f.read()
        
        # Add icon import if not present
        if f'{icon}' not in content:
            # Find the lucide-react import line and add the icon
            lucide_import_pattern = r"import { ([^}]+) } from 'lucide-react'"
            match = re.search(lucide_import_pattern, content)
            if match:
                current_imports = match.group(1)
                new_imports = f"{current_imports}, {icon}"
                content = content.replace(match.group(0), f"import {{ {new_imports} }} from 'lucide-react'")
        
        # Add new route to baseRoutes array (only if it doesn't exist)
        if f"url: '{path}'" not in content:
            # Find the baseRoutes array and add the new route
            routes_pattern = r'(const baseRoutes = \[.*?)(])'
            routes_match = re.search(routes_pattern, content, re.DOTALL)
            if routes_match:
                routes_content = routes_match.group(1)
                new_route_entry = f"""  {{
    title: '{label}',
    url: '{path}',
    icon: {icon},
  }},
"""
                updated_routes = f"{routes_content}{new_route_entry}"
                content = content.replace(routes_match.group(1), updated_routes)
        
        # Write updated content
        with open(sidebar_file, 'w') as f:
            f.write(content)

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
                            
                            # Skip path aliases
                            if import_name.startswith('@/'):
                                continue
                            
                            # Skip Node.js built-in modules
                            builtin_modules = {'path', 'fs', 'url', 'util', 'crypto', 'os', 'http', 'https', 'stream'}
                            if import_name in builtin_modules:
                                continue
                            
                            # Extract package name
                            if import_name.startswith('@'):
                                # Scoped package
                                parts = import_name.split('/')
                                if len(parts) >= 2:
                                    package_name = f"{parts[0]}/{parts[1]}"
                                else:
                                    package_name = import_name
                            else:
                                # Regular package
                                package_name = import_name.split('/')[0]
                            
                            needed_packages.add(package_name)
                    
                    except Exception as e:
                        print(f"⚠️ Error scanning {file_info['path']}: {e}")
            
            # Find missing packages
            missing_packages = needed_packages - all_current
            
            if missing_packages:
                print(f"📦 Adding missing dependencies to package.json: {', '.join(missing_packages)}")
                
                # Add missing packages
                if 'dependencies' not in package_data:
                    package_data['dependencies'] = {}
                
                for pkg in missing_packages:
                    package_data['dependencies'][pkg] = 'latest'
                
                # Write updated package.json
                with open(package_json_path, 'w') as f:
                    json.dump(package_data, f, indent=2)
                
                print(f"✅ Added {len(missing_packages)} packages to package.json")
                print("💡 Run 'npm install' to install the new dependencies")
            
        except Exception as e:
            print(f"⚠️ Error checking dependencies: {e}")

def main():
    """Demo the bolt.diy style system"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable not set")
        return
    
    # Create system with custom project name
    system = BoltStyleGroq(api_key, "bolt_style_dashboard")
    
    print("\n" + "="*60)
    print("🚀 Bolt.diy Style Groq System")
    print("="*60)
    print("This system:")
    print("✅ Uses bolt.diy prompt structure and design philosophy")
    print("✅ Creates professional, production-ready UI")
    print("✅ Includes rich, realistic data")
    print("✅ Implements sophisticated visual design")
    print()
    
    # Demo request
    request = "Create an analytics dashboard with cards showing revenue, users, and sales. Also add a section that shows our top users in a table."
    
    print(f"\n📝 User Request: {request}")
    print("="*50)
    
    response = system.send_message(request)
    
    # Show clean response
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
        print(f"\n🤖 Model Response:\n{clean_response}")
    
    print(f"\n📊 Project Status: {len(system.project_files)} files")

if __name__ == "__main__":
    main()