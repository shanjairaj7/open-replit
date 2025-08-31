import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'
import { toast } from 'sonner'

export interface User {
  id: number
  email: string
  name: string
  is_active: boolean
  created_at: string
}

interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
  
  // Actions
  signup: (email: string, password: string, name: string) => Promise<boolean>
  login: (email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  getProfile: () => Promise<void>
  clearError: () => void
}

const API_BASE_URL = import.meta.env.VITE_APP_BACKEND_URL || 'http://localhost:8000'

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      signup: async (email: string, password: string, name: string) => {
        set({ loading: true, error: null })
        try {
          console.log('Attempting signup with:', { email, name })
          const response = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/signup`, {
            email,
            password,
            name
          })

          console.log('Signup response:', { 
            status: response.status, 
            data: response.data 
          })

          if (response.status === 201) {
            const { access_token, user } = response.data
            
            console.log('Signup successful, setting auth state:', { user, token: access_token })
            
            // CRITICAL: Store token for authentication
            // Token is now available in Zustand store: useAuthStore.getState().token
            // Access pattern: const { token } = useAuthStore()
            // API calls: Authorization header = `Bearer ${token}`
            console.log('🔑 TOKEN STORED:', access_token)
            console.log('🔑 How to access token: useAuthStore.getState().token')
            
            // Set token in axios defaults for future requests
            axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
            
            set({ 
              user, 
              token: access_token, 
              isAuthenticated: true, 
              loading: false 
            })
            
            toast.success('Account created successfully!')
            return true
          } else {
            console.error('Unexpected signup response status:', response.status)
            set({ error: `Unexpected response status: ${response.status}`, loading: false })
            toast.error(`Signup failed with status: ${response.status}`)
            return false
          }
        } catch (error: any) {
          console.error('Signup error:', error)
          let errorMessage = 'Signup failed. Please try again.'
          
          if (error.response?.data?.detail) {
            const detail = error.response.data.detail
            if (Array.isArray(detail)) {
              // Handle validation errors (array format)
              errorMessage = detail.map((err: any) => err.msg).join(', ')
            } else {
              // Handle single error message
              errorMessage = detail
            }
          } else if (error.response?.data) {
            // Handle other error formats
            errorMessage = error.response.data.message || error.response.data.error || errorMessage
          } else if (error.message) {
            errorMessage = error.message
          }
          
          console.error('Processed error message:', errorMessage)
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      login: async (email: string, password: string) => {
        set({ loading: true, error: null })
        try {
          console.log('Attempting login with:', { email })
          const response = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/login`, {
            email,
            password
          })

          console.log('Login response:', { 
            status: response.status, 
            data: response.data 
          })

          if (response.status === 200) {
            const { access_token, user } = response.data
            
            console.log('Login successful, setting auth state:', { user, token: access_token })
            
            // CRITICAL: Store token for authentication  
            // Token is now available in Zustand store: useAuthStore.getState().token
            // Access pattern: const { token } = useAuthStore()
            // API calls: Authorization header = `Bearer ${token}`
            console.log('🔑 TOKEN STORED:', access_token)
            console.log('🔑 How to access token: useAuthStore.getState().token')
            
            // Set token in axios defaults for future requests
            axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
            
            set({ 
              user, 
              token: access_token, 
              isAuthenticated: true, 
              loading: false 
            })
            
            toast.success('Logged in successfully!')
            return true
          } else {
            console.error('Unexpected login response status:', response.status)
            set({ error: `Unexpected response status: ${response.status}`, loading: false })
            toast.error(`Login failed with status: ${response.status}`)
            return false
          }
        } catch (error: any) {
          console.error('Login error:', error)
          let errorMessage = 'Login failed. Please try again.'
          
          if (error.response?.data?.detail) {
            const detail = error.response.data.detail
            if (Array.isArray(detail)) {
              // Handle validation errors (array format)
              errorMessage = detail.map((err: any) => err.msg).join(', ')
            } else {
              // Handle single error message
              errorMessage = detail
            }
          } else if (error.response?.data) {
            // Handle other error formats
            errorMessage = error.response.data.message || error.response.data.error || errorMessage
          } else if (error.message) {
            errorMessage = error.message
          }
          
          console.error('Processed error message:', errorMessage)
          set({ error: errorMessage, loading: false })
          toast.error(errorMessage)
        }
        return false
      },

      logout: async () => {
        const { token } = get()
        
        if (token) {
          try {
            await axios.post(`${API_BASE_URL}/auth/logout`)
          } catch (error) {
            console.error('Logout API call failed:', error)
          }
        }

        // Clear token from axios defaults
        delete axios.defaults.headers.common['Authorization']
        
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false, 
          error: null 
        })
        
        toast.success('Logged out successfully!')
      },

      getProfile: async () => {
        const { token } = get()
        
        if (!token) return
        
        try {
          const response = await axios.get<User>(`${API_BASE_URL}/auth/profile`)
          
          if (response.status === 200) {
            set({ user: response.data })
          }
        } catch (error: any) {
          console.error('Failed to get profile:', error)
          // If token is invalid, logout
          if (error.response?.status === 401) {
            get().logout()
          }
        }
      },

      clearError: () => {
        set({ error: null })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Set token in axios defaults when rehydrating from localStorage
        if (state?.token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      }
    }
  )
)