import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

/**
 * BOILERPLATE APPLICATION ENTRY POINT
 * 
 * This is the main entry point for the React application.
 * It sets up the React root and renders the App component.
 * 
 * Standard React 18+ setup with:
 * - StrictMode for development warnings
 * - Tailwind CSS for styling
 * - Shadcn/ui components
 * - Root component mounting
 * 
 * Customization:
 * - Add global providers (Context, Redux, etc.) here
 * - Add error boundaries for production
 * - Add analytics or monitoring setup
 * - Configure service workers if needed
 */

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
