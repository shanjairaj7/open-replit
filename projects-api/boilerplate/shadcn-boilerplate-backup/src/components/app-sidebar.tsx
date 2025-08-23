import { useLocation } from 'react-router-dom'
import { Home } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

// Route groups for organized sidebar
const routeGroups = [
  {
    title: "Overview",
    items: [
      { title: "Home", url: "/", icon: Home },
    ]
  },
]

export function AppSidebar() {
  const location = useLocation()

  const isActiveRoute = (url: string) => {
    if (url === "/") return location.pathname === "/"
    if (url.includes(":")) {
      // Handle parameterized routes like /users/:id
      const baseRoute = url.split("/:")[0]
      return location.pathname.startsWith(baseRoute)
    }
    return location.pathname === url || location.pathname.startsWith(url + "/")
  }

  return (
    <Sidebar>
      <SidebarContent>
        {routeGroups.map((group) => (
          <SidebarGroup key={group.title}>
            <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild
                      isActive={isActiveRoute(item.url)}
                    >
                      <a href={item.url}>
                        <item.icon />
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
    </Sidebar>
  )
}