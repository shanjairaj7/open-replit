import { Link, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { 
  LayoutDashboard, 
  CheckSquare, 
  Users, 
  Building,
  MessageSquare,
  Settings,
  PlusCircle
} from 'lucide-react'
import { useTaskStore } from '@/stores/taskStore'
import { useAuthStore } from '@/stores/auth-store'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

export default function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { organizations } = useTaskStore()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="flex flex-col w-64 bg-background border-r border-border h-screen fixed">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-xl font-bold text-foreground">ProjectFlow</h1>
        <p className="text-sm text-muted-foreground">Project Management</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4">
        <ul className="space-y-1">
          <li>
            <Link to="/">
              <Button 
                variant={isActive("/") ? "secondary" : "ghost"} 
                className="w-full justify-start"
              >
                <LayoutDashboard className="mr-2 h-4 w-4" />
                Dashboard
              </Button>
            </Link>
          </li>
          <li>
            <Link to="/tasks">
              <Button 
                variant={isActive("/tasks") ? "secondary" : "ghost"} 
                className="w-full justify-start"
              >
                <CheckSquare className="mr-2 h-4 w-4" />
                Tasks
              </Button>
            </Link>
          </li>
          <li>
            <Link to="/organizations">
              <Button 
                variant={isActive("/organizations") ? "secondary" : "ghost"} 
                className="w-full justify-start"
              >
                <Building className="mr-2 h-4 w-4" />
                Organizations
              </Button>
            </Link>
          </li>
          <li>
            <Link to="/team">
              <Button 
                variant={isActive("/team") ? "secondary" : "ghost"} 
                className="w-full justify-start"
              >
                <Users className="mr-2 h-4 w-4" />
                Team
              </Button>
            </Link>
          </li>
          <li>
            <Link to="/messages">
              <Button 
                variant={isActive("/messages") ? "secondary" : "ghost"} 
                className="w-full justify-start"
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Messages
              </Button>
            </Link>
          </li>
        </ul>

        {/* Organizations Section */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-muted-foreground">ORGANIZATIONS</h3>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => window.location.href = '/organizations'}>
              <PlusCircle className="h-4 w-4" />
            </Button>
          </div>
          <ul className="space-y-1">
            {organizations.map((org) => (
              <li key={org.id}>
                <Button variant="ghost" className="w-full justify-start">
                  <div className="flex items-center">
                    <div className="bg-primary rounded-sm w-6 h-6 flex items-center justify-center mr-2">
                      <span className="text-xs text-primary-foreground font-bold">
                        {org.name.charAt(0)}
                      </span>
                    </div>
                    <span className="truncate">{org.name}</span>
                  </div>
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-border">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="w-full justify-between">
              <div className="flex items-center">
                <Avatar className="h-8 w-8 mr-2">
                  <AvatarFallback>
                    {user?.name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="truncate">{user?.name}</span>
              </div>
              <Settings className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.name}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/profile">Profile</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/settings">Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => logout()}>
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}