"""
Simple config for Railway deployment
"""
import os
from pathlib import Path

class Settings:
    WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/tmp/workspace")
    PROJECTS_PATH = os.environ.get("PROJECTS_PATH", "/tmp/projects") 
    BOILERPLATE_PATH = os.environ.get("BOILERPLATE_PATH", str(Path(__file__).parent / "boilerplate"))

settings = Settings()