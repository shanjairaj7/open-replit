import { useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { 
  Home,
  BarChart3,
  Users,
  FolderKanban,
  UserCircle,
  FileText,
  TrendingUp,
  Settings
} from "lucide-react"
import { cn } from '@/lib/utils'

// Routes will be dynamically added here by the AI system
const routeGroups = [
  {
    title: "Overview",
    items: [
      { title: "Home", url: "/", icon: Home },
      { title: "Dashboard", url: "/dashboard", icon: BarChart3 },
    ]
  },
  {
    title: "Sales",
    items: [
      { title: "Leads", url: "/leads", icon: Users },
    ]
  },
  {
    title: "Operations",
    items: [
      { title: "Projects", url: "/projects", icon: FolderKanban },
      { title: "Clients", url: "/clients", icon: UserCircle },
    ]
  },
  {
    title: "Finance",
    items: [
      { title: "Invoices", url: "/invoices", icon: FileText },
    ]
  },
  {
    title: "Analytics",
    items: [
      { title: "Analytics", url: "/analytics", icon: TrendingUp },
    ]
  },
  {
    title: "System",
    items: [
      { title: "Settings", url: "/settings", icon: Settings },
    ]
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
            <h2 className="text-lg font-semibold">CRM System</h2>
            <p className="text-xs text-muted-foreground">v1.0.0</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-4">
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
}