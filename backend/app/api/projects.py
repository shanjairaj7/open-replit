"""
Project management API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from app.models.project_models import (
    CreateProjectRequest,
    ProjectInfo,
    ProjectListResponse,
    FileListResponse,
    FileContent,
    ReadFileRequest,
    UpdateFileRequest,
    DeleteFileRequest,
    ListFilesRequest,
    CommandRequest,
    CommandResponse,
    FileInfo
)
from app.services.project_service import ProjectService

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get project service instance
def get_project_service() -> ProjectService:
    return ProjectService()


@router.post("/projects", response_model=ProjectInfo)
async def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service)
) -> ProjectInfo:
    """Create a new project from boilerplate"""
    try:
        logger.info(f"Creating project '{request.name}' with template '{request.template}'")
        project = service.create_project(
            name=request.name,
            request=request.request,
            template=request.template
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    service: ProjectService = Depends(get_project_service)
) -> ProjectListResponse:
    """List all projects"""
    try:
        projects = service.list_projects()
        return ProjectListResponse(
            projects=projects,
            total=len(projects)
        )
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/projects/{project_id}", response_model=ProjectInfo)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service)
) -> ProjectInfo:
    """Get project details by ID"""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service)
):
    """Delete a project"""
    success = service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}


@router.post("/projects/{project_id}/files/list", response_model=FileListResponse)
async def list_project_files(
    project_id: str,
    request: ListFilesRequest,
    service: ProjectService = Depends(get_project_service)
) -> FileListResponse:
    """List files in project directory"""
    try:
        files = service.list_project_files(project_id, request.path)
        return FileListResponse(
            files=files,
            path=request.path
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/projects/{project_id}/files/read", response_model=FileContent)
async def read_file(
    project_id: str,
    request: ReadFileRequest,
    service: ProjectService = Depends(get_project_service)
) -> FileContent:
    """Read file content from project"""
    try:
        content = service.read_file(project_id, request.file_path)
        return FileContent(
            path=request.file_path,
            content=content
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/projects/{project_id}/files/write")
async def update_file(
    project_id: str,
    request: UpdateFileRequest,
    service: ProjectService = Depends(get_project_service)
):
    """Create or update file in project"""
    try:
        success = service.write_file(project_id, request.file_path, request.content)
        if success:
            return {"message": f"File '{request.file_path}' updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


@router.post("/projects/{project_id}/files/delete")
async def delete_file(
    project_id: str,
    request: DeleteFileRequest,
    service: ProjectService = Depends(get_project_service)
):
    """Delete file from project"""
    try:
        success = service.delete_file(project_id, request.file_path)
        if success:
            return {"message": f"File '{request.file_path}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/projects/{project_id}/command", response_model=CommandResponse)
async def execute_command(
    project_id: str,
    request: CommandRequest,
    service: ProjectService = Depends(get_project_service)
) -> CommandResponse:
    """Execute a command in the project directory"""
    try:
        result = service.execute_command(project_id, request.command, request.cwd)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute command: {str(e)}")