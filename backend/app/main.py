from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.api.chat import router as chat_router
from app.api.models import router as models_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI backend server...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI backend server...")

# Create FastAPI app
app = FastAPI(
    title="Bolt.diy Backend API",
    description="Backend API for bolt.diy cloud migration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Allow all origins for development
# TODO: Restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(models_router, prefix="/api", tags=["models"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(projects_router, prefix="/api", tags=["projects"])

@app.get("/")
async def root():
    return {
        "message": "Bolt.diy Backend API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )