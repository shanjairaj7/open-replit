import { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useTaskStore } from '@/stores/taskStore'
import { useNavigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  CheckSquare, 
  Users, 
  Calendar,
  MessageSquare,
  Plus
} from 'lucide-react'

/**
 * PROJECT MANAGEMENT DASHBOARD
 * 
 * Main dashboard for the project management application
 * 
 * Features:
 * - Task overview and statistics
 * - Quick navigation to key features
 * - Recent activity feed
 */

export default function HomePage() {
  const { tasks, organizations, fetchTasks, fetchOrganizations } = useTaskStore()
  const navigate = useNavigate()

  useEffect(() => {
    fetchTasks()
    fetchOrganizations()
  }, [fetchTasks, fetchOrganizations])

  const stats = {
    totalTasks: tasks.length,
    completedTasks: tasks.filter(t => t.status === 'Done').length,
    inProgressTasks: tasks.filter(t => t.status === 'In Progress').length,
    todoTasks: tasks.filter(t => t.status === 'To Do').length,
    organizations: organizations.length
  }

  return (
    <div className="flex-1 p-6">
      <div className="flex flex-col space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground">Welcome to your project management workspace</p>
          </div>
          <Button onClick={() => navigate('/tasks')}>
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
              <CheckSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalTasks}</div>
              <p className="text-xs text-muted-foreground">
                {stats.completedTasks} completed
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">To Do</CardTitle>
              <div className="h-4 w-4 rounded-full bg-blue-500"></div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.todoTasks}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <div className="h-4 w-4 rounded-full bg-yellow-500"></div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.inProgressTasks}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <div className="h-4 w-4 rounded-full bg-green-500"></div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.completedTasks}</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}