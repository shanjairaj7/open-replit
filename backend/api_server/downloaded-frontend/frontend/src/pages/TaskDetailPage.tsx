import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { 
  Calendar, 
  User, 
  MessageSquare, 
  Edit, 
  Trash2, 
  X,
  Send
} from 'lucide-react'
import { useTaskStore } from '@/stores/taskStore'
import { format } from 'date-fns'
import { useAuthStore } from '@/stores/auth-store'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { tasks, comments, loading, fetchTasks, fetchComments, updateTask, deleteTask, createComment } = useTaskStore()
  const { user } = useAuthStore()
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editStatus, setEditStatus] = useState('')
  const [editDueDate, setEditDueDate] = useState('')
  const [comment, setComment] = useState('')
  const [deleting, setDeleting] = useState(false)

  const task = tasks.find(t => t.id === parseInt(id || '0'))

  useEffect(() => {
    if (id) {
      fetchTasks()
      fetchComments(parseInt(id))
    }
  }, [id, fetchTasks, fetchComments])

  useEffect(() => {
    if (task) {
      setEditTitle(task.title)
      setEditDescription(task.description || '')
      setEditStatus(task.status)
      setEditDueDate(task.due_date ? task.due_date.split('T')[0] : '')
    }
  }, [task])

  const handleUpdateTask = async () => {
    if (!task) return
    
    const success = await updateTask(task.id, {
      title: editTitle,
      description: editDescription || null,
      status: editStatus,
      due_date: editDueDate ? `${editDueDate}T00:00:00` : null
    })
    
    if (success) {
      setIsEditing(false)
    }
  }

  const handleDeleteTask = async () => {
    if (!task) return
    
    const success = await deleteTask(task.id)
    if (success) {
      navigate('/tasks')
    }
  }

  const handleAddComment = async () => {
    if (!task || !comment.trim()) return
    
    const success = await createComment({
      content: comment,
      task_id: task.id
    })
    
    if (success) {
      setComment('')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'To Do': return 'bg-blue-100 text-blue-800'
      case 'In Progress': return 'bg-yellow-100 text-yellow-800'
      case 'Done': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (!task) {
    return (
      <div className="flex-1 p-6">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <X className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Task not found</h2>
            <p className="text-muted-foreground mb-4">The task you're looking for doesn't exist or has been deleted.</p>
            <Button onClick={() => navigate('/tasks')}>Back to Tasks</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={() => navigate('/tasks')}>
            ← Back to Tasks
          </Button>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button variant="destructive" onClick={() => setDeleting(true)}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        {/* Task Details */}
        <Card className="mb-6">
          <CardHeader>
            {isEditing ? (
              <div className="space-y-4">
                <Input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="text-2xl font-bold"
                />
                <Textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Task description"
                  className="min-h-[100px]"
                />
                <div className="flex flex-wrap gap-4">
                  <div className="flex-1 min-w-[200px]">
                    <label className="text-sm font-medium">Status</label>
                    <Select value={editStatus} onValueChange={setEditStatus}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="To Do">To Do</SelectItem>
                        <SelectItem value="In Progress">In Progress</SelectItem>
                        <SelectItem value="Done">Done</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label className="text-sm font-medium">Due Date</label>
                    <Input
                      type="date"
                      value={editDueDate}
                      onChange={(e) => setEditDueDate(e.target.value)}
                    />
                  </div>
                </div>
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleUpdateTask} disabled={loading}>
                    {loading ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-2xl">{task.title}</CardTitle>
                  <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
                </div>
                {task.description && (
                  <p className="text-muted-foreground">{task.description}</p>
                )}
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center">
                    <Calendar className="h-4 w-4 mr-2" />
                    <span>
                      {task.due_date 
                        ? `Due ${format(new Date(task.due_date), 'MMM d, yyyy')}` 
                        : 'No due date'}
                    </span>
                  </div>
                  <div className="flex items-center">
                    <User className="h-4 w-4 mr-2" />
                    <span>Created by you</span>
                  </div>
                  <div className="flex items-center">
                    <Calendar className="h-4 w-4 mr-2" />
                    <span>
                      Created {format(new Date(task.created_at), 'MMM d, yyyy')}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </CardHeader>
        </Card>

        {/* Comments Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <MessageSquare className="h-5 w-5 mr-2" />
              Comments ({comments[task.id]?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Add Comment */}
            <div className="flex space-x-4 mb-6">
              <div className="flex-1">
                <Textarea
                  placeholder="Add a comment..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={handleAddComment} disabled={!comment.trim() || loading}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Comments List */}
            <div className="space-y-4">
              {comments[task.id]?.map((comment) => (
                <div key={comment.id} className="flex space-x-4 p-4 border rounded-lg">
                  <div className="flex-shrink-0">
                    <div className="bg-primary rounded-full w-10 h-10 flex items-center justify-center">
                      <span className="text-primary-foreground font-medium">
                        {user?.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center mb-1">
                      <h4 className="font-medium">{user?.name}</h4>
                      <span className="text-xs text-muted-foreground ml-2">
                        {format(new Date(comment.created_at), 'MMM d, yyyy h:mm a')}
                      </span>
                    </div>
                    <p className="text-muted-foreground">{comment.content}</p>
                  </div>
                </div>
              ))}
              
              {(!comments[task.id] || comments[task.id].length === 0) && (
                <div className="text-center py-8">
                  <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No comments yet</h3>
                  <p className="text-muted-foreground">
                    Be the first to comment on this task.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleting} onOpenChange={setDeleting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Task</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Are you sure you want to delete this task? This action cannot be undone.</p>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setDeleting(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDeleteTask} disabled={loading}>
                {loading ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}