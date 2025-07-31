import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  DollarSign, 
  Users, 
  FileText, 
  TrendingUp, 
  Clock, 
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { Lead, Project, Invoice } from '@/types'
import { mockLeads, mockProjects, mockInvoices } from '@/lib/mockData'

export default function Dashboard() {
  const [leads] = useLocalStorage<Lead[]>('leads', mockLeads)
  const [projects] = useLocalStorage<Project[]>('projects', mockProjects)
  const [invoices] = useLocalStorage<Invoice[]>('invoices', mockInvoices)
  const [stats, setStats] = useState({
    totalRevenue: 0,
    outstandingInvoices: 0,
    activeProjects: 0,
    newLeads: 0,
    monthlyRevenue: [12000, 15000, 18000, 22000, 25000, 28000]
  })

  useEffect(() => {
    const totalRevenue = invoices
      .filter(inv => inv.status === 'paid')
      .reduce((sum, inv) => sum + inv.total, 0)

    const outstandingInvoices = invoices
      .filter(inv => inv.status === 'sent' || inv.status === 'overdue')
      .reduce((sum, inv) => sum + (inv.total - inv.paid), 0)

    const activeProjects = projects.filter(p => p.status === 'active').length
    const newLeads = leads.filter(l => {
      const daysSinceCreated = (new Date().getTime() - l.createdAt.getTime()) / (1000 * 60 * 60 * 24)
      return daysSinceCreated <= 7
    }).length

    setStats({
      totalRevenue,
      outstandingInvoices,
      activeProjects,
      newLeads,
      monthlyRevenue: stats.monthlyRevenue
    })
  }, [invoices, projects, leads])

  const StatCard = ({ 
    title, 
    value, 
    icon: Icon, 
    trend, 
    trendValue 
  }: {
    title: string
    value: string | number
    icon: any
    trend?: 'up' | 'down'
    trendValue?: string
  }) => (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <p className="text-xs text-muted-foreground flex items-center mt-1">
            {trend === 'up' ? (
              <ArrowUpRight className="h-3 w-3 mr-1 text-green-500" />
            ) : (
              <ArrowDownRight className="h-3 w-3 mr-1 text-red-500" />
            )}
            {trendValue}
          </p>
        )}
      </CardContent>
    </Card>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here's your business overview.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Revenue"
          value={`$${stats.totalRevenue.toLocaleString()}`}
          icon={DollarSign}
          trend="up"
          trendValue="+12% from last month"
        />
        <StatCard
          title="Outstanding"
          value={`$${stats.outstandingInvoices.toLocaleString()}`}
          icon={Clock}
          trend="down"
          trendValue="-5% from last week"
        />
        <StatCard
          title="Active Projects"
          value={stats.activeProjects}
          icon={FileText}
          trend="up"
          trendValue="+2 new this week"
        />
        <StatCard
          title="New Leads"
          value={stats.newLeads}
          icon={Users}
          trend="up"
          trendValue="+3 this week"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle>Revenue Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.monthlyRevenue.map((revenue, index) => (
                <div key={index} className="flex items-center">
                  <div className="w-12 text-sm text-muted-foreground">
                    {new Date(2024, index, 1).toLocaleString('default', { month: 'short' })}
                  </div>
                  <div className="flex-1 mx-4">
                    <Progress value={(revenue / 30000) * 100} className="h-2" />
                  </div>
                  <div className="w-20 text-sm font-medium">
                    ${revenue.toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-3" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Invoice INV-2024-001 paid</p>
                  <p className="text-xs text-muted-foreground">2 hours ago</p>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-3" />
                <div className="flex-1">
                  <p className="text-sm font-medium">New lead from TechCorp</p>
                  <p className="text-xs text-muted-foreground">5 hours ago</p>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-yellow-500 rounded-full mr-3" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Project milestone completed</p>
                  <p className="text-xs text-muted-foreground">1 day ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upcoming Deadlines</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Proposal - TechCorp</p>
                  <p className="text-xs text-muted-foreground">Due in 2 days</p>
                </div>
                <Badge variant="outline" className="text-xs">High</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Invoice - RetailGiant</p>
                  <p className="text-xs text-muted-foreground">Due in 5 days</p>
                </div>
                <Badge variant="outline" className="text-xs">Medium</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <Button variant="outline" className="w-full">
                <Users className="h-4 w-4 mr-2" />
                New Lead
              </Button>
              <Button variant="outline" className="w-full">
                <FileText className="h-4 w-4 mr-2" />
                New Project
              </Button>
              <Button variant="outline" className="w-full">
                <DollarSign className="h-4 w-4 mr-2" />
                New Invoice
              </Button>
              <Button variant="outline" className="w-full">
                <TrendingUp className="h-4 w-4 mr-2" />
                View Reports
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}