import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { Invoice } from '@/types'
import { mockInvoices, mockClients } from '@/lib/mockData'
import { Plus, Download, Eye, Edit, Trash2 } from 'lucide-react'

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  sent: 'bg-blue-100 text-blue-800',
  paid: 'bg-green-100 text-green-800',
  overdue: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800'
}

export default function Invoices() {
  const [invoices] = useLocalStorage<Invoice[]>('invoices', mockInvoices)
  const [clients] = useLocalStorage('clients', mockClients)

  const getClient = (clientId: string) => clients.find(c => c.id === clientId)

  const getTotalOutstanding = () => {
    return invoices
      .filter(inv => inv.status === 'sent' || inv.status === 'overdue')
      .reduce((sum, inv) => sum + (inv.total - inv.paid), 0)
  }

  const getTotalPaid = () => {
    return invoices
      .filter(inv => inv.status === 'paid')
      .reduce((sum, inv) => sum + inv.total, 0)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
          <p className="text-muted-foreground">Manage billing and payments</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Invoice
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Outstanding</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getTotalOutstanding().toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">Across {invoices.filter(i => i.status === 'sent' || i.status === 'overdue').length} invoices</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Paid</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getTotalPaid().toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">This year</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${invoices.filter(i => i.status === 'overdue').reduce((sum, inv) => sum + (inv.total - inv.paid), 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {invoices.filter(i => i.status === 'overdue').length} invoices
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium text-sm">Invoice</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Client</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Due Date</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Amount</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => {
                  const client = getClient(invoice.clientId)
                  return (
                    <tr key={invoice.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div>
                          <p className="font-medium">{invoice.number}</p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(invoice.issueDate).toLocaleDateString()}
                          </p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {client?.company}
                      </td>
                      <td className="py-3 px-4">
                        {new Date(invoice.dueDate).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 font-medium">
                        ${invoice.total.toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={statusColors[invoice.status]}>
                          {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}