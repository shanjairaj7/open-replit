import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { Project } from '@/types'
import { mockProjects, mockClients } from '@/lib/mockData'
import { Plus, Clock, DollarSign, CheckCircle, AlertCircle } from 'lucide-react'

const statusColors = {
  planning: 'bg-gray-100 text-gray-800',
  active: 'bg-green-100 text-green-800',
  'on-hold': 'bg-yellow-100 text-yellow-800',
  completed: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-red-100 text-red-800'
}

export default function Projects() {
  const [projects] = useLocalStorage<Project[]>('projects', mockProjects)
  const [clients] = useLocalStorage('clients', mockClients)
  const [activeTab, setActiveTab] = useState('all')

  const getClient = (clientId: string) => clients.find(c => c.id === clientId)

  const filteredProjects = projects.filter(project => {
    if (activeTab === 'all') return true
    return project.status === activeTab
  })

  const calculateProgress = (project: Project) => {
    const completed = project.milestones.filter(m => m.completed).length
    return (completed / project.milestones.length) * 100
  }

  const calculateRevenue = (project: Project) => {
    const totalHours = project.timeEntries.reduce((sum, entry) => sum + entry.hours, 0)
    return totalHours * project.hourlyRate
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Track your ongoing engagements</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">All Projects</TabsTrigger>
          <TabsTrigger value="planning">Planning</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredProjects.map((project) => {
              const client = getClient(project.clientId)
              const progress = calculateProgress(project)
              const revenue = calculateRevenue(project)

              return (
                <Card key={project.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{project.name}</CardTitle>
                        <p className="text-sm text-muted-foreground">{client?.company}</p>
                      </div>
                      <Badge className={statusColors[project.status]}>
                        {project.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Progress</span>
                        <span>{Math.round(progress)}%</span>
                      </div>
                      <Progress value={progress} className="h-2" />
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex items-center">
                        <Clock className="h-4 w-4 mr-1 text-muted-foreground" />
                        <span>{project.milestones.filter(m => !m.completed).length} open tasks</span>
                      </div>
                      <div className="flex items-center">
                        <DollarSign className="h-4 w-4 mr-1 text-muted-foreground" />
                        <span>${revenue.toLocaleString()} earned</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-sm text-muted-foreground">
                        Due {new Date(project.endDate).toLocaleDateString()}
                      </div>
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}