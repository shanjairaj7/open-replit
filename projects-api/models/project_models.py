"""
Project management models for the boilerplate system
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """Project status enumeration"""
    CREATED = "created"
    BUILDING = "building"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project"""
    name: str = Field(..., description="Project name", pattern="^[a-zA-Z0-9_-]+$")
    request: str = Field(..., description="User's natural language request for the project")
    template: str = Field(default="shadcn-boilerplate", description="Template to use")
    

class ProjectInfo(BaseModel):
    """Project information model"""
    id: str
    name: str
    path: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    request: str
    template: str
    port: Optional[int] = None
    build_output: Optional[str] = None
    error: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Response model for project list"""
    projects: List[ProjectInfo]
    total: int


class FileInfo(BaseModel):
    """File information model"""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    

class FileListResponse(BaseModel):
    """Response model for file list"""
    files: List[FileInfo]
    path: str


class FileContent(BaseModel):
    """File content model"""
    path: str
    content: str
    encoding: str = "utf-8"


class ReadFileRequest(BaseModel):
    """Request model for reading file content"""
    file_path: str = Field(..., description="File path relative to project root")


class UpdateFileRequest(BaseModel):
    """Request model for updating file content"""
    file_path: str = Field(..., description="File path relative to project root")
    content: str
    encoding: str = "utf-8"


class ListFilesRequest(BaseModel):
    """Request model for listing files"""
    path: str = Field(default="", description="Directory path relative to project root")


class DeleteFileRequest(BaseModel):
    """Request model for deleting a file"""
    file_path: str = Field(..., description="File path relative to project root")


class CommandRequest(BaseModel):
    """Request model for executing commands"""
    command: str = Field(..., description="Full command string to execute (e.g., 'npm run build')")
    cwd: Optional[str] = Field(None, description="Working directory")
    

class CommandResponse(BaseModel):
    """Response model for command execution"""
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int


class GenerateRequest(BaseModel):
    """Request model for AI code generation"""
    prompt: str = Field(..., description="AI prompt for code generation")
    files_context: Optional[List[str]] = Field(None, description="Files to include as context")
    

class BuildStatus(BaseModel):
    """Build status model"""
    project_id: str
    status: str  # "idle", "building", "success", "error"
    last_build: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None