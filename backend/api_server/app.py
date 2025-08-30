"""
Modal.com Compatible FastAPI Backend - Emergency Project
Main application file with dynamic Modal configuration for deployment
"""

import os
import modal
from datetime import datetime

# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "emergency-really-nice-project-management-0827-222036")
APP_TITLE = os.getenv("APP_TITLE", "Emergency Project Management")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Project and task management system")
SECRET_NAME = os.getenv("MODAL_SECRET_NAME", f"{APP_NAME}-secrets")

print(f"🚀 Initializing Modal app: {APP_NAME}")
print(f"📋 Using secret: {SECRET_NAME}")

# Modal app configuration with dynamic naming
modal_app = modal.App(APP_NAME)
app = modal_app  # Alias for Modal deployment

# Create persistent volume for JSON database
database_volume = modal.Volume.from_name(f"{APP_NAME}-database", create_if_missing=True)

# Modal image with dependencies from requirements.txt
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", "/root")
)

# Modal ASGI app with secrets and configuration
@modal_app.function(
    image=image,
    secrets=[
        modal.Secret.from_name(SECRET_NAME),  # Dynamic secret name per deployment
    ],
    volumes={f"/root/json_data": database_volume},  # Mount persistent volume for JSON database
)
@modal.asgi_app()
def fastapi_app():
    """Create and configure FastAPI application for Modal deployment"""

    # Import dependencies inside function for Modal compatibility
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from routes.auth import router as auth_router
    from routes.organisation import router as organisation_router
    from routes.task import router as task_router
    from routes.health import router as health_router

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

    # Include routers
    app.include_router(auth_router)
    app.include_router(organisation_router)
    app.include_router(task_router)
    app.include_router(health_router)

    return app

# For local development
if __name__ == "__main__":
    import uvicorn
    print("🔧 Running in local development mode")

    # Create a simple FastAPI app for local development
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from routes.auth import router as auth_router
    from routes.organisation import router as organisation_router
    from routes.task import router as task_router
    from routes.health import router as health_router

    local_app = FastAPI(title="Emergency Project Management - Local Dev")

    local_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    local_app.include_router(auth_router)
    local_app.include_router(organisation_router)
    local_app.include_router(task_router)
    local_app.include_router(health_router)

    uvicorn.run(local_app, host="0.0.0.0", port=8000)
