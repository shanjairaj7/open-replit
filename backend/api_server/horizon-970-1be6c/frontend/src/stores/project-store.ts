import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'
import { toast } from 'sonner'

const API_BASE_URL = import.meta.env.VITE_APP_BACKEND_URL || 'http://localhost:8000'

interface User {
  id: number
  name: string
  email: string
}

interface Organization {
  id: number
  name: string
  description: string
  owner_id: number
  created_at: string
}

interface Membership {
  id: number
  user_id: number
  organization_id: number
  role: string
  created_at: string
}

interface Task {
  id: number
  title: string
  description: string
  status: string
  created_by: number
  assigned_to: number | null
  organization_id: number
  created_at: string
  updated_at: string
}

interface Comment {
  id: number
  content: string
  task_id: number
  created_by: number
  created_at: string
}

interface ProjectState {
  organizations: Organization[]
  currentOrganization: Organization | null
  tasks: Task[]
  currentTask: Task | null
  comments: Comment[]
  members: User[]
  loading: boolean
  error: string | null

  // Organization actions
  createOrganization: (name: string, description: string) => Promise<boolean>
  fetchOrganizations: () => Promise<void>
  setCurrentOrganization: (org: Organization | null) => void
  inviteMember: (email: string, organizationId: number) => Promise<boolean>

  // Task actions
  createTask: (task: Omit<Task, 'id' | 'created_at' | 'updated_at'>) => Promise<boolean>
  fetchTasks: (organizationId: number) => Promise<void>
  updateTask: (id: number, updates: Partial<Task>) => Promise<boolean>
  deleteTask: (id: number) => Promise<boolean>
  setCurrentTask: (task: Task | null) => void

  // Comment actions
  createComment: (content: string, taskId: number) => Promise<boolean>
  fetchComments: (taskId: number) => Promise<void>

  // Utility actions
  clearError: () => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      organizations: [],
      currentOrganization: null,
      tasks: [],
      currentTask: null,
      comments: [],
      members: [],
      loading: false,
      error: null,

      // Organization actions
      createOrganization: async (name: string, description: string) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.post<Organization>(
            `${API_BASE_URL}/organizations/`,
            { name, description }
          )

          if (response.status === 200) {
            const newOrg = response.data
            set((state) => ({
              organizations: [...state.organizations, newOrg],
              loading: false
            }))
            toast.success('Organization created successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Create organization error:', error)
          let errorMessage = 'Failed to create organization. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      fetchOrganizations: async () => {
        set({ loading: true, error: null })
        try {
          const response = await axios.get<Organization[]>(
            `${API_BASE_URL}/organizations/`
          )

          if (response.status === 200) {
            set({ organizations: response.data, loading: false })
          }
        } catch (error: any) {
          console.error('Fetch organizations error:', error)
          let errorMessage = 'Failed to fetch organizations. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
      },

      setCurrentOrganization: (org) => {
        set({ currentOrganization: org })
      },

      inviteMember: async (email: string, organizationId: number) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.post(
            `${API_BASE_URL}/organizations/invite`,
            { email, organization_id: organizationId }
          )

          if (response.status === 200) {
            set({ loading: false })
            toast.success('Invitation sent successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Invite member error:', error)
          let errorMessage = 'Failed to send invitation. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      // Task actions
      createTask: async (task) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.post<Task>(
            `${API_BASE_URL}/tasks/`,
            task
          )

          if (response.status === 200) {
            const newTask = response.data
            set((state) => ({
              tasks: [...state.tasks, newTask],
              loading: false
            }))
            toast.success('Task created successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Create task error:', error)
          let errorMessage = 'Failed to create task. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      fetchTasks: async (organizationId: number) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.get<Task[]>(
            `${API_BASE_URL}/tasks/?organization_id=${organizationId}`
          )

          if (response.status === 200) {
            set({ tasks: response.data, loading: false })
          }
        } catch (error: any) {
          console.error('Fetch tasks error:', error)
          let errorMessage = 'Failed to fetch tasks. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
      },

      updateTask: async (id: number, updates: Partial<Task>) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.put<Task>(
            `${API_BASE_URL}/tasks/${id}`,
            updates
          )

          if (response.status === 200) {
            const updatedTask = response.data
            set((state) => ({
              tasks: state.tasks.map((task) =>
                task.id === id ? updatedTask : task
              ),
              loading: false
            }))
            toast.success('Task updated successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Update task error:', error)
          let errorMessage = 'Failed to update task. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      deleteTask: async (id: number) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.delete(
            `${API_BASE_URL}/tasks/${id}`
          )

          if (response.status === 200) {
            set((state) => ({
              tasks: state.tasks.filter((task) => task.id !== id),
              loading: false
            }))
            toast.success('Task deleted successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Delete task error:', error)
          let errorMessage = 'Failed to delete task. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      setCurrentTask: (task) => {
        set({ currentTask: task })
      },

      // Comment actions
      createComment: async (content: string, taskId: number) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.post<Comment>(
            `${API_BASE_URL}/tasks/${taskId}/comments`,
            { content }
          )

          if (response.status === 200) {
            const newComment = response.data
            set((state) => ({
              comments: [...state.comments, newComment],
              loading: false
            }))
            toast.success('Comment added successfully!')
            return true
          }
        } catch (error: any) {
          console.error('Create comment error:', error)
          let errorMessage = 'Failed to add comment. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      fetchComments: async (taskId: number) => {
        set({ loading: true, error: null })
        try {
          const response = await axios.get<Comment[]>(
            `${API_BASE_URL}/tasks/${taskId}/comments`
          )

          if (response.status === 200) {
            set({ comments: response.data, loading: false })
          }
        } catch (error: any) {
          console.error('Fetch comments error:', error)
          let errorMessage = 'Failed to fetch comments. Please try again.'
          
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
      },

      // Utility actions
      clearError: () => {
        set({ error: null })
      }
    }),
    {
      name: 'project-storage',
      partialize: (state) => ({
        organizations: state.organizations,
        currentOrganization: state.currentOrganization,
        tasks: state.tasks,
        currentTask: state.currentTask
      })
    }
  )
)