import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { Lead } from '@/types'
import { mockLeads } from '@/lib/mockData'
import { Plus, Search, Mail, Phone, MoreVertical } from 'lucide-react'

const stageColors = {
  prospect: 'bg-gray-100 text-gray-800',
  qualified: 'bg-blue-100 text-blue-800',
  proposal: 'bg-yellow-100 text-yellow-800',
  negotiation: 'bg-orange-100 text-orange-800',
  won: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800'
}

export default function Leads() {
  const [leads, setLeads] = useLocalStorage<Lead[]>('leads', mockLeads)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStage, setFilterStage] = useState<string>('all')

  const filteredLeads = leads.filter(lead => {
    const matchesSearch = lead.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         lead.contactName.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStage = filterStage === 'all' || lead.stage === filterStage
    return matchesSearch && matchesStage
  })

  const updateLeadStage = (leadId: string, newStage: Lead['stage']) => {
    setLeads(leads.map(lead => 
      lead.id === leadId ? { ...lead, stage: newStage, updatedAt: new Date() } : lead
    ))
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
          <p className="text-muted-foreground">Manage your sales pipeline</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Lead
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search leads..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filterStage} onValueChange={setFilterStage}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="prospect">Prospect</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="proposal">Proposal</SelectItem>
                <SelectItem value="negotiation">Negotiation</SelectItem>
                <SelectItem value="won">Won</SelectItem>
                <SelectItem value="lost">Lost</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium text-sm">Company</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Contact</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Value</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Stage</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Last Contact</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead) => (
                  <tr key={lead.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium">{lead.company}</p>
                        <p className="text-sm text-muted-foreground">{lead.source}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-sm">{lead.contactName}</p>
                        <p className="text-sm text-muted-foreground">{lead.email}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium">
                      ${lead.value.toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <Select
                        value={lead.stage}
                        onValueChange={(value) => updateLeadStage(lead.id, value as Lead['stage'])}
                      >
                        <SelectTrigger className="w-[120px] h-8">
                          <Badge className={stageColors[lead.stage]}>
                            {lead.stage.charAt(0).toUpperCase() + lead.stage.slice(1)}
                          </Badge>
                        </SelectTrigger>
                        <SelectContent>
                          {Object.keys(stageColors).map((stage) => (
                            <SelectItem key={stage} value={stage}>
                              {stage.charAt(0).toUpperCase() + stage.slice(1)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="py-3 px-4 text-sm text-muted-foreground">
                      {new Date(lead.lastContact).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm">
                          <Mail className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Phone className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}