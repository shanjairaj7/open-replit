import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useProjectStore } from '@/stores/project-store'
import { useEffect } from 'react'
import { 
  Calendar, 
  User, 
  MessageSquare, 
  Paperclip, 
  Plus, 
  Edit3, 
  Trash2,
  CheckCircle,
  Circle
} from 'lucide-react'

export default function TaskDetailPage() {
  const [comment, setComment] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState('Design homepage')
  const [editedDescription, setEditedDescription] = useState('Create wireframes and mockups for the homepage')
  const [editedStatus, setEditedStatus] = useState('In Progress')
  const [editedAssignee, setEditedAssignee] = useState('John Doe')

  const { currentTask, comments, fetchComments, createComment, updateTask } = useProjectStore()

  useEffect(() => {
    if (currentTask) {
      fetchComments(currentTask.id)
      setEditedTitle(currentTask.title)
      setEditedDescription(currentTask.description)
      setEditedStatus(currentTask.status)
    }
  }, [currentTask])


  const handleAddComment = async () => {
    if (comment.trim() && currentTask) {
      await createComment(comment, currentTask.id)
      setComment('')
    }
  }

  const handleSaveChanges = async () => {
    if (currentTask) {
      await updateTask(currentTask.id, {
        title: editedTitle,
        description: editedDescription,
        status: editedStatus,
        assigned_to: editedAssignee ? 1 : null // This would be the actual user ID in a real app
      })
      setIsEditing(false)
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'To Do': return 'secondary'
      case 'In Progress': return 'default'
      case 'Done': return 'outline'
      default: return 'secondary'
    }
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-start mb-6">
          <div>
            {isEditing ? (
              <Input
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                className="text-3xl font-bold mb-2"
              />
            ) : (
              <h1 className="text-3xl font-bold mb-2">Design homepage</h1>
            )}
            <div className="flex items-center space-x-4">
              <Badge variant={getStatusBadgeVariant('In Progress')}>In Progress</Badge>
              <div className="flex items-center text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                <span>Due Jun 15, 2023</span>
              </div>
            </div>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" size="sm">
              <Paperclip className="h-4 w-4 mr-2" />
              Attach
            </Button>
            {isEditing ? (
              <Button onClick={handleSaveChanges} size="sm">
                Save Changes
              </Button>
            ) : (
              <Button onClick={() => setIsEditing(true)} size="sm">
                <Edit3 className="h-4 w-4 mr-2" />
                Edit
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                {isEditing ? (
                  <Textarea
                    value={editedDescription}
                    onChange={(e) => setEditedDescription(e.target.value)}
                    className="min-h-[120px]"
                  />
                ) : (
                  <p className="text-muted-foreground">
                    Create wireframes and mockups for the homepage. Focus on mobile-first design and ensure 
                    all key elements are included. Review with the design team before finalizing.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageSquare className="h-5 w-5 mr-2" />
                  Comments (2)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {comments.map((comment) => (
                    <div key={comment.id} className="flex space-x-4">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src="/placeholder-user.jpg" />
                        <AvatarFallback>
                          <User className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="bg-muted rounded-lg p-4">
                          <div className="flex justify-between">
                            <span className="font-medium">{comment.author}</span>
                            <span className="text-sm text-muted-foreground">{comment.timestamp}</span>
                          </div>
                          <p className="mt-2">{comment.content}</p>
                        </div>
                      </div>
                    </div>
                  ))}

                  <div className="flex space-x-4">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src="/placeholder-user.jpg" />
                      <AvatarFallback>
                        <User className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="border rounded-lg p-4">
                        <Textarea
                          placeholder="Add a comment..."
                          value={comment}
                          onChange={(e) => setComment(e.target.value)}
                          className="min-h-[80px] mb-3"
                        />
                        <div className="flex justify-between">
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm">
                              <Paperclip className="h-4 w-4 mr-2" />
                              Attach
                            </Button>
                          </div>
                          <Button onClick={handleAddComment} size="sm">
                            Comment
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Task Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-muted-foreground">Assignee</Label>
                  {isEditing ? (
                    <Select value={editedAssignee} onValueChange={setEditedAssignee}>
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select assignee" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="John Doe">John Doe</SelectItem>
                        <SelectItem value="Jane Smith">Jane Smith</SelectItem>
                        <SelectItem value="Bob Johnson">Bob Johnson</SelectItem>
                        <SelectItem value="Alice Brown">Alice Brown</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="flex items-center mt-1">
                      <Avatar className="h-6 w-6 mr-2">
                        <AvatarImage src="/placeholder-user.jpg" />
                        <AvatarFallback>
                          <User className="h-3 w-3" />
                        </AvatarFallback>
                      </Avatar>
                      <span>John Doe</span>
                    </div>
                  )}
                </div>

                <div>
                  <Label className="text-muted-foreground">Status</Label>
                  {isEditing ? (
                    <Select value={editedStatus} onValueChange={setEditedStatus}>
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="To Do">To Do</SelectItem>
                        <SelectItem value="In Progress">In Progress</SelectItem>
                        <SelectItem value="Done">Done</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="mt-1">
                      <Badge variant={getStatusBadgeVariant('In Progress')}>
                        In Progress
                      </Badge>
                    </div>
                  )}
                </div>

                <div>
                  <Label className="text-muted-foreground">Priority</Label>
                  <div className="mt-1">
                    <Badge variant="destructive">High</Badge>
                  </div>
                </div>

                <div>
                  <Label className="text-muted-foreground">Created</Label>
                  <div className="mt-1">Jun 1, 2023</div>
                </div>

                <div>
                  <Label className="text-muted-foreground">Last Updated</Label>
                  <div className="mt-1">Jun 5, 2023</div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Attachments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-2 rounded-md border">
                    <div className="flex items-center">
                      <div className="bg-muted p-2 rounded-md mr-3">
                        <Paperclip className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium">homepage-wireframes.pdf</div>
                        <div className="text-sm text-muted-foreground">2.4 MB</div>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-md border">
                    <div className="flex items-center">
                      <div className="bg-muted p-2 rounded-md mr-3">
                        <Paperclip className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium">design-notes.docx</div>
                        <div className="text-sm text-muted-foreground">1.1 MB</div>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <Button variant="outline" className="w-full">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Attachment
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}