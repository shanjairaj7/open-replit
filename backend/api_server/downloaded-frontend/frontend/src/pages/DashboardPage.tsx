import { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  LayoutDashboard, 
  CheckSquare, 
  Users, 
  Calendar,
  MessageSquare,
  Plus
} from 'lucide-react'
import { useTaskStore } from '@/stores/taskStore'
import { useNavigate } from 'react-router-dom'

export default function DashboardPage() {
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

        {/* Recent Tasks */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center">
                <CheckSquare className="h-4 w-4 mr-2" />
                Recent Tasks
              </CardTitle>
            </CardHeader>
            <CardContent>
              {tasks.length > 0 ? (
                <div className="space-y-4">
                  {tasks.slice(0, 5).map((task) => (
                    <div key={task.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <h3 className="font-medium">{task.title}</h3>
                        <p className="text-sm text-muted-foreground">{task.description}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs px-2 py-1 bg-muted rounded">
                          {task.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <CheckSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No tasks yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Get started by creating your first task.
                  </p>
                  <Button onClick={() => navigate('/tasks')}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Task
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Organizations */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Users className="h-4 w-4 mr-2" />
                  Organizations
                </CardTitle>
              </CardHeader>
              <CardContent>
                {organizations.length > 0 ? (
                  <div className="space-y-3">
                    {organizations.map((org) => (
                      <div key={org.id} className="flex items-center p-3 border rounded-lg">
                        <div className="bg-primary rounded-sm w-10 h-10 flex items-center justify-center mr-3">
                          <span className="text-sm text-primary-foreground font-bold">
                            {org.name.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-medium">{org.name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {org.description || 'No description'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <Users className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">
                      No organizations yet
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <LayoutDashboard className="h-4 w-4 mr-2" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/tasks')}>
                  <CheckSquare className="h-4 w-4 mr-2" />
                  View All Tasks
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/calendar')}>
                  <Calendar className="h-4 w-4 mr-2" />
                  Open Calendar
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/team')}>
                  <Users className="h-4 w-4 mr-2" />
                  Manage Team
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/messages')}>
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Send Message
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}