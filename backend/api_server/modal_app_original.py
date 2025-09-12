"""
Azure App Service Compatible FastAPI Backend - Emergency Project
Main application file for Azure deployment
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Dynamic configuration for production deployment
APP_NAME = os.getenv("APP_NAME", "emergency-really-nice-project-management")
APP_TITLE = os.getenv("APP_TITLE", "Emergency Project Management")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Project and task management system")

print(f"🚀 Initializing FastAPI app for Azure: {APP_NAME}")
print(f"📋 Title: {APP_TITLE}")

# Create FastAPI app with dynamic configuration
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "FastAPI backend running on Azure",
        "app_name": APP_NAME,
        "timestamp": datetime.now().isoformat(),
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "api_server",
        "app_name": APP_NAME
    }

# For local development and Azure deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🔧 Running on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
