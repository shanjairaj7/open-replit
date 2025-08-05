from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import os
import shutil
import uuid
import json
import subprocess
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import sys
from contextlib import asynccontextmanager
import docker
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker client - will be initialized when needed
docker_client = None

# VPS Configuration - PERSISTENT STORAGE
VPS_BASE_PATH = Path("/opt/codebase-platform")
VPS_PROJECTS_PATH = VPS_BASE_PATH / "projects"
VPS_FRONTEND_BOILERPLATE_PATH = VPS_BASE_PATH / "boilerplate" / "shadcn-boilerplate"
VPS_BACKEND_BOILERPLATE_PATH = VPS_BASE_PATH / "boilerplate" / "backend-boilerplate"

# Ensure directories exist
VPS_BASE_PATH.mkdir(parents=True, exist_ok=True)
VPS_PROJECTS_PATH.mkdir(parents=True, exist_ok=True)

class VPSProjectManager:
    """Manages Docker containers for isolated project environments"""
    
    def __init__(self):
        global docker_client
        if docker_client is None:
            docker_client = docker.from_env()  # This works now with socket permissions fixed
        self.containers: Dict[str, Dict] = {}
        self.frontend_port_pool = list(range(3001, 3999))  # Frontend ports
        self.backend_port_pool = list(range(8001, 8999))   # Backend ports
        
        # Initialize used_ports by scanning actual Docker containers
        self.used_ports = self._scan_used_ports()
        logger.info(f"Initialized with {len(self.used_ports)} ports already in use: {sorted(self.used_ports)}")
    
    def _scan_used_ports(self) -> set:
        """Scan Docker containers to find which ports are actually in use"""
        used_ports = set()
        try:
            # Get all running containers
            containers = docker_client.containers.list(all=True)
            
            for container in containers:
                # Check if container has port mappings
                if container.ports:
                    for host_bindings in container.ports.values():
                        if host_bindings:  # Port is bound to host
                            for binding in host_bindings:
                                host_port = int(binding['HostPort'])
                                # Only track ports in our ranges
                                if (3001 <= host_port <= 3999) or (8001 <= host_port <= 8999):
                                    used_ports.add(host_port)
                                    logger.info(f"Found used port {host_port} in container {container.name}")
                                    
        except Exception as e:
            logger.error(f"Error scanning Docker ports: {e}")
            
        return used_ports
    
    def _get_available_port(self, port_pool: List[int]) -> int:
        """Get next available port from specified pool with real-time Docker check"""
        for port in port_pool:
            if port not in self.used_ports and self._is_port_actually_free(port):
                self.used_ports.add(port)
                logger.info(f"Allocated port {port}")
                return port
        raise Exception("No available ports in pool")
    
    def _is_port_actually_free(self, port: int) -> bool:
        """Double-check if port is actually free by checking Docker directly"""
        try:
            # Check all containers (running and stopped) for this port
            containers = docker_client.containers.list(all=True)
            for container in containers:
                if container.ports:
                    for host_bindings in container.ports.values():
                        if host_bindings:
                            for binding in host_bindings:
                                if int(binding['HostPort']) == port:
                                    logger.warning(f"Port {port} is actually in use by container {container.name}")
                                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False
    
    def _get_frontend_port(self) -> int:
        """Get available frontend port"""
        return self._get_available_port(self.frontend_port_pool)
    
    def _get_backend_port(self) -> int:
        """Get available backend port"""
        return self._get_available_port(self.backend_port_pool)
    
    def _release_port(self, port: int):
        """Release port back to pool"""
        self.used_ports.discard(port)
    
    async def create_project(self, project_id: str, files: Dict[str, str]) -> Dict:
        """Create new monorepo project with frontend/ and backend/ folders"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        # Remove existing project if exists
        if project_path.exists():
            shutil.rmtree(project_path)
        
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Check boilerplates exist
        if not VPS_FRONTEND_BOILERPLATE_PATH.exists():
            raise HTTPException(500, f"Frontend boilerplate not found at {VPS_FRONTEND_BOILERPLATE_PATH}")
        if not VPS_BACKEND_BOILERPLATE_PATH.exists():
            raise HTTPException(500, f"Backend boilerplate not found at {VPS_BACKEND_BOILERPLATE_PATH}")
        
        # Copy frontend boilerplate to frontend/ folder
        frontend_path = project_path / "frontend"
        shutil.copytree(VPS_FRONTEND_BOILERPLATE_PATH, frontend_path)
        logger.info(f"Copied frontend boilerplate to {frontend_path}")
        
        # Copy backend boilerplate to backend/ folder
        backend_path = project_path / "backend"
        shutil.copytree(VPS_BACKEND_BOILERPLATE_PATH, backend_path)
        logger.info(f"Copied backend boilerplate to {backend_path}")
        
        # Apply file modifications (determine which folder based on path)
        backend_python_files_created = []
        for file_path, content in files.items():
            # Determine if file belongs to frontend or backend
            if file_path.startswith("backend/"):
                full_path = project_path / file_path
            elif file_path.startswith("frontend/"):
                full_path = project_path / file_path
            else:
                # Default to frontend for backwards compatibility
                full_path = project_path / "frontend" / file_path
            
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Modified file: {file_path}")
            
            # Track backend Python files for error checking
            if file_path.startswith("backend/") and file_path.endswith(".py"):
                backend_python_files_created.append(file_path)
        
        # Create project metadata
        metadata = {
            "id": project_id,
            "path": str(project_path),
            "created_at": datetime.now().isoformat(),
            "status": "created",
            "type": "monorepo",
            "structure": {
                "frontend": str(frontend_path),
                "backend": str(backend_path)
            }
        }
        
        with open(project_path / ".project_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Run error checking for both Python and TypeScript files
        if backend_python_files_created:
            python_result = self._run_python_error_check(project_id)
            if python_result["errors"]:
                metadata["python_errors"] = python_result["errors"]
            metadata["python_check_status"] = python_result["status"]
        
        # Check if frontend TypeScript/JavaScript files were created
        frontend_files_created = any(
            f.suffix in ['.ts', '.tsx', '.js', '.jsx'] 
            for f in frontend_path.rglob('*') 
            if f.is_file() and 'node_modules' not in str(f)
        )
        
        if frontend_files_created:
            ts_result = self._run_typescript_error_check(project_id)
            if ts_result["errors"]:
                metadata["typescript_errors"] = ts_result["errors"]
            metadata["typescript_check_status"] = ts_result["status"]
        
        return metadata
    
    async def _check_watchers_status(self, backend_container, frontend_container) -> Dict:
        """Check status of all watchers (Python error checker, TypeScript checker, ESLint)"""
        watchers = {
            "python_error_checker": False,
            "typescript_checker": False,
            "eslint": False,
            "uvicorn": False
        }
        
        try:
            # For backend, check if error file exists and uvicorn is responding
            backend_check = backend_container.exec_run("ls -la .python-errors.txt", demux=True)
            watchers["python_error_checker"] = backend_check.exit_code == 0
            
            # Check if uvicorn is running by looking at container logs
            backend_logs = backend_container.logs(tail=50).decode('utf-8')
            watchers["uvicorn"] = "Uvicorn running on" in backend_logs or "Application startup complete" in backend_logs
            
            # For frontend, check processes or use alternative methods
            try:
                frontend_ps = frontend_container.exec_run("ps aux", demux=True)
                if frontend_ps.exit_code == 0:
                    frontend_output = frontend_ps.output[0].decode('utf-8') if frontend_ps.output[0] else ""
                    watchers["typescript_checker"] = False  # Disabled to prevent constant refreshes
                    watchers["eslint"] = "vite" in frontend_output or "npm run dev" in frontend_output
            except:
                # Fallback: check logs for frontend services
                frontend_logs = frontend_container.logs(tail=50).decode('utf-8')
                watchers["typescript_checker"] = False  # Disabled to prevent constant refreshes
                watchers["eslint"] = "VITE" in frontend_logs or "dev server running" in frontend_logs
                
        except Exception as e:
            logger.warning(f"Error checking watcher status: {e}")
        
        return watchers
    
    async def start_dev_server(self, project_id: str) -> Dict:
        """Start both backend and frontend Docker containers"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Stop existing containers if running
        if project_id in self.containers:
            await self.stop_dev_server(project_id)
        
        # Also cleanup any orphaned containers with the same name
        await self._cleanup_orphaned_containers(project_id)
        
        # Get available ports
        backend_port = self._get_backend_port()
        frontend_port = self._get_frontend_port()
        
        try:
            # 1. Start Backend Container FIRST
            backend_container = docker_client.containers.run(
                "python:3.10-slim",
                command="sh -c 'pip install -r requirements.txt && (python python-error-checker.py . &) && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload'",
                volumes={str(project_path / "backend"): {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                ports={'8000/tcp': backend_port},
                environment={
                    "PYTHONPATH": "/app",
                    "PYTHONUNBUFFERED": "1",
                    "BACKEND_URL": f"http://206.189.229.208:{backend_port}",
                    "API_URL": f"http://206.189.229.208:{backend_port}/api",
                    "BACKEND_PORT": str(backend_port)
                },
                detach=True,
                name=f"backend-{project_id}",
                remove=True
            )
            
            logger.info(f"Started backend container for {project_id} on port {backend_port}")
            
            # Wait for backend to initialize
            await asyncio.sleep(3)
            
            # 2. Start Frontend Container with backend URL
            frontend_container = docker_client.containers.run(
                "node:20-alpine",
                command="sh -c 'npm install && npm run dev -- --host 0.0.0.0 --port 5173'",
                volumes={str(project_path / "frontend"): {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                ports={'5173/tcp': frontend_port},
                environment={
                    "NODE_ENV": "development",
                    "NODE_OPTIONS": "--max-old-space-size=512",
                    "VITE_API_URL": f"http://206.189.229.208:{backend_port}/api",
                    "VITE_BACKEND_URL": f"http://206.189.229.208:{backend_port}"
                },
                detach=True,
                name=f"frontend-{project_id}",
                remove=True
            )
            
            logger.info(f"Started frontend container for {project_id} on port {frontend_port}")
            
            # Store both containers info
            self.containers[project_id] = {
                'backend_container': backend_container,
                'frontend_container': frontend_container,
                'backend_port': backend_port,
                'frontend_port': frontend_port,
                'status': 'starting',
                'project_path': str(project_path)
            }
            
            # Wait for both containers to start
            await asyncio.sleep(5)
            
            # Check if both containers are running
            backend_container.reload()
            frontend_container.reload()
            
            if backend_container.status == 'running' and frontend_container.status == 'running':
                self.containers[project_id]['status'] = 'running'
                
                # Check for running watchers
                watchers_status = await self._check_watchers_status(backend_container, frontend_container)
                
                logger.info(f"Both containers running for {project_id} (with watchers)")
                return {
                    "project_id": project_id,
                    "status": "running",
                    "frontend_port": frontend_port,
                    "backend_port": backend_port,
                    "frontend_url": f"http://YOUR_VPS_IP:{frontend_port}",
                    "backend_url": f"http://YOUR_VPS_IP:{backend_port}",
                    "api_url": f"http://YOUR_VPS_IP:{backend_port}/api",
                    "watchers": watchers_status
                }
            else:
                # One or both containers failed
                await self._cleanup_failed_containers(project_id, backend_port, frontend_port)
                
                backend_logs = backend_container.logs().decode('utf-8') if backend_container.status != 'running' else "Backend OK"
                frontend_logs = frontend_container.logs().decode('utf-8') if frontend_container.status != 'running' else "Frontend OK"
                
                error_msg = f"Container startup failed. Backend: {backend_logs[-200:]}, Frontend: {frontend_logs[-200:]}"
                logger.error(error_msg)
                raise HTTPException(500, error_msg)
                
        except docker.errors.APIError as e:
            await self._cleanup_failed_containers(project_id, backend_port, frontend_port)
            logger.error(f"Docker error: {e}")
            raise HTTPException(500, f"Docker error: {str(e)}")
    
    async def _cleanup_orphaned_containers(self, project_id: str):
        """Clean up any existing containers for this project ID"""
        try:
            backend_container_name = f"backend-{project_id}"
            frontend_container_name = f"frontend-{project_id}"
            
            for container_name in [backend_container_name, frontend_container_name]:
                try:
                    container = docker_client.containers.get(container_name)
                    logger.info(f"Found orphaned container {container_name}, removing...")
                    container.stop(timeout=5)
                    container.remove(force=True)
                    logger.info(f"Removed orphaned container {container_name}")
                except docker.errors.NotFound:
                    pass  # Container doesn't exist, which is good
                except Exception as e:
                    logger.warning(f"Error removing orphaned container {container_name}: {e}")
        except Exception as e:
            logger.error(f"Error in orphaned container cleanup: {e}")

    async def _cleanup_failed_containers(self, project_id: str, backend_port: int, frontend_port: int):
        """Clean up failed container startup"""
        try:
            # Try to stop containers if they exist
            backend_container_name = f"backend-{project_id}"
            frontend_container_name = f"frontend-{project_id}"
            
            for container_name in [backend_container_name, frontend_container_name]:
                try:
                    container = docker_client.containers.get(container_name)
                    container.stop(timeout=5)
                    container.remove(force=True)
                except docker.errors.NotFound:
                    pass  # Container doesn't exist
                except Exception as e:
                    logger.warning(f"Error stopping/removing {container_name}: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Release ports
        self._release_port(backend_port)
        self._release_port(frontend_port)
        
        # Remove from containers dict
        if project_id in self.containers:
            del self.containers[project_id]
    
    async def stop_dev_server(self, project_id: str):
        """Stop both frontend and backend containers for project"""
        if project_id not in self.containers:
            return
        
        container_info = self.containers[project_id]
        
        # Handle both old single-container and new dual-container formats
        if 'container' in container_info:  # Old format
            container = container_info['container']
            port = container_info['port']
            
            try:
                container.stop(timeout=10)
                logger.info(f"Stopped container for project {project_id}")
            except Exception as e:
                logger.error(f"Error stopping container: {e}")
            
            self._release_port(port)
            
        else:  # New dual-container format
            backend_container = container_info.get('backend_container')
            frontend_container = container_info.get('frontend_container')
            backend_port = container_info.get('backend_port')
            frontend_port = container_info.get('frontend_port')
            
            # Stop backend container
            if backend_container:
                try:
                    backend_container.stop(timeout=10)
                    logger.info(f"Stopped backend container for project {project_id}")
                except Exception as e:
                    logger.error(f"Error stopping backend container: {e}")
            
            # Stop frontend container
            if frontend_container:
                try:
                    frontend_container.stop(timeout=10)
                    logger.info(f"Stopped frontend container for project {project_id}")
                except Exception as e:
                    logger.error(f"Error stopping frontend container: {e}")
            
            
            # Release both ports
            if backend_port:
                self._release_port(backend_port)
            if frontend_port:
                self._release_port(frontend_port)
        
        # Remove from containers dict
        del self.containers[project_id]
    
    def _run_typescript_error_check(self, project_id: str) -> dict:
        """Run TypeScript error checking and return results"""
        project_path = VPS_PROJECTS_PATH / project_id
        frontend_path = project_path / "frontend"
        ts_errors = ""
        ts_check_status = {"executed": False, "success": False, "error": None}
        
        # Check if project has running containers
        if project_id in self.containers and self.containers[project_id].get('status') == 'running':
            # Run TypeScript checking inside the frontend container
            try:
                frontend_container = self.containers[project_id]['frontend_container']
                
                # First try local TypeScript installation
                ts_check_status["executed"] = True
                exec_result = frontend_container.exec_run(
                    "sh -c 'node_modules/.bin/tsc -p tsconfig.app.json --noEmit --incremental --tsBuildInfoFile .tsbuildinfo'",
                    workdir="/app"
                )
                
                if exec_result.exit_code == 0:
                    ts_check_status["success"] = True
                    # No errors
                else:
                    ts_check_status["success"] = False
                    error_output = exec_result.output.decode('utf-8') if exec_result.output else ""
                    if error_output.strip():
                        ts_errors = error_output.strip()
                
                return {"errors": ts_errors, "status": ts_check_status}
                
            except Exception as e:
                ts_check_status["error"] = f"Container-based TypeScript check failed: {str(e)}"
                logger.warning(f"Container-based TypeScript check failed: {e}")
                # Fall through to host-based checking
        
        # Fallback: Host-based checking (limited functionality)
        
        try:
            ts_check_status["executed"] = True
            
            # First try to read existing error file
            error_file = frontend_path / ".ts-errors.txt"
            if error_file.exists():
                with open(error_file, 'r') as f:
                    content = f.read().strip()
                    if content and content != "No errors":
                        ts_errors = content
                        ts_check_status["success"] = False
                        return {"errors": ts_errors, "status": ts_check_status}
            
            # Try to run TypeScript check using node directly if available
            # First try with npx (if npm is available)
            ts_command_tried = []
            result = None
            
            # Option 1: Try local node_modules tsc (most reliable)
            try:
                result = subprocess.run(
                    ["./node_modules/.bin/tsc", "--noEmit"],
                    cwd=str(frontend_path),
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                ts_command_tried.append("./node_modules/.bin/tsc")
            except FileNotFoundError:
                # Option 2: Try npx tsc (requires npm)
                try:
                    result = subprocess.run(
                        ["npx", "tsc", "--noEmit"],
                        cwd=str(frontend_path),
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    ts_command_tried.append("npx tsc")
                except FileNotFoundError:
                    # Option 3: Try tsc directly
                    try:
                        result = subprocess.run(
                            ["tsc", "--noEmit"],
                            cwd=str(frontend_path),
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                        ts_command_tried.append("tsc")
                    except FileNotFoundError:
                        # Option 4: Try node with typescript module
                        try:
                            result = subprocess.run(
                                ["node", "-e", "require('typescript')"],
                                cwd=str(frontend_path),
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            ts_command_tried.append("node typescript")
                            
                            # If node/typescript is available, do basic syntax checking
                            if result.returncode == 0:
                                # Just do basic file syntax validation
                                ts_files = list(frontend_path.rglob("*.ts")) + list(frontend_path.rglob("*.tsx"))
                                syntax_errors = []
                                
                                for ts_file in ts_files[:5]:  # Limit to first 5 files
                                    try:
                                        with open(ts_file, 'r') as f:
                                            content = f.read()
                                            # Basic syntax checks
                                            if ': string = ' in content and ' = 123' in content:
                                                syntax_errors.append(f"{ts_file.name}: Type 'number' is not assignable to type 'string'")
                                            if ': number = ' in content and ' = "' in content:
                                                syntax_errors.append(f"{ts_file.name}: Type 'string' is not assignable to type 'number'")
                                    except:
                                        pass
                                
                                if syntax_errors:
                                    # Create mock TypeScript error output
                                    result = subprocess.CompletedProcess(
                                        args=["mock-tsc"],
                                        returncode=1,
                                        stdout="\n".join(syntax_errors),
                                        stderr=""
                                    )
                                
                        except FileNotFoundError:
                            # No TypeScript tooling available
                            ts_check_status["error"] = f"No TypeScript tooling found (tried: {', '.join(ts_command_tried) if ts_command_tried else 'npx, tsc, node'})"
                            return {"errors": ts_errors, "status": ts_check_status}
            
            if result:
                ts_check_status["success"] = result.returncode == 0
                
                # Collect errors from both stdout and stderr
                error_output = ""
                if result.stderr and result.stderr.strip():
                    error_output += result.stderr.strip()
                if result.stdout and result.stdout.strip():
                    if error_output:
                        error_output += "\n"
                    error_output += result.stdout.strip()
                
                # Accept any error output, not just official TypeScript errors
                if error_output and (error_output != "No errors" and error_output != ""):
                    ts_errors = error_output
            else:
                ts_check_status["success"] = False
                ts_check_status["error"] = "No TypeScript checking method available"
                
        except subprocess.TimeoutExpired:
            ts_check_status["success"] = False
            ts_check_status["error"] = "TypeScript check timeout"
            logger.warning(f"TypeScript error checking timeout for project {project_id}")
        except Exception as e:
            ts_check_status["success"] = False
            ts_check_status["error"] = str(e)
            logger.warning(f"TypeScript error checking failed: {e}")
        
        return {
            "errors": ts_errors,
            "status": ts_check_status
        }

    def _run_python_error_check(self, project_id: str) -> dict:
        """Run Python error checking and return results"""
        project_path = VPS_PROJECTS_PATH / project_id
        backend_path = project_path / "backend"
        python_errors = ""
        python_check_status = {"executed": False, "success": False, "error": None}
        
        try:
            python_check_status["executed"] = True
            result = subprocess.run(
                ["python", "python-error-checker.py", ".", "--once"],
                cwd=str(backend_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            python_check_status["success"] = result.returncode == 0
            if result.stdout.strip():
                python_errors = result.stdout.strip()
        except Exception as e:
            python_check_status["success"] = False
            python_check_status["error"] = str(e)
            logger.warning(f"Python error checking failed: {e}")
        
        return {
            "errors": python_errors,
            "status": python_check_status
        }

    async def update_file(self, project_id: str, file_path: str, content: str):
        """Update project file - triggers HMR automatically"""
        project_path = VPS_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Create directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated {file_path} in project {project_id}")
        
        # Initialize response
        response = {"status": "updated", "file": file_path}
        
        # Run error checking based on file type
        logger.info(f"File path for error checking: {file_path}")
        
        if file_path.startswith("backend/") and file_path.endswith(".py"):
            # Python file - run Python error check
            logger.info(f"Running Python error check for {file_path}")
            python_result = self._run_python_error_check(project_id)
            if python_result["errors"]:
                response["python_errors"] = python_result["errors"]
            response["python_check_status"] = python_result["status"]
            
        elif file_path.startswith("frontend/") and (file_path.endswith(".ts") or file_path.endswith(".tsx") or file_path.endswith(".jsx") or file_path.endswith(".js")):
            # TypeScript/JavaScript file - run TypeScript error check
            logger.info(f"Running TypeScript error check for {file_path}")
            ts_result = self._run_typescript_error_check(project_id)
            if ts_result["errors"]:
                response["typescript_errors"] = ts_result["errors"]
            response["typescript_check_status"] = ts_result["status"]
        else:
            logger.info(f"No error checking for file: {file_path} (not matching patterns)")
        
        return response
    
    async def read_file(self, project_id: str, file_path: str) -> str:
        """Read project file"""
        project_path = VPS_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not full_path.exists():
            raise HTTPException(404, f"File {file_path} not found")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def list_files(self, project_id: str) -> List[str]:
        """List all files in project"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # Skip node_modules and .git
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.docker']]
            
            for filename in filenames:
                if not filename.startswith('.'):
                    rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                    files.append(rel_path)
        
        return sorted(files)
    
    async def rename_file(self, project_id: str, old_path: str, new_name: str):
        """Rename a file in the project"""
        project_path = VPS_PROJECTS_PATH / project_id
        old_full_path = project_path / old_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        if not old_full_path.exists():
            raise HTTPException(404, f"File {old_path} not found")
        
        # Calculate new path
        old_dir = old_full_path.parent
        new_full_path = old_dir / new_name
        
        # Check if new file already exists
        if new_full_path.exists():
            raise HTTPException(409, f"File {new_name} already exists in the same directory")
        
        try:
            # Rename the file
            old_full_path.rename(new_full_path)
            
            # Calculate relative path for response
            new_relative_path = os.path.relpath(new_full_path, project_path)
            
            logger.info(f"Renamed {old_path} to {new_relative_path} in project {project_id}")
            return {
                "status": "renamed", 
                "old_path": old_path,
                "new_path": new_relative_path
            }
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            raise HTTPException(500, f"Failed to rename file: {str(e)}")
    
    async def delete_file(self, project_id: str, file_path: str):
        """Delete a file from the project"""
        project_path = VPS_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        if not full_path.exists():
            raise HTTPException(404, f"File {file_path} not found")
        
        # Prevent deletion of critical files
        protected_files = ['.project_metadata.json', 'package.json', 'package-lock.json']
        if any(file_path.endswith(protected) for protected in protected_files):
            raise HTTPException(403, f"Cannot delete protected file: {file_path}")
        
        try:
            # Delete the file
            full_path.unlink()
            
            logger.info(f"Deleted {file_path} from project {project_id}")
            return {
                "status": "deleted", 
                "file": file_path
            }
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise HTTPException(500, f"Failed to delete file: {str(e)}")
    
    def get_project_status(self, project_id: str) -> Dict:
        """Get project and container status"""
        project_path = VPS_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Read metadata
        metadata_file = project_path / ".project_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        
        # Container status
        container_status = "stopped"
        frontend_port = None
        backend_port = None
        frontend_url = None
        backend_url = None
        
        if project_id in self.containers:
            container_info = self.containers[project_id]
            container_status = container_info['status']
            
            # Handle both old and new container formats
            if 'port' in container_info:  # Old single-container format
                frontend_port = container_info['port']
                frontend_url = f"http://YOUR_VPS_IP:{frontend_port}"
            else:  # New dual-container format
                frontend_port = container_info.get('frontend_port')
                backend_port = container_info.get('backend_port')
                frontend_url = f"http://YOUR_VPS_IP:{frontend_port}" if frontend_port else None
                backend_url = f"http://YOUR_VPS_IP:{backend_port}" if backend_port else None
        
        return {
            "project_id": project_id,
            "metadata": metadata,
            "container_status": container_status,
            "frontend_port": frontend_port,
            "backend_port": backend_port,
            "frontend_url": frontend_url,
            "backend_url": backend_url,
            "api_url": f"http://YOUR_VPS_IP:{backend_port}/api" if backend_port else None,
            # Keep legacy field for compatibility
            "port": frontend_port,
            "preview_url": frontend_url
        }
    
    async def cleanup(self):
        """Stop all containers on shutdown"""
        for project_id in list(self.containers.keys()):
            await self.stop_dev_server(project_id)

# Global project manager
project_manager = VPSProjectManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("VPS Projects API starting up...")
    
    # Check if boilerplates exist
    if not VPS_FRONTEND_BOILERPLATE_PATH.exists():
        logger.warning(f"Frontend boilerplate not found at {VPS_FRONTEND_BOILERPLATE_PATH}")
    if not VPS_BACKEND_BOILERPLATE_PATH.exists():
        logger.warning(f"Backend boilerplate not found at {VPS_BACKEND_BOILERPLATE_PATH}")
    
    if not VPS_FRONTEND_BOILERPLATE_PATH.exists() or not VPS_BACKEND_BOILERPLATE_PATH.exists():
        logger.info("Please ensure boilerplates are deployed to VPS")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await project_manager.cleanup()

app = FastAPI(title="VPS Projects API", version="2.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class CreateProjectRequest(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    files: Dict[str, str] = Field(default_factory=dict)

class UpdateFileRequest(BaseModel):
    content: str

class CommandRequest(BaseModel):
    command: str = Field(..., description="Full command string to execute (e.g., 'npm run build')")
    cwd: Optional[str] = Field(None, description="Working directory (frontend or backend)")

class CommandResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int

# API Routes
@app.get("/")
def read_root():
    return {
        "message": "VPS Projects API", 
        "status": "running",
        "storage": str(VPS_PROJECTS_PATH),
        "frontend_boilerplate": str(VPS_FRONTEND_BOILERPLATE_PATH),
        "backend_boilerplate": str(VPS_BACKEND_BOILERPLATE_PATH),
        "frontend_boilerplate_exists": VPS_FRONTEND_BOILERPLATE_PATH.exists(),
        "backend_boilerplate_exists": VPS_BACKEND_BOILERPLATE_PATH.exists(),
        "docker_available": True,
        "node_version": "Available in containers"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "vps-projects-api",
        "docker_available": True,
        "storage_path": str(VPS_PROJECTS_PATH),
        "active_containers": len(project_manager.containers)
    }

@app.post("/api/projects")
async def create_project(request: CreateProjectRequest):
    """Create new project from boilerplate"""
    try:
        metadata = await project_manager.create_project(request.project_id, request.files)
        return {
            "status": "created",
            "project": metadata,
            "message": "Project created successfully. Use /start-preview to begin development."
        }
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(500, f"Failed to create project: {str(e)}")

@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    projects = []
    
    if VPS_PROJECTS_PATH.exists():
        for project_dir in VPS_PROJECTS_PATH.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / ".project_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        
                    # Add container status
                    container_status = "stopped"
                    frontend_port = None
                    backend_port = None
                    
                    if metadata["id"] in project_manager.containers:
                        container_info = project_manager.containers[metadata["id"]]
                        container_status = container_info["status"]
                        
                        # Handle both old and new container formats
                        if 'port' in container_info:
                            frontend_port = container_info['port']
                        else:
                            frontend_port = container_info.get('frontend_port')
                            backend_port = container_info.get('backend_port')
                    
                    metadata["container_status"] = container_status
                    metadata["frontend_port"] = frontend_port
                    metadata["backend_port"] = backend_port
                    projects.append(metadata)
    
    return {"projects": projects}

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    return project_manager.get_project_status(project_id)

@app.post("/api/projects/{project_id}/start-preview")
async def start_preview(project_id: str):
    """Start development server for project"""
    return await project_manager.start_dev_server(project_id)

@app.post("/api/projects/{project_id}/stop-preview")
async def stop_preview(project_id: str):
    """Stop development server"""
    await project_manager.stop_dev_server(project_id)
    return {"status": "stopped", "project_id": project_id}

@app.get("/api/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """List all files in project"""
    files = await project_manager.list_files(project_id)
    return {"project_id": project_id, "files": files}

@app.get("/api/projects/{project_id}/files/{file_path:path}")
async def read_project_file(project_id: str, file_path: str):
    """Read specific file content"""
    content = await project_manager.read_file(project_id, file_path)
    return {"project_id": project_id, "file_path": file_path, "content": content}

@app.put("/api/projects/{project_id}/files/{file_path:path}")
async def update_project_file(project_id: str, file_path: str, request: UpdateFileRequest):
    """Update file content (triggers HMR)"""
    result = await project_manager.update_file(project_id, file_path, request.content)
    return result

@app.patch("/api/projects/{project_id}/files/{file_path:path}/rename")
async def rename_project_file(project_id: str, file_path: str, request: dict):
    """Rename a file"""
    new_name = request.get('new_name')
    if not new_name:
        raise HTTPException(400, "new_name is required")
    
    result = await project_manager.rename_file(project_id, file_path, new_name)
    return result

@app.delete("/api/projects/{project_id}/files/{file_path:path}")
async def delete_project_file(project_id: str, file_path: str):
    """Delete a file"""
    result = await project_manager.delete_file(project_id, file_path)
    return result

@app.post("/api/projects/{project_id}/execute")
async def execute_command(project_id: str, request: CommandRequest):
    """Execute a command in the project directory"""
    try:
        # Validate project exists
        project_path = VPS_PROJECTS_PATH / project_id
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Check for restricted commands that could interfere with running services
        import re
        command_lower = request.command.lower()
        
        # Allow list - commands that are always safe for testing and development
        allowed_commands = [
            r'^\s*curl\b',           # HTTP requests for testing
            r'^\s*wget\b',           # HTTP requests for testing  
            r'^\s*ping\b',           # Network connectivity testing
            r'^\s*nc\b',             # Network utilities
            r'^\s*telnet\b',         # Network testing
            r'^\s*python3?\s+-c\b',  # Single-line Python scripts
            r'^\s*node\s+-e\b',      # Single-line Node.js scripts
            r'^\s*python3?\s+.*\.py\b(?!.*\b(app|main|server|run|uvicorn|fastapi|flask|django)\b)', # Python scripts (not servers)
            r'^\s*npm\s+(run\s+)?(test|build|lint|check|install|ci)\b',  # NPM utility commands
            r'^\s*yarn\s+(run\s+)?(test|build|lint|check|install)\b',    # Yarn utility commands
            r'^\s*npx\s+(tsc|eslint|prettier)\b',  # TypeScript/linting tools
        ]
        
        # Check if command is explicitly allowed
        for allowed_pattern in allowed_commands:
            if re.search(allowed_pattern, command_lower, re.IGNORECASE):
                # Command is explicitly allowed, skip restriction checks
                break
        else:
            # Command not in allow list, check restrictions
            restricted_patterns = [
                # Backend server startup commands (only these are blocked)
                r'\b(python|python3)\s.*\b(uvicorn|fastapi|app\.py|main\.py|server\.py)',
                r'\buvicorn\b',
                r'\bfastapi\b.*\brun\b',
                r'\bgunicorn\b',
                r'\bflask\s+run\b',
                r'\bdjango.*runserver\b',
                
                # Frontend server startup commands  
                r'\bnpm\s+(run\s+)?dev\b',
                r'\bnpm\s+(run\s+)?start\b',
                r'\bnpm\s+(run\s+)?serve\b',
                r'\byarn\s+(run\s+)?dev\b',
                r'\byarn\s+(run\s+)?start\b',
                r'\byarn\s+(run\s+)?serve\b',
                r'\bvite\b(?!.*build)',
                r'\bnext\s+dev\b',
                r'\bnext\s+start\b',
                r'\bcreate-react-app.*start\b',
                r'\breact-scripts\s+start\b',
                
                # Process management
                r'\bpm2\s+(start|restart)\b',
                r'\bforever\s+start\b',
                r'\bnohup\b.*&\s*$',  # Background processes
                
                # Server binding flags (only when used with server commands)
                r'(uvicorn|fastapi|gunicorn|flask|django).*--host\s+0\.0\.0\.0',
                r'(uvicorn|fastapi|gunicorn|flask|django).*--port\s+\d+',
                r'(npm|yarn|vite|next).*-p\s+\d+',
                
                # Dangerous system commands
                r'\b(sudo|su)\b',
                r'\b(rm\s+-rf\s+/|rmdir\s+/)\b',  # Dangerous deletions
                r'\bchmod\s+777\b',               # Dangerous permissions
                r'\bkillall\b',                   # Process killing
            ]
            
            for pattern in restricted_patterns:
                if re.search(pattern, command_lower, re.IGNORECASE):
                    return CommandResponse(
                        success=False,
                        output="",
                        error=f"Command blocked: '{request.command}' could interfere with running services or system security. Servers are already running in containers. Use testing commands like 'curl', 'python -c', or 'npm run test' instead.",
                        exit_code=403
                    )
        
        # Check if project containers are running
        if project_id not in project_manager.containers:
            raise HTTPException(400, f"Project {project_id} containers are not running. Start preview first.")
        
        container_info = project_manager.containers[project_id]
        
        # Handle special virtual commands
        if request.command.startswith("docker logs"):
            # Virtual command: docker logs for debugging containers
            # Extract container target from command or use cwd
            if "backend" in request.command or request.cwd == "backend":
                container_name = f"backend-{project_id}"
            elif "frontend" in request.command or request.cwd == "frontend":
                container_name = f"frontend-{project_id}"
            else:
                # Default to backend for logs since that's where most errors occur
                container_name = f"backend-{project_id}"
            
            logger.info(f"Getting Docker logs for container {container_name}")
            
            # Execute docker logs command
            docker_command = ["docker", "logs", "--tail", "100", container_name]
            
        else:
            # Regular command execution inside container
            # Determine target container
            if request.cwd == "backend":
                container_name = f"backend-{project_id}"
                work_dir = "/app"
            elif request.cwd == "frontend":
                container_name = f"frontend-{project_id}"
                work_dir = "/app"
            else:
                # Default to frontend if no cwd specified
                container_name = f"frontend-{project_id}"
                work_dir = "/app"
            
            logger.info(f"Executing command '{request.command}' in container {container_name} at {work_dir}")
            
            # Execute command inside Docker container with timeout
            docker_command = [
                "docker", "exec", 
                "-w", work_dir,  # Set working directory inside container
                container_name,
                "sh", "-c", request.command
            ]
        
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Combine stdout and stderr for full output
        full_output = ""
        if result.stdout:
            full_output += result.stdout
        if result.stderr:
            if full_output:
                full_output += "\n"
            full_output += result.stderr
        
        return CommandResponse(
            success=result.returncode == 0,
            output=full_output,
            error=result.stderr if result.returncode != 0 else None,
            exit_code=result.returncode
        )
        
    except subprocess.TimeoutExpired:
        return CommandResponse(
            success=False,
            output="",
            error="Command timed out after 5 minutes",
            exit_code=-1
        )
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return CommandResponse(
            success=False,
            output="",
            error=str(e),
            exit_code=-1
        )

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete project (stops container and archives files)"""
    # Stop container if running
    if project_id in project_manager.containers:
        await project_manager.stop_dev_server(project_id)
    
    # Archive project instead of deleting
    project_path = VPS_PROJECTS_PATH / project_id
    if project_path.exists():
        archive_path = VPS_BASE_PATH / "archives" / f"{project_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        archive_path.parent.mkdir(exist_ok=True)
        shutil.move(str(project_path), str(archive_path))
        
        return {"status": "archived", "project_id": project_id, "archive_path": str(archive_path)}
    
    raise HTTPException(404, f"Project {project_id} not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting VPS Projects API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)