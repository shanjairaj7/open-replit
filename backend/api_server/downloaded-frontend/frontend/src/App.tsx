import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/protected-route'
import Sidebar from './components/Sidebar'
import DashboardPage from './pages/DashboardPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import OrganizationsPage from './pages/OrganizationsPage'
import ProfilePage from './pages/ProfilePage'
import SettingsPage from './pages/SettingsPage'
import SignupPage from './pages/SignupPage'
import SimpleHomePage from './pages/SimpleHomePage'
import TaskDetailPage from './pages/TaskDetailPage'
import TasksPage from './pages/TasksPage'

/**
 * PROJECT MANAGEMENT APP COMPONENT WITH AUTHENTICATION
 * 
 * This is a project management React application with protected routes and authentication.
 * Features included:
 * - Component library for styling
 * - Zustand store for state management
 * - Protected routes with authentication
 * - Login/Signup pages
 * - Sidebar navigation
 * - Task management, organizations, dashboard, and profile pages
 * - Persistent auth state with localStorage
 */

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 ml-64 overflow-auto">
        {children}
      </div>
    </div>
  )
}
function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Protected routes with sidebar */}
        <Route path="/" element={
          <ProtectedRoute>
            <AppLayout>
              <DashboardPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <AppLayout>
              <DashboardPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/tasks" element={
          <ProtectedRoute>
            <AppLayout>
              <TasksPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/tasks/:id" element={
          <ProtectedRoute>
            <AppLayout>
              <TaskDetailPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/organizations" element={
          <ProtectedRoute>
            <AppLayout>
              <OrganizationsPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/home" element={
          <ProtectedRoute>
            <AppLayout>
              <HomePage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/simple-home" element={
          <ProtectedRoute>
            <AppLayout>
              <SimpleHomePage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute>
            <AppLayout>
              <SettingsPage />
            </AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/profile" element={
          <ProtectedRoute>
            <AppLayout>
              <ProfilePage />
            </AppLayout>
          </ProtectedRoute>
        } />

        {/* Redirect any unknown routes to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App