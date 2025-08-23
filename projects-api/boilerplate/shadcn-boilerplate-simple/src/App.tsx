import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import { ProtectedRoute } from './components/protected-route'
import SimpleHomePage from './pages/SimpleHomePage'

/**
 * BOILERPLATE APP COMPONENT WITH AUTHENTICATION
 * 
 * This is a sample React application with protected routes and authentication.
 * Features included:
 * - Zustand store for state management
 * - Protected routes with authentication
 * - Login/Signup pages
 * - Sample protected pages (Home, Profile, Settings)
 * - Persistent auth state with localStorage
 */
function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Protected routes */}
        <Route path="/" element={
          <ProtectedRoute>
            <SimpleHomePage />
          </ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        } />
        <Route path="/profile" element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        } />

        {/* Redirect any unknown routes to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App