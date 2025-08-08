#!/usr/bin/env python3
"""
Local Projects API - No Docker Version
Runs projects locally using subprocess instead of Docker containers
"""

from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import os
import shutil
import uuid
import json
import subprocess
import psutil
import signal
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local Configuration - NO DOCKER
LOCAL_BASE_PATH = Path.home() / "local-projects"
LOCAL_PROJECTS_PATH = LOCAL_BASE_PATH / "projects"
LOCAL_FRONTEND_BOILERPLATE_PATH = Path(__file__).parent / "boilerplate" / "shadcn-boilerplate"
LOCAL_BACKEND_BOILERPLATE_PATH = Path(__file__).parent / "boilerplate" / "backend-boilerplate"

# Ensure directories exist
LOCAL_BASE_PATH.mkdir(parents=True, exist_ok=True)
LOCAL_PROJECTS_PATH.mkdir(parents=True, exist_ok=True)

class LocalProjectManager:
    """Manages local processes for isolated project environments - NO DOCKER"""
    
    def __init__(self):
        self.processes: Dict[str, Dict] = {}  # Track local processes instead of containers
        self.frontend_port_pool = list(range(3001, 3999))  # Frontend ports
        self.backend_port_pool = list(range(8001, 8999))   # Backend ports
        
        # Initialize used_ports by scanning actual local processes
        self.used_ports = self._scan_used_ports()
        logger.info(f"Initialized with {len(self.used_ports)} ports already in use: {sorted(self.used_ports)}")
    
    def _scan_used_ports(self) -> set:
        """Scan local processes to find which ports are actually in use"""
        used_ports = set()
        try:
            # Get all network connections (need root privileges on macOS for all processes)
            # This may not work without sudo, so we'll handle the exception gracefully
            connections = psutil.net_connections(kind='inet')
            
            for conn in connections:
                if conn.laddr and conn.status == psutil.CONN_LISTEN:
                    port = conn.laddr.port
                    # Only track ports in our ranges
                    if (3001 <= port <= 3999) or (8001 <= port <= 8999):
                        used_ports.add(port)
                        logger.info(f"Found used port {port}")
                                    
        except (psutil.AccessDenied, OSError) as e:
            # On macOS, we might not have access to all processes
            logger.warning(f"Limited access to port scanning: {e}")
            logger.info("Starting with empty port tracking - will check ports individually")
            
        return used_ports
    
    def _get_available_port(self, port_type: str, preferred_port: int, max_attempts: int = 20) -> int:
        """Get next available port with sequential fallback strategy"""
        # Clean up stale port tracking first
        ports_to_remove = []
        for port in self.used_ports.copy():
            if self._is_port_actually_free(port):
                ports_to_remove.append(port)
        for port in ports_to_remove:
            self.used_ports.discard(port)
            logger.debug(f"Released stale port {port}")
        
        # Try ports sequentially starting from preferred port
        for attempt in range(max_attempts):
            candidate_port = preferred_port + attempt
            
            # Check if we've already allocated this port
            if candidate_port in self.used_ports:
                logger.debug(f"Port {candidate_port} already allocated, trying next")
                continue
                
            # Multi-level validation
            if self._validate_port_availability(candidate_port):
                self.used_ports.add(candidate_port)
                logger.info(f"✅ Allocated {port_type} port {candidate_port}")
                return candidate_port
            else:
                logger.debug(f"Port {candidate_port} not available, trying next")
        
        raise Exception(f"Could not find available {port_type} port after {max_attempts} attempts starting from {preferred_port}")
    
    def _validate_port_availability(self, port: int) -> bool:
        """Multi-level validation to check if port is truly available"""
        return self._socket_bind_test(port) and self._system_port_check(port)
    
    def _socket_bind_test(self, port: int) -> bool:
        """Test if we can bind to the port using socket"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1.0)  # Quick timeout
                sock.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False
        except Exception as e:
            logger.debug(f"Socket bind test failed for port {port}: {e}")
            return False
    
    def _system_port_check(self, port: int) -> bool:
        """Additional system-level port check using lsof if available"""
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            # If lsof returns no output, port is free
            return result.returncode != 0 or len(result.stdout.strip()) == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            # lsof not available or failed, fall back to socket test result
            return True
    
    def _is_port_actually_free(self, port: int) -> bool:
        """Backward compatibility method - use socket test only"""
        return self._socket_bind_test(port)
    
    def _get_frontend_port(self, preferred_port: int = 3001) -> int:
        """Get available frontend port with fallback"""
        return self._get_available_port("frontend", preferred_port, max_attempts=20)
    
    def _get_backend_port(self, preferred_port: int = 8001) -> int:
        """Get available backend port with fallback"""  
        return self._get_available_port("backend", preferred_port, max_attempts=20)
    
    async def _validate_service_running(self, port: int, service_type: str, max_wait: int = 10) -> bool:
        """Validate that service is actually running and responding on the port"""
        import urllib.request
        import urllib.error
        
        url = f"http://localhost:{port}"
        if service_type == "backend":
            url += "/"  # Try root endpoint for backend
            
        for attempt in range(max_wait):
            try:
                # Check if port is bound first (faster than HTTP request)
                if self._is_port_actually_free(port):
                    await asyncio.sleep(1)
                    continue
                    
                # Try HTTP request
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status < 500:  # Accept any non-server-error response
                        logger.info(f"✅ {service_type.title()} service validated on port {port}")
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, OSError) as e:
                logger.debug(f"Validation attempt {attempt + 1} failed for {service_type} port {port}: {e}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Unexpected error validating {service_type} port {port}: {e}")
                await asyncio.sleep(1)
        
        logger.warning(f"❌ {service_type.title()} service validation failed on port {port}")
        return False
    
    def _release_port(self, port: int):
        """Release port back to pool"""
        self.used_ports.discard(port)
    
    async def create_project(self, project_id: str, files: Dict[str, str]) -> Dict:
        """Create new monorepo project with frontend/ and backend/ folders - LOCAL VERSION"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        # Remove existing project if exists
        if project_path.exists():
            shutil.rmtree(project_path)
        
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Check boilerplates exist
        if not LOCAL_FRONTEND_BOILERPLATE_PATH.exists():
            raise HTTPException(500, f"Frontend boilerplate not found at {LOCAL_FRONTEND_BOILERPLATE_PATH}")
        if not LOCAL_BACKEND_BOILERPLATE_PATH.exists():
            raise HTTPException(500, f"Backend boilerplate not found at {LOCAL_BACKEND_BOILERPLATE_PATH}")
        
        # Copy frontend boilerplate to frontend/ folder (excluding heavy directories)
        frontend_path = project_path / "frontend"
        shutil.copytree(
            LOCAL_FRONTEND_BOILERPLATE_PATH, 
            frontend_path,
            ignore=shutil.ignore_patterns('node_modules', 'dist', 'build', '.next', '.vite', '__pycache__', '.mypy_cache', '.git')
        )
        logger.info(f"Copied frontend boilerplate to {frontend_path} (excluding node_modules and build files)")
        
        # Copy backend boilerplate to backend/ folder (excluding heavy directories)
        backend_path = project_path / "backend"
        shutil.copytree(
            LOCAL_BACKEND_BOILERPLATE_PATH, 
            backend_path,
            ignore=shutil.ignore_patterns('node_modules', 'dist', 'build', '__pycache__', '.mypy_cache', '.git', 'venv', '.venv', 'test_env', 'env', 'debug_output.txt', 'stderr.txt', 'stdout.txt', '*.log')
        )
        logger.info(f"Copied backend boilerplate to {backend_path} (excluding venv and cache files)")
        
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
        
        # Skip error checking during project creation for speed
        # Error checking will be done when files are updated or when explicitly requested
        logger.info("Skipping error checking during project creation for performance")
        
        return metadata

    def _run_python_error_check(self, project_id: str, file_path: str = None) -> dict:
        """Run comprehensive Python error checker with virtual environment support"""
        logger.info(f"Running ultimate Python error checker for {project_id}")
        project_path = LOCAL_PROJECTS_PATH / project_id
        backend_path = project_path / "backend"
        python_errors = ""
        python_check_status = {"executed": True, "success": True, "error": None}
        
        try:
            # Check if virtual environment exists
            venv_path = backend_path / "venv"
            venv_python = None
            
            # Try different venv locations
            possible_pythons = [
                venv_path / "bin" / "python",
                venv_path / "bin" / "python3",
                venv_path / "Scripts" / "python.exe",
                venv_path / "Scripts" / "python3.exe",
            ]
            
            for python_path in possible_pythons:
                if python_path.exists():
                    venv_python = str(python_path)
                    break
            
            if not venv_python:
                # Fallback to system Python
                python_cmd = "python3"
                if not subprocess.run([python_cmd, "--version"], capture_output=True).returncode == 0:
                    python_cmd = "python"
                logger.warning(f"No venv found, using system Python: {python_cmd}")
            else:
                python_cmd = venv_python
                logger.info(f"Using virtual environment Python: {python_cmd}")
            
            # PHASE 1: AST Syntax Analysis for all Python files
            errors = []
            warnings = []
            
            app_files = []
            exclude_dirs = {'test_env', 'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache'}
            
            for root, dirs, files in os.walk(backend_path):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if file.endswith('.py'):
                        app_files.append(os.path.join(root, file))
            
            # Track all imports found in the code
            all_imports = set()
            local_modules = set()
            
            for py_file in app_files:
                rel_path = os.path.relpath(py_file, backend_path)
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        import ast
                        tree = ast.parse(content, filename=py_file)
                        
                        # Collect all imports
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    all_imports.add(alias.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    module = node.module.split('.')[0]
                                    if node.level == 0:  # Absolute import
                                        all_imports.add(module)
                                    else:  # Relative import
                                        local_modules.add(module)
                        
                    except SyntaxError as e:
                        errors.append(f"❌ SYNTAX ERROR in {rel_path}:{e.lineno} - {e.msg}")
                        
                except Exception as e:
                    errors.append(f"❌ FILE ERROR in {rel_path} - {str(e)}")
            
            # PHASE 2: Import Testing in Virtual Environment (if venv exists)
            if venv_python:                
                # Test each import in the virtual environment
                missing_imports = set()
                
                for import_name in sorted(all_imports):
                    if import_name in local_modules or import_name in ['models', 'services', 'routers', 'dependencies']:
                        continue  # Skip local modules
                    
                    # Test if import works in venv
                    test_cmd = [python_cmd, '-c', f'import {import_name}']
                    try:
                        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode != 0:
                            missing_imports.add(import_name)
                            errors.append(f"❌ MISSING IMPORT: {import_name} - not available in virtual environment")
                    except subprocess.TimeoutExpired:
                        warnings.append(f"Import test timeout for {import_name}")
            
            # PHASE 3: Individual File Load Test + Full App Load Test
            # First, test each Python file individually to catch runtime errors
            for py_file in app_files:
                rel_path = os.path.relpath(py_file, backend_path)
                
                # Skip certain files that shouldn't be run directly
                if any(skip in rel_path for skip in ['__init__.py', 'test_', 'python-error-checker']):
                    continue
                
                # Test individual file execution (avoid running servers)
                if rel_path != 'app.py':  # Don't exec app.py directly as it starts servers
                    test_cmd = [python_cmd, '-c', f'import sys; sys.path.insert(0, "."); exec(open("{py_file}").read())']
                    try:
                        result = subprocess.run(test_cmd, cwd=str(backend_path), capture_output=True, text=True, timeout=5)
                        if result.returncode != 0:
                            error_output = result.stderr.strip()
                            if error_output and "ModuleNotFoundError" not in error_output:  # Avoid duplicate import errors
                                # Find the actual error line instead of just taking first line
                                error_lines = error_output.split('\n')
                                error_detail = None
                                for line in error_lines:
                                    if any(keyword in line for keyword in ['Error:', 'Exception:', 'TypeError:', 'ValueError:', 'NameError:', 'SyntaxError:']):
                                        error_detail = line.strip()
                                        break
                                
                                if not error_detail:
                                    # If no specific error found, use the last non-empty line
                                    error_detail = next((line for line in reversed(error_lines) if line.strip()), error_lines[0] if error_lines else "Unknown error")
                                
                                errors.append(f"❌ RUNTIME ERROR in {rel_path}: {error_detail}")
                    except subprocess.TimeoutExpired:
                        warnings.append(f"Runtime test timeout for {rel_path}")
                    except Exception:
                        pass  # Skip files that can't be tested this way
            
            # Then test main app.py loading
            test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

# Try to import and create the app
try:
    from app import app
    print("SUCCESS: app module imported")
    
    # Check if it's a FastAPI app
    if hasattr(app, 'routes'):
        print(f"SUCCESS: FastAPI app created with {len(app.routes)} routes")
    else:
        print("WARNING: app exists but doesn't appear to be a FastAPI app")
        
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
            
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
                tf.write(test_script)
                test_file = tf.name
            
            try:
                result = subprocess.run(
                    [python_cmd, test_file],
                    cwd=str(backend_path),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    # Parse the error to find specific issues
                    error_output = result.stderr + result.stdout
                    
                    # Look for ModuleNotFoundError
                    import re
                    module_matches = re.findall(r"ModuleNotFoundError: No module named '([^']+)'", error_output)
                    for module in module_matches:
                        errors.append(f"❌ RUNTIME ERROR: Missing module '{module}' prevents server startup")
                    
                    # Look for ImportError
                    import_matches = re.findall(r"ImportError: cannot import name '([^']+)'", error_output)
                    for name in import_matches:
                        errors.append(f"❌ RUNTIME ERROR: Cannot import '{name}' - check if function/class exists")
                    
                    # Look for AttributeError
                    attr_matches = re.findall(r"AttributeError: module '([^']+)' has no attribute '([^']+)'", error_output)
                    for module, attr in attr_matches:
                        errors.append(f"❌ RUNTIME ERROR: Module '{module}' has no attribute '{attr}'")
                    
                    if not (module_matches or import_matches or attr_matches):
                        # Generic error - show more detail
                        error_lines = error_output.strip().split('\n')
                        if error_lines:
                            # Find the actual error line (usually contains 'Error:' or 'Exception:')
                            error_detail = None
                            for line in error_lines:
                                if any(keyword in line for keyword in ['Error:', 'Exception:', 'TypeError:', 'ValueError:', 'NameError:']):
                                    error_detail = line.strip()
                                    break
                            
                            if not error_detail:
                                # If no specific error found, use the last non-empty line
                                error_detail = next((line for line in reversed(error_lines) if line.strip()), "Unknown error")
                            
                            errors.append(f"❌ RUNTIME ERROR: Failed to load app.py - {error_detail}")
                        else:
                            errors.append(f"❌ RUNTIME ERROR: Failed to load app.py - Unknown error")
                        
            except subprocess.TimeoutExpired:
                errors.append("❌ TIMEOUT: App load took too long (possible infinite loop)")
            finally:
                os.unlink(test_file)
            
            # PHASE 4: Requirements.txt validation is handled by the runtime tests above
            # No manual checking - rely on actual import tests and module loading
            
            # PHASE 5: Actual Server Start Test (only if no errors and doing full check)
            if not errors and not file_path:
                # Try to actually start the server
                start_cmd = [python_cmd, '-m', 'uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '0']
                
                try:
                    # Start server and immediately kill it (just testing if it starts)
                    process = subprocess.Popen(
                        start_cmd,
                        cwd=str(backend_path),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Wait a bit to see if it starts
                    import time
                    time.sleep(2)
                    
                    # Check if process is still running
                    if process.poll() is None:
                        # Server started successfully
                        logger.info("✅ Server starts successfully!")
                        process.terminate()
                    else:
                        # Server crashed
                        stdout, stderr = process.communicate()
                        error_msg = stderr or stdout
                        if error_msg:
                            errors.append(f"❌ SERVER CRASH: {error_msg.strip()[:200]}")
                            
                except Exception as e:
                    warnings.append(f"Could not test server start: {str(e)}")
            
            # Format results
            if errors:
                python_errors = f"Python Error Report\n{'='*50}\nTotal Errors: {len(errors)}\n\n" + "\n".join(errors)
                if warnings:
                    python_errors += f"\n\nWarnings:\n" + "\n".join(warnings)
                python_check_status["success"] = False
            else:
                python_errors = "✅ No Python errors found - Backend is ready to run!"
                python_check_status["success"] = True
                        
        except Exception as e:
            python_check_status["success"] = False
            python_check_status["error"] = str(e)
            logger.warning(f"Failed to run Python error checker: {e}")
            python_errors = f"Error running Python error checker: {e}"
        
        return {
            "errors": python_errors,
            "status": python_check_status
        }

    def _run_typescript_error_check(self, project_id: str) -> dict:
        """Run TypeScript error checking locally"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        frontend_path = project_path / "frontend"
        ts_errors = ""
        ts_check_status = {"executed": True, "success": True, "error": None}
        
        try:
            # Run TypeScript check using npx tsc with timeout
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=str(frontend_path),
                capture_output=True,
                text=True,
                timeout=20  # 20 second timeout for TypeScript
            )
            
            ts_check_status["success"] = result.returncode == 0
            
            if result.returncode != 0 and (result.stdout.strip() or result.stderr.strip()):
                error_output = (result.stderr + "\n" + result.stdout).strip()
                if error_output and error_output != "No errors":
                    ts_errors = error_output
                    ts_check_status["success"] = False
                    
        except Exception as e:
            ts_check_status["success"] = False
            ts_check_status["error"] = str(e)
            logger.warning(f"TypeScript error checking failed: {e}")
            ts_errors = f"Error running TypeScript error checker: {e}"
        
        return {
            "errors": ts_errors,
            "status": ts_check_status
        }

    async def start_backend(self, project_id: str) -> Dict:
        """Start only the backend service for a project"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Initialize project processes dict if not exists
        if project_id not in self.processes:
            self.processes[project_id] = {
                'backend_process': None,
                'frontend_process': None,
                'backend_port': None,
                'frontend_port': None,
                'status': 'stopped',
                'project_path': str(project_path)
            }
        
        process_info = self.processes[project_id]
        
        # Stop existing backend if running
        if process_info.get('backend_process') and process_info['backend_process'].poll() is None:
            process_info['backend_process'].terminate()
            if process_info.get('backend_port'):
                self._release_port(process_info['backend_port'])
        
        # Allocate backend port
        try:
            backend_port = self._get_backend_port(preferred_port=8001)
            logger.info(f"🚀 Allocated backend port: {backend_port}")
        except Exception as e:
            raise HTTPException(500, f"Backend port allocation failed: {str(e)}")
        
        try:
            backend_path = project_path / "backend"
            
            # Create virtual environment and install backend dependencies
            logger.info("Creating virtual environment and installing backend dependencies...")
            
            # Create venv if not exists
            venv_path = backend_path / "venv"
            if not venv_path.exists():
                venv_create = subprocess.run(
                    "python3 -m venv venv",
                    shell=True,
                    cwd=str(backend_path),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if venv_create.returncode != 0:
                    logger.warning(f"Venv creation issues: {venv_create.stderr}")
            
            # Install dependencies in venv
            pip_install = subprocess.run(
                "venv/bin/pip install -r requirements.txt",
                shell=True,
                cwd=str(backend_path),
                capture_output=True,
                text=True,
                timeout=120
            )
            if pip_install.returncode != 0:
                logger.warning(f"Backend pip install issues: {pip_install.stderr}")
            
            # Run Python error check before starting backend
            logger.info("Running Python error check before starting backend...")
            python_check = self._run_python_error_check(project_id)
            if not python_check["status"]["success"]:
                self._release_port(backend_port)
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot start backend - Python errors found:\n{python_check['errors']}"
                )
            
            # Start Backend Process using virtual environment
            backend_cmd = f"venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port {backend_port} --reload"
            backend_process = subprocess.Popen(
                backend_cmd,
                shell=True,
                cwd=str(backend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": str(backend_path)}
            )
            
            logger.info(f"Started backend: {backend_cmd} (PID: {backend_process.pid})")
            
            # Validate backend process startup
            logger.info("⏳ Waiting for backend to initialize...")
            await asyncio.sleep(5)
            
            # Check if backend process is still alive
            if backend_process.poll() is not None:
                stdout, stderr = backend_process.communicate()
                logger.error(f"Backend stdout: {stdout.decode('utf-8', errors='ignore')}")
                logger.error(f"Backend stderr: {stderr.decode('utf-8', errors='ignore')}")
                self._release_port(backend_port)
                raise Exception(f"Backend process exited with code {backend_process.returncode}")
            
            logger.info(f"✅ Backend process started on port {backend_port}")
            
            # Update process info
            process_info.update({
                'backend_process': backend_process,
                'backend_port': backend_port,
                'status': 'backend_running' if not process_info.get('frontend_process') else 'running'
            })
            
            return {
                "project_id": project_id,
                "service": "backend",
                "status": "started",
                "backend_port": backend_port,
                "backend_url": f"http://localhost:{backend_port}"
            }
                
        except Exception as e:
            # Cleanup on failure
            self._release_port(backend_port)
            logger.error(f"Failed to start backend: {e}")
            raise HTTPException(500, f"Failed to start backend: {str(e)}")
    
    async def start_frontend(self, project_id: str) -> Dict:
        """Start only the frontend service for a project"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Initialize project processes dict if not exists
        if project_id not in self.processes:
            self.processes[project_id] = {
                'backend_process': None,
                'frontend_process': None,
                'backend_port': None,
                'frontend_port': None,
                'status': 'stopped',
                'project_path': str(project_path)
            }
        
        process_info = self.processes[project_id]
        
        # Stop existing frontend if running
        if process_info.get('frontend_process') and process_info['frontend_process'].poll() is None:
            process_info['frontend_process'].terminate()
            if process_info.get('frontend_port'):
                self._release_port(process_info['frontend_port'])
        
        # Allocate frontend port
        try:
            frontend_port = self._get_frontend_port(preferred_port=3001)
            logger.info(f"🚀 Allocated frontend port: {frontend_port}")
        except Exception as e:
            raise HTTPException(500, f"Frontend port allocation failed: {str(e)}")
        
        try:
            frontend_path = project_path / "frontend"
            
            # Install frontend dependencies
            logger.info("Installing frontend dependencies...")
            npm_install = subprocess.run(
                "npm install",
                shell=True,
                cwd=str(frontend_path),
                capture_output=True,
                text=True,
                timeout=120
            )
            if npm_install.returncode != 0:
                logger.warning(f"Frontend npm install issues: {npm_install.stderr}")
            
            # Get backend URL for environment
            backend_port = process_info.get('backend_port', 8001)  # Default fallback
            backend_url = f"http://localhost:{backend_port}"
            
            # Start Frontend Process
            frontend_cmd = f"npm run dev -- --host 0.0.0.0 --port {frontend_port}"
            frontend_process = subprocess.Popen(
                frontend_cmd,
                shell=True,
                cwd=str(frontend_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "VITE_API_URL": backend_url}
            )
            
            logger.info(f"Started frontend: {frontend_cmd} (PID: {frontend_process.pid})")
            
            # Validate frontend process startup  
            logger.info("⏳ Waiting for frontend to initialize...")
            await asyncio.sleep(4)
            
            # Check if frontend process is still alive
            if frontend_process.poll() is not None:
                logger.error(f"❌ Frontend process exited with code {frontend_process.returncode}")
                self._release_port(frontend_port)
                
                # Try fallback port for frontend
                logger.info("🔄 Trying fallback port for frontend...")
                try:
                    frontend_port = self._get_frontend_port(preferred_port=frontend_port + 1)
                    frontend_cmd = f"npm run dev -- --host 0.0.0.0 --port {frontend_port}"
                    frontend_process = subprocess.Popen(
                        frontend_cmd,
                        shell=True,
                        cwd=str(frontend_path),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env={**os.environ, "VITE_API_URL": backend_url}
                    )
                    await asyncio.sleep(4)
                    if frontend_process.poll() is not None:
                        frontend_process.terminate()
                        self._release_port(frontend_port)
                        raise Exception("Frontend failed to start on fallback port")
                        
                except Exception as fallback_e:
                    raise Exception(f"Frontend startup failed: {fallback_e}")
            
            logger.info(f"✅ Frontend process started on port {frontend_port}")
            
            # Update process info
            process_info.update({
                'frontend_process': frontend_process,
                'frontend_port': frontend_port,
                'status': 'frontend_running' if not process_info.get('backend_process') else 'running'
            })
            
            return {
                "project_id": project_id,
                "service": "frontend",
                "status": "started",
                "frontend_port": frontend_port,
                "frontend_url": f"http://localhost:{frontend_port}"
            }
                
        except Exception as e:
            # Cleanup on failure
            self._release_port(frontend_port)
            logger.error(f"Failed to start frontend: {e}")
            raise HTTPException(500, f"Failed to start frontend: {str(e)}")
    
    async def restart_backend(self, project_id: str) -> Dict:
        """Restart the backend service for a project"""
        if project_id in self.processes and self.processes[project_id].get('backend_process'):
            # Stop existing backend
            backend_process = self.processes[project_id]['backend_process']
            backend_port = self.processes[project_id].get('backend_port')
            
            if backend_process and backend_process.poll() is None:
                backend_process.terminate()
                try:
                    backend_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    backend_process.kill()
                
            if backend_port:
                self._release_port(backend_port)
                
            # Clear backend info
            self.processes[project_id]['backend_process'] = None
            self.processes[project_id]['backend_port'] = None
        
        # Start backend again
        return await self.start_backend(project_id)
    
    async def restart_frontend(self, project_id: str) -> Dict:
        """Restart the frontend service for a project"""
        if project_id in self.processes and self.processes[project_id].get('frontend_process'):
            # Stop existing frontend
            frontend_process = self.processes[project_id]['frontend_process']
            frontend_port = self.processes[project_id].get('frontend_port')
            
            if frontend_process and frontend_process.poll() is None:
                frontend_process.terminate()
                try:
                    frontend_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    frontend_process.kill()
                
            if frontend_port:
                self._release_port(frontend_port)
                
            # Clear frontend info
            self.processes[project_id]['frontend_process'] = None
            self.processes[project_id]['frontend_port'] = None
        
        # Start frontend again
        return await self.start_frontend(project_id)
    
    async def setup_environment(self, project_id: str) -> Dict:
        """Setup project environment (venv, packages) without starting services"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        try:
            backend_path = project_path / "backend"
            frontend_path = project_path / "frontend"
            
            logger.info(f"Setting up environment for project {project_id}")
            
            # Backend setup: Create virtual environment and install dependencies
            if backend_path.exists():
                logger.info("Setting up backend environment...")
                
                # Create venv if not exists
                venv_path = backend_path / "venv"
                if not venv_path.exists():
                    venv_create = subprocess.run(
                        "python3 -m venv venv",
                        shell=True,
                        cwd=str(backend_path),
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if venv_create.returncode != 0:
                        logger.warning(f"Backend venv creation issues: {venv_create.stderr}")
                    else:
                        logger.info("✅ Backend virtual environment created")
                else:
                    logger.info("✅ Backend virtual environment already exists")
                
                # Install dependencies in venv
                requirements_file = backend_path / "requirements.txt"
                if requirements_file.exists():
                    pip_install = subprocess.run(
                        "venv/bin/pip install -r requirements.txt",
                        shell=True,
                        cwd=str(backend_path),
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if pip_install.returncode != 0:
                        logger.warning(f"Backend pip install issues: {pip_install.stderr}")
                    else:
                        logger.info("✅ Backend dependencies installed")
                
                # Run Python error check
                logger.info("Running Python error check...")
                python_check = self._run_python_error_check(project_id)
                if not python_check["status"]["success"]:
                    logger.warning(f"Python errors found: {python_check['errors']}")
            
            # Frontend setup: Install npm dependencies
            if frontend_path.exists():
                logger.info("Setting up frontend environment...")
                
                package_json = frontend_path / "package.json"
                if package_json.exists():
                    npm_install = subprocess.run(
                        "npm install",
                        shell=True,
                        cwd=str(frontend_path),
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if npm_install.returncode != 0:
                        logger.warning(f"Frontend npm install issues: {npm_install.stderr}")
                    else:
                        logger.info("✅ Frontend dependencies installed")
            
            return {
                "project_id": project_id,
                "status": "environment_setup_complete",
                "message": "Virtual environment and dependencies setup completed. Services can be started using action tags.",
                "backend_ready": backend_path.exists() and (backend_path / "venv").exists(),
                "frontend_ready": frontend_path.exists() and (frontend_path / "node_modules").exists(),
                "python_errors": python_check.get("errors", "") if backend_path.exists() else None
            }
                
        except Exception as e:
            logger.error(f"Failed to setup environment: {e}")
            raise HTTPException(500, f"Failed to setup environment: {str(e)}")
    
    async def start_dev_server(self, project_id: str) -> Dict:
        """Start both backend and frontend local processes (legacy method for compatibility)"""
        # Start backend first
        backend_result = await self.start_backend(project_id)
        
        # Then start frontend
        frontend_result = await self.start_frontend(project_id)
        
        # Return combined result
        return {
            "project_id": project_id,
            "status": "running",
            "frontend_port": frontend_result['frontend_port'],
            "backend_port": backend_result['backend_port'], 
            "frontend_url": frontend_result['frontend_url'],
            "backend_url": backend_result['backend_url'],
            "backend_url": backend_result['backend_url']
        }
    
    async def stop_dev_server(self, project_id: str):
        """Stop both frontend and backend processes for project"""
        if project_id not in self.processes:
            return
        
        process_info = self.processes[project_id]
        
        backend_process = process_info.get('backend_process')
        frontend_process = process_info.get('frontend_process')
        backend_port = process_info.get('backend_port')
        frontend_port = process_info.get('frontend_port')
        
        # Stop backend process
        if backend_process and backend_process.poll() is None:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=10)
                logger.info(f"Stopped backend process for project {project_id}")
            except subprocess.TimeoutExpired:
                backend_process.kill()
                logger.warning(f"Force killed backend process for project {project_id}")
            except Exception as e:
                logger.error(f"Error stopping backend process: {e}")
        
        # Stop frontend process
        if frontend_process and frontend_process.poll() is None:
            try:
                frontend_process.terminate()
                frontend_process.wait(timeout=10)
                logger.info(f"Stopped frontend process for project {project_id}")
            except subprocess.TimeoutExpired:
                frontend_process.kill()
                logger.warning(f"Force killed frontend process for project {project_id}")
            except Exception as e:
                logger.error(f"Error stopping frontend process: {e}")
        
        # Release both ports
        if backend_port:
            self._release_port(backend_port)
        if frontend_port:
            self._release_port(frontend_port)
        
        # Remove from processes dict
        del self.processes[project_id]
    
    async def update_file(self, project_id: str, file_path: str, content: str):
        """Update project file - triggers HMR automatically for local dev servers"""
        project_path = LOCAL_PROJECTS_PATH / project_id
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
        
        # Handle requirements.txt updates - automatically install dependencies
        if file_path == "backend/requirements.txt":
            backend_path = project_path / "backend"
            venv_python = backend_path / "venv" / "bin" / "python"
            
            if venv_python.exists():
                logger.info(f"Requirements.txt updated - installing dependencies in virtual environment...")
                try:
                    # Run pip install with timeout
                    pip_result = subprocess.run([
                        str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"
                    ], cwd=str(backend_path), capture_output=True, text=True, timeout=120)
                    
                    if pip_result.returncode == 0:
                        response["pip_install"] = {
                            "success": True,
                            "output": pip_result.stdout,
                            "message": "Dependencies installed successfully"
                        }
                        logger.info("✅ Dependencies installed successfully")
                    else:
                        response["pip_install"] = {
                            "success": False,
                            "output": pip_result.stdout,
                            "error": pip_result.stderr,
                            "message": "Failed to install some dependencies"
                        }
                        logger.warning(f"❌ Pip install failed: {pip_result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    response["pip_install"] = {
                        "success": False,
                        "error": "Pip install timed out after 120 seconds",
                        "message": "Dependencies installation timed out"
                    }
                    logger.warning("❌ Pip install timed out")
                except Exception as e:
                    response["pip_install"] = {
                        "success": False,
                        "error": str(e),
                        "message": "Error during pip install"
                    }
                    logger.error(f"❌ Pip install error: {str(e)}")
            else:
                response["pip_install"] = {
                    "success": False,
                    "error": "Virtual environment not found",
                    "message": "No virtual environment found - dependencies not installed"
                }
                logger.warning("❌ No virtual environment found for pip install")
        
        # Run error checking based on file type with timeout protection
        if file_path.startswith("backend/") and file_path.endswith(".py"):
            try:
                # Run Python error check with overall timeout
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("Python error check timed out")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second timeout
                
                python_result = self._run_python_error_check(project_id, file_path)
                response["python_errors"] = python_result["errors"]
                response["python_check_status"] = python_result["status"]
                
                signal.alarm(0)  # Cancel timeout
                
            except (TimeoutError, Exception) as e:
                signal.alarm(0)  # Cancel timeout
                logger.warning(f"Python error check failed/timed out: {e}")
                response["python_errors"] = f"Error check timed out: {str(e)}"
                response["python_check_status"] = {"executed": False, "success": False, "error": str(e)}
            
        elif file_path.startswith("frontend/") and (file_path.endswith(".ts") or file_path.endswith(".tsx") or file_path.endswith(".jsx") or file_path.endswith(".js")):
            try:
                # Run TypeScript error check with overall timeout
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("TypeScript error check timed out")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second timeout
                
                ts_result = self._run_typescript_error_check(project_id)
                if ts_result["errors"]:
                    response["typescript_errors"] = ts_result["errors"]
                response["typescript_check_status"] = ts_result["status"]
                
                signal.alarm(0)  # Cancel timeout
                
            except (TimeoutError, Exception) as e:
                signal.alarm(0)  # Cancel timeout
                logger.warning(f"TypeScript error check failed/timed out: {e}")
                response["typescript_errors"] = f"Error check timed out: {str(e)}"
                response["typescript_check_status"] = {"executed": False, "success": False, "error": str(e)}
        
        return response

    async def read_file(self, project_id: str, file_path: str) -> str:
        """Read project file"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not full_path.exists():
            raise HTTPException(404, f"File {file_path} not found")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def list_files(self, project_id: str) -> List[str]:
        """List all files in project"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # Skip node_modules and .git
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.mypy_cache', 'dist', 'build']]
            
            for filename in filenames:
                if not filename.startswith('.'):
                    rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                    files.append(rel_path)
        
        return sorted(files)

    def get_project_status(self, project_id: str) -> Dict:
        """Get project and process status"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Read metadata
        metadata_file = project_path / ".project_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        
        # Process status
        process_status = "stopped"
        frontend_port = None
        backend_port = None
        frontend_url = None
        backend_url = None
        
        if project_id in self.processes:
            process_info = self.processes[project_id]
            process_status = process_info['status']
            frontend_port = process_info.get('frontend_port')
            backend_port = process_info.get('backend_port')
            frontend_url = f"http://localhost:{frontend_port}" if frontend_port else None
            backend_url = f"http://localhost:{backend_port}" if backend_port else None
        
        return {
            "project_id": project_id,
            "metadata": metadata,
            "container_status": process_status,  # Keep same field name for compatibility
            "frontend_port": frontend_port,
            "backend_port": backend_port,
            "frontend_url": frontend_url,
            "backend_url": backend_url,
            "backend_url": f"http://localhost:{backend_port}" if backend_port else None,
            "port": frontend_port,  # Legacy compatibility
            "preview_url": frontend_url  # Legacy compatibility
        }

    async def cleanup(self):
        """Stop all processes on shutdown"""
        for project_id in list(self.processes.keys()):
            await self.stop_dev_server(project_id)

# Pydantic models
class CreateProjectRequest(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    files: Dict[str, str] = Field(default_factory=dict)

class UpdateFileRequest(BaseModel):
    content: str

class CommandRequest(BaseModel):
    command: str = Field(..., description="Full command string to execute")
    cwd: Optional[str] = Field(None, description="Working directory (frontend or backend)")

class CommandResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int

# Global project manager
project_manager = LocalProjectManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Local Projects API starting up...")
    
    # Check if boilerplates exist
    if not LOCAL_FRONTEND_BOILERPLATE_PATH.exists():
        logger.warning(f"Frontend boilerplate not found at {LOCAL_FRONTEND_BOILERPLATE_PATH}")
    if not LOCAL_BACKEND_BOILERPLATE_PATH.exists():
        logger.warning(f"Backend boilerplate not found at {LOCAL_BACKEND_BOILERPLATE_PATH}")
    
    if not LOCAL_FRONTEND_BOILERPLATE_PATH.exists() or not LOCAL_BACKEND_BOILERPLATE_PATH.exists():
        logger.info("Please ensure boilerplates are available in projects-api/boilerplate/")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await project_manager.cleanup()

app = FastAPI(title="Local Projects API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/")
def read_root():
    return {
        "message": "Local Projects API (No Docker)", 
        "status": "running",
        "storage": str(LOCAL_PROJECTS_PATH),
        "frontend_boilerplate": str(LOCAL_FRONTEND_BOILERPLATE_PATH),
        "backend_boilerplate": str(LOCAL_BACKEND_BOILERPLATE_PATH),
        "frontend_boilerplate_exists": LOCAL_FRONTEND_BOILERPLATE_PATH.exists(),
        "backend_boilerplate_exists": LOCAL_BACKEND_BOILERPLATE_PATH.exists(),
        "docker_available": False,  # This is the local version
        "node_version": "Local system Node.js"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "local-projects-api",
        "docker_available": False,
        "storage_path": str(LOCAL_PROJECTS_PATH),
        "active_processes": len(project_manager.processes)
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
    
    if LOCAL_PROJECTS_PATH.exists():
        for project_dir in LOCAL_PROJECTS_PATH.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / ".project_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        
                    # Add process status
                    process_status = "stopped"
                    frontend_port = None
                    backend_port = None
                    
                    if metadata["id"] in project_manager.processes:
                        process_info = project_manager.processes[metadata["id"]]
                        process_status = process_info["status"]
                        frontend_port = process_info.get('frontend_port')
                        backend_port = process_info.get('backend_port')
                    
                    metadata["container_status"] = process_status
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

@app.post("/api/projects/{project_id}/start-backend")
async def start_backend_service(project_id: str):
    """Start only the backend service"""
    return await project_manager.start_backend(project_id)

@app.post("/api/projects/{project_id}/start-frontend")
async def start_frontend_service(project_id: str):
    """Start only the frontend service"""
    return await project_manager.start_frontend(project_id)

@app.post("/api/projects/{project_id}/restart-backend")
async def restart_backend_service(project_id: str):
    """Restart the backend service"""
    return await project_manager.restart_backend(project_id)

@app.post("/api/projects/{project_id}/restart-frontend")
async def restart_frontend_service(project_id: str):
    """Restart the frontend service"""
    return await project_manager.restart_frontend(project_id)

@app.post("/api/projects/{project_id}/setup-environment")
async def setup_project_environment(project_id: str):
    """Setup project environment (venv, packages) without starting services"""
    return await project_manager.setup_environment(project_id)

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
    """Update file content (triggers HMR automatically)"""
    result = await project_manager.update_file(project_id, file_path, request.content)
    return result

@app.post("/api/projects/{project_id}/execute")
async def execute_command(project_id: str, request: CommandRequest):
    """Execute a command in the project directory with server management restrictions"""
    try:
        # Validate project exists
        project_path = LOCAL_PROJECTS_PATH / project_id
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        # Check if this project has managed servers running
        project_status = project_manager.get_project_status(project_id)
        is_running = project_status.get("container_status") == "running"
        frontend_port = project_status.get("frontend_port")
        backend_port = project_status.get("backend_port")
        
        # Block server start/stop commands
        blocked_patterns = [
            r"uvicorn.*app.*--host.*--port",
            r"python.*app\.py",
            r"npm.*run.*dev",
            r"npm.*start",
            r"yarn.*dev",
            r"yarn.*start",
            r"node.*server",
            r"fastapi.*dev",
            r"flask.*run",
            r"django.*runserver"
        ]
        
        import re
        command_lower = request.command.lower()
        
        for pattern in blocked_patterns:
            if re.search(pattern, command_lower):
                # Provide helpful guidance instead of executing
                guidance_msg = "🚫 SERVER COMMAND BLOCKED\n\n"
                
                if is_running:
                    guidance_msg += f"✅ Your project servers are already managed and running:\n"
                    if frontend_port:
                        guidance_msg += f"   • Frontend: http://localhost:{frontend_port}\n"
                    if backend_port:
                        guidance_msg += f"   • Backend: http://localhost:{backend_port}\n"
                        guidance_msg += f"   • API: http://localhost:{backend_port}/api\n"
                    guidance_msg += "\n📋 TESTING INSTRUCTIONS:\n"
                    guidance_msg += "• To test if your backend is working: make an HTTP request to the API endpoints\n"
                    guidance_msg += "• To debug errors: CREATE or EDIT a test file (it will trigger error checking)\n"
                    guidance_msg += "• To see backend logs: check the managed preview logs\n"
                    guidance_msg += "• Example test file: Create 'backend/test_debug.py' with a simple import test\n"
                else:
                    guidance_msg += f"❌ Your project servers are not running.\n"
                    guidance_msg += f"📋 TO START SERVERS:\n"
                    guidance_msg += f"• Use the 'Start Preview' button or API endpoint\n"
                    guidance_msg += f"• This will properly start both frontend and backend with error checking\n"
                    guidance_msg += f"• Manual server commands are blocked to prevent port conflicts\n"
                
                guidance_msg += f"\n💡 DEBUGGING TIP:\n"
                guidance_msg += f"If the API is not responding, create a simple test file to trigger error checking:\n"
                guidance_msg += f"Example: Create 'backend/debug_test.py' with 'import app' to see any import errors"
                
                return CommandResponse(
                    success=False,
                    output=guidance_msg,
                    error="Server command blocked - servers are managed automatically",
                    exit_code=1
                )
        
        # Determine target directory
        if request.cwd == "backend":
            work_dir = project_path / "backend"
        elif request.cwd == "frontend":
            work_dir = project_path / "frontend"
        else:
            # Default to project root
            work_dir = project_path
        
        logger.info(f"Executing command '{request.command}' in {work_dir}")
        
        # Modify command to use virtual environment if running in backend
        command_to_run = request.command
        if request.cwd == "backend":
            # Check if venv exists in backend directory (consistent with start_dev_server)
            venv_activate = work_dir / "venv" / "bin" / "activate"
            if venv_activate.exists():
                # Use the same pattern as start_dev_server: source venv and run command
                command_to_run = f"source venv/bin/activate && {request.command}"
                logger.info(f"Using virtual environment: {command_to_run}")
        
        # Execute command locally with timeout
        result = subprocess.run(
            command_to_run,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for user commands
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
            error="Command timed out after 30 seconds",
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
    """Delete project (stops processes and archives files)"""
    # Stop processes if running
    if project_id in project_manager.processes:
        await project_manager.stop_dev_server(project_id)
    
    # Archive project instead of deleting
    project_path = LOCAL_PROJECTS_PATH / project_id
    if project_path.exists():
        archive_path = LOCAL_BASE_PATH / "archives" / f"{project_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        archive_path.parent.mkdir(exist_ok=True)
        shutil.move(str(project_path), str(archive_path))
        
        return {"status": "archived", "project_id": project_id, "archive_path": str(archive_path)}
    
    raise HTTPException(404, f"Project {project_id} not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Local Projects API on port {port}")
    uvicorn.run("local-api:app", host="0.0.0.0", port=port, reload=True)