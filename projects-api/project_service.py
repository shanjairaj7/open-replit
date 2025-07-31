"""
Project management service for handling boilerplate projects
"""
import os
import shutil
import uuid
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from project_models import (
    ProjectInfo, ProjectStatus, FileInfo, CommandResponse
)
from config import settings

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing boilerplate projects"""
    
    def __init__(self):
        self.workspace_path = Path(settings.WORKSPACE_PATH or "/app/workspace")
        self.projects_path = Path(settings.PROJECTS_PATH or "/app/projects")
        self.boilerplate_path = Path(settings.BOILERPLATE_PATH or "/app/boilerplate")
        
        # Ensure directories exist
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.projects_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory project store (could be replaced with database)
        self.projects_db = {}
        self._load_existing_projects()
    
    def _load_existing_projects(self):
        """Load existing projects from filesystem"""
        if self.projects_path.exists():
            for project_dir in self.projects_path.iterdir():
                if project_dir.is_dir():
                    metadata_file = project_dir / ".project_metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                self.projects_db[metadata['id']] = ProjectInfo(**metadata)
                        except Exception as e:
                            logger.error(f"Failed to load project metadata for {project_dir}: {e}")
    
    def create_project(self, name: str, request: str, template: str = "shadcn-boilerplate") -> ProjectInfo:
        """Create a new project from boilerplate"""
        project_id = str(uuid.uuid4())
        project_path = self.projects_path / name
        
        # Check if project already exists
        if project_path.exists():
            raise ValueError(f"Project with name '{name}' already exists")
        
        # Get boilerplate template path
        template_path = self.boilerplate_path / template
        if not template_path.exists():
            raise ValueError(f"Template '{template}' not found")
        
        try:
            # Copy boilerplate to new project
            logger.info(f"Creating project '{name}' from template '{template}'")
            shutil.copytree(template_path, project_path, ignore=shutil.ignore_patterns('node_modules', '.git'))
            
            # Create project info
            project_info = ProjectInfo(
                id=project_id,
                name=name,
                path=str(project_path),
                status=ProjectStatus.CREATED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request=request,
                template=template
            )
            
            # Save metadata
            metadata_file = project_path / ".project_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(project_info.model_dump(mode='json'), f, indent=2, default=str)
            
            # Store in memory
            self.projects_db[project_id] = project_info
            
            logger.info(f"Project '{name}' created successfully with ID: {project_id}")
            return project_info
            
        except Exception as e:
            # Cleanup on failure
            if project_path.exists():
                shutil.rmtree(project_path)
            raise Exception(f"Failed to create project: {str(e)}")
    
    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID"""
        return self.projects_db.get(project_id)
    
    def get_project_by_name(self, name: str) -> Optional[ProjectInfo]:
        """Get project by name"""
        for project in self.projects_db.values():
            if project.name == name:
                return project
        return None
    
    def list_projects(self) -> List[ProjectInfo]:
        """List all projects"""
        return list(self.projects_db.values())
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        project = self.get_project(project_id)
        if not project:
            return False
        
        try:
            # Delete project directory
            project_path = Path(project.path)
            if project_path.exists():
                shutil.rmtree(project_path)
            
            # Remove from memory
            del self.projects_db[project_id]
            
            logger.info(f"Project '{project.name}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False
    
    def list_project_files(self, project_id: str, path: str = "") -> List[FileInfo]:
        """List files in a project directory. If path is empty, returns full tree structure."""
        project = self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        project_path = Path(project.path)
        
        if path == "":
            # Return full tree structure
            return self._get_full_tree(project_path, project_path)
        else:
            # Return single directory listing
            target_path = project_path / path
            
            if not target_path.exists():
                raise ValueError(f"Path '{path}' not found in project")
            
            files = []
            for item in target_path.iterdir():
                # Skip hidden files and node_modules
                if item.name.startswith('.') or item.name == 'node_modules':
                    continue
                    
                file_info = FileInfo(
                    name=item.name,
                    path=str(item.relative_to(project_path)),
                    type="directory" if item.is_dir() else "file",
                    size=item.stat().st_size if item.is_file() else None
                )
                files.append(file_info)
            
            # Sort: directories first, then files
            files.sort(key=lambda x: (x.type != "directory", x.name))
            return files
    
    def _get_full_tree(self, current_path: Path, project_root: Path) -> List[FileInfo]:
        """Recursively get all files and directories in the project"""
        files = []
        
        try:
            for item in current_path.iterdir():
                # Skip hidden files, node_modules, and dist directories
                if (item.name.startswith('.') or 
                    item.name in ['node_modules', 'dist', '__pycache__', '.git']):
                    continue
                
                relative_path = str(item.relative_to(project_root))
                
                file_info = FileInfo(
                    name=item.name,
                    path=relative_path,
                    type="directory" if item.is_dir() else "file",
                    size=item.stat().st_size if item.is_file() else None
                )
                files.append(file_info)
                
                # Recursively get subdirectories
                if item.is_dir():
                    subdirectory_files = self._get_full_tree(item, project_root)
                    files.extend(subdirectory_files)
                    
        except PermissionError:
            # Skip directories we can't read
            pass
        except Exception as e:
            logger.warning(f"Error reading directory {current_path}: {e}")
        
        return files
    
    def read_file(self, project_id: str, file_path: str) -> str:
        """Read file content from project"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        full_path = Path(project.path) / file_path
        
        # Security check - ensure path is within project
        try:
            full_path.resolve().relative_to(Path(project.path).resolve())
        except ValueError:
            raise ValueError("Access denied: Path outside project directory")
        
        if not full_path.exists():
            raise ValueError(f"File '{file_path}' not found")
        
        if not full_path.is_file():
            raise ValueError(f"'{file_path}' is not a file")
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")
    
    def write_file(self, project_id: str, file_path: str, content: str) -> bool:
        """Write content to file in project"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        full_path = Path(project.path) / file_path
        
        # Security check
        try:
            full_path.resolve().relative_to(Path(project.path).resolve())
        except ValueError:
            raise ValueError("Access denied: Path outside project directory")
        
        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update project timestamp
            project.updated_at = datetime.utcnow()
            self._update_project_metadata(project)
            
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to write file: {str(e)}")
    
    def delete_file(self, project_id: str, file_path: str) -> bool:
        """Delete file from project"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        full_path = Path(project.path) / file_path
        
        # Security check
        try:
            full_path.resolve().relative_to(Path(project.path).resolve())
        except ValueError:
            raise ValueError("Access denied: Path outside project directory")
        
        if not full_path.exists():
            raise ValueError(f"File '{file_path}' not found")
        
        try:
            if full_path.is_file():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)
            
            # Update project timestamp
            project.updated_at = datetime.utcnow()
            self._update_project_metadata(project)
            
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to delete file: {str(e)}")
    
    def _update_project_metadata(self, project: ProjectInfo):
        """Update project metadata file"""
        metadata_file = Path(project.path) / ".project_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(project.model_dump(mode='json'), f, indent=2, default=str)
    
    def execute_command(self, project_id: str, command: str, cwd: str = None) -> CommandResponse:
        """Execute a command in the project directory"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Set working directory
        project_path = Path(project.path)
        if cwd:
            work_dir = project_path / cwd
            # Security check
            try:
                work_dir.resolve().relative_to(project_path.resolve())
            except ValueError:
                raise ValueError("Access denied: Working directory outside project")
        else:
            work_dir = project_path
        
        if not work_dir.exists():
            raise ValueError(f"Working directory '{cwd or '.'}' not found")
        
        try:
            logger.info(f"Executing command in {work_dir}: {command}")
            
            # Execute command using shell
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Update project timestamp
            project.updated_at = datetime.utcnow()
            self._update_project_metadata(project)
            
            return CommandResponse(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            raise ValueError("Command timed out after 5 minutes")
        except Exception as e:
            raise ValueError(f"Failed to execute command: {str(e)}")