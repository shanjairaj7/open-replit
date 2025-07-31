"""
Projects API using the exact same implementation as backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Projects API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock settings for Railway environment
class Settings:
    WORKSPACE_PATH = "/tmp/workspace"
    PROJECTS_PATH = "/tmp/projects" 
    BOILERPLATE_PATH = str(Path(__file__).parent / "boilerplate")

# Set up paths
os.environ["WORKSPACE_PATH"] = "/tmp/workspace"
os.environ["PROJECTS_PATH"] = "/tmp/projects"
os.environ["BOILERPLATE_PATH"] = str(Path(__file__).parent / "boilerplate")

# Import the exact same routes from backend
from projects import router as projects_router

# Include the projects router
app.include_router(projects_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Projects API", "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)