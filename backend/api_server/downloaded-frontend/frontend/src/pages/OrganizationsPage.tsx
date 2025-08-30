import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { 
  Users, 
  Plus, 
  UserPlus,
  Building
} from 'lucide-react'
import { useTaskStore } from '@/stores/taskStore'

export default function OrganizationsPage() {
  const { organizations, loading, fetchOrganizations, createOrganization, inviteMember } = useTaskStore()
  const [open, setOpen] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [selectedOrg, setSelectedOrg] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [email, setEmail] = useState('')

  useEffect(() => {
    fetchOrganizations()
  }, [fetchOrganizations])

  const handleCreateOrg = async () => {
    if (!name.trim()) return
    
    const success = await createOrganization({
      name,
      description: description || null
    })
    
    if (success) {
      setOpen(false)
      setName('')
      setDescription('')
    }
  }

  const handleInviteMember = async () => {
    if (!selectedOrg || !email.trim()) return
    
    const success = await inviteMember(selectedOrg, email, 'member')
    
    if (success) {
      setInviteOpen(false)
      setEmail('')
      setSelectedOrg(null)
    }
  }

  return (
    <div className="flex-1 p-6">
      <div className="flex flex-col space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Organizations</h1>
            <p className="text-muted-foreground">Manage your teams and organizations</p>
          </div>
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Organization
          </Button>
        </div>

        {/* Organizations List */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {organizations.map((org) => (
            <Card key={org.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center">
                  <div className="bg-primary rounded-sm w-12 h-12 flex items-center justify-center mr-4">
                    <span className="text-lg text-primary-foreground font-bold">
                      {org.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <CardTitle className="text-lg">{org.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {org.description || 'No description'}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">
                    Created {new Date(org.created_at).toLocaleDateString()}
                  </span>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      setSelectedOrg(org.id)
                      setInviteOpen(true)
                    }}
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    Invite
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {organizations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12">
            <Building className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No organizations</h3>
            <p className="text-muted-foreground mb-4">
              Create your first organization to start collaborating with your team.
            </p>
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Organization
            </Button>
          </div>
        )}
      </div>

      {/* Create Organization Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Organization</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Organization Name</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Acme Inc."
              />
            </div>
            <div>
              <label className="text-sm font-medium">Description</label>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Description of your organization"
              />
            </div>
            <Button onClick={handleCreateOrg} disabled={!name.trim() || loading}>
              {loading ? 'Creating...' : 'Create Organization'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Invite Member Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Member</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Email Address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
              />
            </div>
            <Button onClick={handleInviteMember} disabled={!email.trim() || loading}>
              {loading ? 'Inviting...' : 'Send Invitation'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}