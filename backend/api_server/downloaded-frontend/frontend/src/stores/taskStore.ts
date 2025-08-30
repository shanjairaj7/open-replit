import { create } from 'zustand'
import { toast } from 'sonner'
import api from '@/lib/api'

export interface Task {
  id: number
  title: string
  description: string | null
  status: string
  due_date: string | null
  assigned_to: number | null
  created_by: number
  created_at: string
  updated_at: string | null
}

export interface User {
  id: number
  name: string
  email: string
}

export interface Organization {
  id: number
  name: string
  description: string | null
  owner_id: number
  created_at: string
}

export interface Comment {
  id: number
  content: string
  task_id: number
  user_id: number
  created_at: string
}

interface TaskState {
  tasks: Task[]
  users: User[]
  organizations: Organization[]
  comments: Record<number, Comment[]> // task_id -> comments
  loading: boolean
  error: string | null
  currentFilter: string
  
  // Task actions
  fetchTasks: (status?: string) => Promise<void>
  createTask: (task: Omit<Task, 'id' | 'created_by' | 'created_at' | 'updated_at'>) => Promise<boolean>
  updateTask: (id: number, updates: Partial<Task>) => Promise<boolean>
  deleteTask: (id: number) => Promise<boolean>
  
  // Organization actions
  fetchOrganizations: () => Promise<void>
  createOrganization: (org: Omit<Organization, 'id' | 'owner_id' | 'created_at'>) => Promise<boolean>
  inviteMember: (orgId: number, email: string, role: string) => Promise<boolean>
  
  // Comment actions
  fetchComments: (taskId: number) => Promise<void>
  createComment: (comment: Omit<Comment, 'id' | 'user_id' | 'created_at'>) => Promise<boolean>
  deleteComment: (id: number) => Promise<boolean>
  
  // Filter actions
  setFilter: (filter: string) => void
  clearError: () => void
}

export const useTaskStore = create<TaskState>()((set, get) => ({
  tasks: [],
  users: [],
  organizations: [],
  comments: {},
  loading: false,
  error: null,
  currentFilter: 'all',
  
  // Task actions
  fetchTasks: async (status?: string) => {
    set({ loading: true, error: null })
    try {
      const url = status ? `/tasks?status=${status}` : '/tasks'
      const response = await api.get<Task[]>(url)
      set({ tasks: response.data, loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to fetch tasks'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
    }
  },
  
  createTask: async (task) => {
    set({ loading: true, error: null })
    try {
      const response = await api.post<Task>('/tasks', task)
      set((state) => ({
        tasks: [...state.tasks, response.data],
        loading: false
      }))
      toast.success('Task created successfully!')
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create task'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  updateTask: async (id, updates) => {
    set({ loading: true, error: null })
    try {
      const response = await api.put<Task>(`/tasks/${id}`, updates)
      set((state) => ({
        tasks: state.tasks.map((task) => 
          task.id === id ? { ...task, ...response.data } : task
        ),
        loading: false
      }))
      toast.success('Task updated successfully!')
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update task'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  deleteTask: async (id) => {
    set({ loading: true, error: null })
    try {
      await api.delete(`/tasks/${id}`)
      set((state) => ({
        tasks: state.tasks.filter((task) => task.id !== id),
        loading: false
      }))
      toast.success('Task deleted successfully!')
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to delete task'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  // Organization actions
  fetchOrganizations: async () => {
    set({ loading: true, error: null })
    try {
      const response = await api.get<Organization[]>('/organizations')
      set({ organizations: response.data, loading: false })
    } catch (error: any) {
      // Not all users will have organizations, so we don't show an error toast
      set({ loading: false })
    }
  },
  
  createOrganization: async (org) => {
    set({ loading: true, error: null })
    try {
      const response = await api.post<Organization>('/organizations', org)
      set((state) => ({
        organizations: [...state.organizations, response.data],
        loading: false
      }))
      toast.success('Organization created successfully!')
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create organization'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  inviteMember: async (orgId, email, role) => {
    set({ loading: true, error: null })
    try {
      await api.post(`/organizations/${orgId}/invite`, { email, role })
      set({ loading: false })
      toast.success('Member invited successfully!')
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to invite member'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  // Comment actions
  fetchComments: async (taskId) => {
    set({ loading: true, error: null })
    try {
      const response = await api.get<Comment[]>(`/comments/task/${taskId}`)
      set((state) => ({
        comments: {
          ...state.comments,
          [taskId]: response.data
        },
        loading: false
      }))
    } catch (error: any) {
      // Comments are optional, so we don't show an error toast
      set({ loading: false })
    }
  },
  
  createComment: async (comment) => {
    set({ loading: true, error: null })
    try {
      const response = await api.post<Comment>('/comments', comment)
      set((state) => ({
        comments: {
          ...state.comments,
          [comment.task_id]: [
            ...(state.comments[comment.task_id] || []),
            response.data
          ]
        },
        loading: false
      }))
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create comment'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  deleteComment: async (id) => {
    set({ loading: true, error: null })
    try {
      await api.delete(`/comments/${id}`)
      set((state) => {
        const updatedComments = { ...state.comments }
        Object.keys(updatedComments).forEach((taskId) => {
          updatedComments[parseInt(taskId)] = updatedComments[parseInt(taskId)].filter(
            (comment) => comment.id !== id
          )
        })
        return { comments: updatedComments, loading: false }
      })
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to delete comment'
      set({ error: errorMessage, loading: false })
      toast.error(errorMessage)
      return false
    }
  },
  
  // Filter actions
  setFilter: (filter) => set({ currentFilter: filter }),
  
  clearError: () => set({ error: null })
}))