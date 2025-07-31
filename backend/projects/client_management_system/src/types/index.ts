export interface Lead {
  id: string
  company: string
  contactName: string
  email: string
  phone: string
  value: number
  stage: 'prospect' | 'qualified' | 'proposal' | 'negotiation' | 'won' | 'lost'
  source: string
  lastContact: Date
  nextAction: string
  notes: string
  createdAt: Date
  updatedAt: Date
}

export interface Client {
  id: string
  company: string
  contactName: string
  email: string
  phone: string
  address: string
  website: string
  industry: string
  annualRevenue: number
  status: 'active' | 'inactive' | 'prospect'
  createdAt: Date
  updatedAt: Date
}

export interface Project {
  id: string
  clientId: string
  name: string
  description: string
  status: 'planning' | 'active' | 'on-hold' | 'completed' | 'cancelled'
  startDate: Date
  endDate: Date
  budget: number
  hourlyRate: number
  milestones: Milestone[]
  timeEntries: TimeEntry[]
  createdAt: Date
  updatedAt: Date
}

export interface Milestone {
  id: string
  name: string
  description: string
  dueDate: Date
  completed: boolean
  completedAt?: Date
}

export interface TimeEntry {
  id: string
  projectId: string
  description: string
  hours: number
  date: Date
  billable: boolean
  rate: number
  createdAt: Date
}

export interface Invoice {
  id: string
  clientId: string
  projectId?: string
  number: string
  issueDate: Date
  dueDate: Date
  items: InvoiceItem[]
  subtotal: number
  tax: number
  total: number
  paid: number
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
  notes: string
  createdAt: Date
  updatedAt: Date
}

export interface InvoiceItem {
  id: string
  description: string
  quantity: number
  rate: number
  amount: number
}

export interface Communication {
  id: string
  clientId: string
  type: 'email' | 'call' | 'meeting' | 'note'
  subject: string
  content: string
  date: Date
  direction: 'inbound' | 'outbound'
  createdAt: Date
}

export interface DashboardStats {
  totalRevenue: number
  outstandingInvoices: number
  activeProjects: number
  newLeads: number
  monthlyRevenue: number[]
  projectProfitability: Array<{
    projectId: string
    name: string
    revenue: number
    cost: number
    profit: number
  }>
}