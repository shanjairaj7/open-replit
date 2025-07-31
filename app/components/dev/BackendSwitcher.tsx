import React, { useState, useEffect } from 'react';
import { setUseExternalBackend, apiConfig } from '~/lib/config/api';

export function BackendSwitcher() {
  const [isUsingExternal, setIsUsingExternal] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    // Check if we're using external backend
    const useExternal = localStorage.getItem('use-fastapi-backend') === 'true';
    setIsUsingExternal(useExternal);

    // Check backend status
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    setBackendStatus('checking');
    try {
      const response = await fetch('http://localhost:8000/api/health');
      if (response.ok) {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch (error) {
      setBackendStatus('offline');
    }
  };

  const handleToggle = () => {
    setUseExternalBackend(!isUsingExternal);
  };

  // Only show in development
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 bg-bolt-elements-background-depth-2 border border-bolt-elements-borderColor rounded-lg p-4 shadow-lg z-50">
      <div className="flex items-center gap-3">
        <div className="text-sm font-medium text-bolt-elements-textPrimary">
          Backend Mode:
        </div>
        
        <div className="flex items-center gap-2">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isUsingExternal}
              onChange={handleToggle}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
          </label>
          
          <span className="text-sm text-bolt-elements-textSecondary">
            {isUsingExternal ? 'FastAPI' : 'Remix'}
          </span>
        </div>

        {isUsingExternal && (
          <div className="flex items-center gap-2">
            <button
              onClick={checkBackendStatus}
              className="px-2 py-1 text-xs bg-bolt-elements-button-primary-background text-bolt-elements-button-primary-text rounded hover:bg-bolt-elements-button-primary-backgroundHover"
            >
              Check
            </button>
            
            <div className={`w-2 h-2 rounded-full ${
              backendStatus === 'online' ? 'bg-green-500' :
              backendStatus === 'offline' ? 'bg-red-500' :
              'bg-yellow-500'
            }`} title={
              backendStatus === 'online' ? 'Backend is online' :
              backendStatus === 'offline' ? 'Backend is offline' :
              'Checking backend status...'
            } />
          </div>
        )}
      </div>
      
      {isUsingExternal && backendStatus === 'offline' && (
        <div className="mt-2 text-xs text-red-400">
          FastAPI backend is not running. Start it with: <code>cd backend && python run.py</code>
        </div>
      )}

      {isUsingExternal && backendStatus === 'online' && (
        <div className="mt-2 text-xs text-green-400">
          FastAPI backend is running at http://localhost:8000
        </div>
      )}
    </div>
  );
}