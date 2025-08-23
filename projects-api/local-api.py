#!/usr/bin/env python3
"""
Local Projects API - No Docker Version
Runs projects locally using subprocess instead of Docker containers
"""

from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
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
LOCAL_FRONTEND_BOILERPLATE_PATH = Path(__file__).parent / "boilerplate" / "shadcn-boilerplate"  # React boilerplate with custom CSS (not shadcn components)
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
        
        # Log capture system
        self.logs_base_path = LOCAL_BASE_PATH / "logs"
        self.logs_base_path.mkdir(exist_ok=True)
        self.log_checkpoints: Dict[str, Dict[str, int]] = {}  # {project_id: {service: last_line_seen}}
    
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

    async def _detect_backend_url(self, project_id: str) -> str:
        """Detect if backend is running and return its URL, otherwise return default"""
        process_info = self.processes.get(project_id, {})
        
        # First, check if we have a backend process and port recorded
        backend_port = process_info.get('backend_port')
        backend_process = process_info.get('backend_process')
        
        if backend_port and backend_process:
            # Check if the recorded backend process is still running
            if backend_process.poll() is None:
                # Process is running, verify it's actually responding
                backend_url = f"http://localhost:{backend_port}"
                try:
                    # Try to ping the backend health endpoint
                    import aiohttp
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                        async with session.get(f"{backend_url}/health") as response:
                            if response.status == 200:
                                logger.info(f"✅ Backend detected and responding at {backend_url}")
                                return backend_url
                            else:
                                logger.warning(f"⚠️ Backend at {backend_url} not responding properly (status: {response.status})")
                except Exception as e:
                    logger.warning(f"⚠️ Backend at {backend_url} not responding: {e}")
            else:
                logger.warning(f"⚠️ Backend process for {project_id} has exited")
        
        # If we couldn't detect a running backend, check for any backend on common ports
        common_backend_ports = [8001, 8000, 8002, 8003, 8004]
        
        for port in common_backend_ports:
            backend_url = f"http://localhost:{port}"
            try:
                import aiohttp
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
                    async with session.get(f"{backend_url}/health") as response:
                        if response.status == 200:
                            logger.info(f"✅ Found responsive backend at {backend_url}")
                            # Update our records with the found backend
                            if project_id not in self.processes:
                                self.processes[project_id] = {}
                            self.processes[project_id]['backend_port'] = port
                            return backend_url
            except:
                continue  # Try next port
        
        # No responsive backend found, return default
        default_url = "http://localhost:8001"
        logger.warning(f"⚠️ No responsive backend detected, using default: {default_url}")
        logger.warning(f"💡 Tip: Start the backend first with start_backend action for proper integration")
        return default_url
    
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
        
        # Schedule index.html update via HTTP API call after project creation
        async def update_index_html_via_api():
            try:
                import aiohttp
                
                # First, read the current index.html content via API
                async with aiohttp.ClientSession() as session:
                    # Read current file content
                    async with session.get(f'http://localhost:8000/api/projects/{project_id}/files/frontend/index.html') as response:
                        if response.status == 200:
                            data = await response.json()
                            html_content = data['content']
                        else:
                            logger.error(f"Failed to read index.html via API: {response.status}")
                            return
                    
                    # Inject meta tag with project ID after charset meta tag
                    html_content = html_content.replace(
                        '<meta charset="UTF-8" />',
                        f'<meta charset="UTF-8" />\n    <meta name="project-id" content="{project_id}" />'
                    )
                    
                    # Update console capture script to use API approach
                    html_content = html_content.replace(
                        '''        // Get project ID from URL or generate one
        const getProjectId = () => {
          const urlParams = new URLSearchParams(window.location.search);
          return urlParams.get('project_id') || 
                 document.title.toLowerCase().replace(/[^a-z0-9]/g, '-') || 
                 'frontend-project';
        };''',
                        '''        // Get project ID from meta tag (injected by local-api.py)
        const getProjectId = () => {
          const metaTag = document.querySelector('meta[name="project-id"]');
          return metaTag ? metaTag.content : 'frontend-project';
        };'''
                    )
                    
                    # Replace localStorage with API approach
                    html_content = html_content.replace(
                        '''        // Write logs to local logs.md file
        const writeLogsToFile = async (logs, immediate = false) => {
          try {
            const logText = logs.map(log => 
              `[${log.timestamp}] [${log.level}] ${log.message}`
            ).join('\\n') + '\\n';
            
            // Store in localStorage as a simple approach
            const existingLogs = localStorage.getItem('frontend-console-logs') || '';
            const newLogs = existingLogs + logText;
            localStorage.setItem('frontend-console-logs', newLogs);
            
            // Also expose globally for debugging
            window.__frontendLogsText = newLogs;
            
          } catch (error) {
            // Failsafe: don't create infinite loops
            if (error.message !== 'Failed to write logs to storage') {
              console.warn('Error writing logs to storage:', error);
            }
          }
        };''',
                        '''        // Send logs to backend API
        const sendLogsToBackend = async (logs, immediate = false) => {
          try {
            const response = await fetch('http://localhost:8000/api/frontend-logs', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                project_id: projectId,
                logs: logs,
                immediate: immediate
              })
            });

            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
          } catch (error) {
            // Failsafe: don't create infinite loops
            if (!error.message.includes('Failed to send logs')) {
              console.error('❌ Error sending logs to backend:', error);
            }
          }
        };'''
                    )
                    
                    # Replace all writeLogsToFile calls with sendLogsToBackend
                    replacements = [
                        ('writeLogsToFile([logEntry], true);', 'sendLogsToBackend([logEntry], true);'),
                        ('writeLogsToFile(logsToWrite, false);', 'sendLogsToBackend(logsToSend, false);'),
                        ('writeLogsToFile(logsToWrite, true);', 'sendLogsToBackend(logsToSend, true);'),
                        ('writeLogs: () => writeLogsToFile([...logBuffer], true),', 'sendLogs: () => sendLogsToBackend([...logBuffer], true),'),
                        ('getStoredLogs: () => localStorage.getItem(\'frontend-console-logs\')', 'getAllLogs: () => logBuffer'),
                        ('// Write to logs immediately for critical errors', '// Send logs to backend immediately for critical errors'),
                        ('// Batch write logs every 5 seconds', '// Batch send logs every 5 seconds'),
                        ('// Write logs before page unload', '// Send logs before page unload'),
                        ('const logsToWrite = [...logBuffer];', 'const logsToSend = [...logBuffer];\n            logBuffer.length = 0; // Clear buffer after copying'),
                    ]
                    
                    for old, new in replacements:
                        html_content = html_content.replace(old, new)
                    
                    # Update the file via HTTP API
                    update_payload = {
                        'content': html_content
                    }
                    async with session.put(f'http://localhost:8000/api/projects/{project_id}/files/frontend/index.html', 
                                         json=update_payload) as response:
                        if response.status == 200:
                            logger.info(f"Successfully updated index.html via HTTP API for project {project_id}")
                        else:
                            logger.error(f"Failed to update index.html via HTTP API: {response.status}")
                            
            except Exception as e:
                logger.error(f"Failed to update index.html via HTTP API for project {project_id}: {e}")
        
        # Store the update function to call after metadata is created
        self._pending_index_updates = getattr(self, '_pending_index_updates', [])
        self._pending_index_updates.append((project_id, update_index_html_via_api))
        
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
        
        # Execute pending index.html updates via API
        if hasattr(self, '_pending_index_updates'):
            for proj_id, update_func in self._pending_index_updates:
                if proj_id == project_id:
                    try:
                        await update_func()
                        logger.info(f"Successfully updated index.html via API for project {project_id}")
                    except Exception as e:
                        logger.error(f"Failed to update index.html via API for project {project_id}: {e}")
            # Clear processed updates
            self._pending_index_updates = [(pid, func) for pid, func in self._pending_index_updates if pid != project_id]
        
        # Skip error checking during project creation for speed
        # Error checking will be done when files are updated or when explicitly requested
        logger.info("Skipping error checking during project creation for performance")
        
        return metadata

    def _run_python_error_check(self, project_id: str, file_path: str = None) -> dict:
        """Run Python error checker using the existing python-error-checker.py tool"""
        logger.info(f"Running Python error checker for {project_id}")
        project_path = LOCAL_PROJECTS_PATH / project_id
        backend_path = project_path / "backend"
        python_errors = ""
        python_check_status = {"executed": True, "success": True, "error": None}
        
        try:
            # Check if the python-error-checker.py exists
            error_checker_path = backend_path / "python-error-checker.py"
            
            if not error_checker_path.exists():
                logger.warning(f"python-error-checker.py not found in {backend_path}")
                return {
                    "errors": "⚠️ Python error checker not found - skipping error check",
                    "status": {"executed": False, "success": True, "error": "python-error-checker.py not found"}
                }
            
            # Find virtual environment python
            venv_path = backend_path / "venv"
            venv_python = None
            
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
                if subprocess.run([python_cmd, "--version"], capture_output=True).returncode != 0:
                    python_cmd = "python"
                logger.warning(f"No venv found, using system Python: {python_cmd}")
            else:
                python_cmd = venv_python
                logger.info(f"Using virtual environment Python: {python_cmd}")
            
            # Run the error checker with --once flag
            cmd = [python_cmd, "python-error-checker.py", ".", "--once"]
            
            result = subprocess.run(
                cmd,
                cwd=str(backend_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # No errors found
                python_errors = "✅ No Python errors found"
                python_check_status["success"] = True
            else:
                # Errors found
                error_output = result.stdout.strip() or result.stderr.strip()
                if error_output:
                    python_errors = error_output
                else:
                    python_errors = "Python validation errors detected"
                python_check_status["success"] = False
                
        except subprocess.TimeoutExpired:
            python_check_status["success"] = False
            python_check_status["error"] = "Error checker timeout"
            python_errors = "⚠️ Python error checker timed out after 30 seconds"
            logger.warning(f"Python error checker timed out for {project_id}")
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
    
    def _get_log_file_path(self, project_id: str, service: str) -> Path:
        """Get log file path for a project service"""
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.logs_base_path / f"{project_id}_{service}_{timestamp}.log"
    
    def _start_log_capture_thread(self, project_id: str, service: str, process: subprocess.Popen):
        """Start a thread to capture logs from a process in real-time"""
        import threading
        
        log_file_path = self._get_log_file_path(project_id, service)
        
        def capture_logs():
            try:
                with open(log_file_path, 'w', buffering=1) as log_file:
                    # Write header
                    log_file.write(f"===== {service.upper()} LOG CAPTURE STARTED =====\n")
                    log_file.write(f"Project: {project_id}\n")
                    log_file.write(f"Service: {service}\n")
                    log_file.write(f"Timestamp: {datetime.now()}\n")
                    log_file.write(f"PID: {process.pid}\n")
                    log_file.write("=" * 50 + "\n\n")
                    log_file.flush()
                    
                    # Capture output line by line
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log_file.write(line)
                            log_file.flush()
                        
                        # Check if process is still alive
                        if process.poll() is not None:
                            break
                            
            except Exception as e:
                logger.error(f"Log capture error for {project_id} {service}: {e}")
                
        thread = threading.Thread(target=capture_logs, daemon=True)
        thread.start()
        
        # Store the log file path in process info
        if project_id not in self.processes:
            self.processes[project_id] = {}
        self.processes[project_id][f'{service}_log_file'] = str(log_file_path)
        
        logger.info(f"Started log capture for {project_id} {service}: {log_file_path}")
    
    def get_logs(self, project_id: str, service: str = "backend", include_new_only: bool = True) -> Dict:
        """Get logs for a project service with checkpoint tracking"""
        log_file_path = self._get_log_file_path(project_id, service)
        
        if not log_file_path.exists():
            return {
                "logs": "",
                "total_lines": 0,
                "new_lines": 0,
                "checkpoint_updated": False,
                "log_file_path": str(log_file_path),
                "message": f"No log file found for {project_id} {service}"
            }
        
        try:
            with open(log_file_path, 'r') as f:
                all_lines = f.readlines()
                
            total_lines = len(all_lines)
            
            # Get checkpoint for this project/service
            if project_id not in self.log_checkpoints:
                self.log_checkpoints[project_id] = {}
                
            last_seen = self.log_checkpoints[project_id].get(service, 0)
            
            if include_new_only and last_seen > 0:
                # Only return new lines since last checkpoint
                new_lines = all_lines[last_seen:]
                new_logs = ''.join(new_lines)
                new_line_count = len(new_lines)
            else:
                # Return all logs
                new_logs = ''.join(all_lines)
                new_line_count = total_lines
                
            # Update checkpoint to current position
            self.log_checkpoints[project_id][service] = total_lines
            
            # Add checkpoint marker to the log file
            with open(log_file_path, 'a') as f:
                f.write(f"\n<!-- CHECKPOINT: Model viewed logs up to line {total_lines} at {datetime.now()} -->\n")
                f.flush()
            
            return {
                "logs": new_logs,
                "total_lines": total_lines,
                "new_lines": new_line_count,
                "checkpoint_updated": True,
                "last_checkpoint": last_seen,
                "current_checkpoint": total_lines,
                "log_file_path": str(log_file_path)
            }
            
        except Exception as e:
            logger.error(f"Error reading logs for {project_id} {service}: {e}")
            return {
                "logs": f"Error reading logs: {e}",
                "total_lines": 0,
                "new_lines": 0,
                "checkpoint_updated": False,
                "log_file_path": str(log_file_path),
                "error": str(e)
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
        
        # Check if backend is already running
        if process_info.get('backend_process') and process_info['backend_process'].poll() is None:
            backend_port = process_info.get('backend_port')
            backend_url = f"http://localhost:{backend_port}"
            
            logger.info(f"✅ Backend already running on port {backend_port}")
            return {
                "project_id": project_id,
                "service": "backend",
                "status": "already_running",
                "backend_port": backend_port,
                "backend_url": backend_url,
                "message": f"Backend already running at {backend_url} - use this BACKEND_URL environment variable for your tests. If you see API errors, check your implementation with check_errors instead of restarting."
            }
        
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
            
            # Start Backend Process using virtual environment with cache clearing
            # Use explicit cache clearing and environment settings to prevent module caching issues
            backend_cmd = f"venv/bin/python -u -B -m uvicorn app:app --host 0.0.0.0 --port {backend_port} --reload --reload-dir ."
            backend_process = subprocess.Popen(
                backend_cmd,
                shell=True,
                cwd=str(backend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified logging
                env={**os.environ, "PYTHONPATH": str(backend_path), "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            logger.info(f"Started backend: {backend_cmd} (PID: {backend_process.pid})")
            
            # Start log capture thread
            self._start_log_capture_thread(project_id, "backend", backend_process)
            
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
            backend_url = await self._detect_backend_url(project_id)
            logger.info(f"🔗 Using backend URL for frontend: {backend_url}")
            
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
        """Restart the backend service for a project with cache clearing"""
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
            
            # Clear Python cache files to ensure fresh module loading
            backend_path = LOCAL_PROJECTS_PATH / project_id / "backend"
            if backend_path.exists():
                # Remove __pycache__ directories
                import shutil
                for root, dirs, files in os.walk(backend_path):
                    for dir_name in dirs:
                        if dir_name == "__pycache__":
                            pycache_path = os.path.join(root, dir_name)
                            shutil.rmtree(pycache_path, ignore_errors=True)
                            logger.info(f"Cleared Python cache: {pycache_path}")
        
        # Start backend again with fresh imports
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
                
                # Install dependencies in venv with proper alias handling
                requirements_file = backend_path / "requirements.txt"
                if requirements_file.exists():
                    # Use script that handles Python alias issues properly
                    install_script = """
source venv/bin/activate
unalias python 2>/dev/null || true  # Remove Python alias if it exists
unalias pip 2>/dev/null || true     # Remove pip alias if it exists
pip install -r requirements.txt
"""
                    pip_install = subprocess.run(
                        install_script,
                        shell=True,
                        cwd=str(backend_path),
                        capture_output=True,
                        text=True,
                        timeout=120,
                        executable="/bin/bash"  # Ensure we use bash for source command
                    )
                    if pip_install.returncode != 0:
                        logger.warning(f"Backend pip install issues: {pip_install.stderr}")
                        # Try fallback method using direct venv paths
                        logger.info("Trying fallback installation method...")
                        fallback_install = subprocess.run(
                            "./venv/bin/pip install -r requirements.txt",
                            shell=True,
                            cwd=str(backend_path),
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        if fallback_install.returncode != 0:
                            logger.error(f"Fallback pip install also failed: {fallback_install.stderr}")
                        else:
                            logger.info("✅ Backend dependencies installed (fallback method)")
                    else:
                        logger.info("✅ Backend dependencies installed")
                
                # Specifically install bcrypt if it's in requirements to avoid common issues
                if requirements_file.exists():
                    with open(requirements_file, 'r') as f:
                        requirements_content = f.read()
                    
                    if 'bcrypt' in requirements_content.lower():
                        logger.info("Installing bcrypt with specific handling...")
                        bcrypt_script = """
source venv/bin/activate
unalias python 2>/dev/null || true
unalias pip 2>/dev/null || true
pip install bcrypt
"""
                        bcrypt_install = subprocess.run(
                            bcrypt_script,
                            shell=True,
                            cwd=str(backend_path),
                            capture_output=True,
                            text=True,
                            timeout=60,
                            executable="/bin/bash"
                        )
                        if bcrypt_install.returncode != 0:
                            logger.warning(f"Bcrypt install issues: {bcrypt_install.stderr}")
                            # Try direct path method
                            fallback_bcrypt = subprocess.run(
                                "./venv/bin/pip install bcrypt",
                                shell=True,
                                cwd=str(backend_path),
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            if fallback_bcrypt.returncode == 0:
                                logger.info("✅ Bcrypt installed (fallback method)")
                        else:
                            logger.info("✅ Bcrypt installed successfully")
                
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
        
        # Check for environment variable usage without load_dotenv in Python files
        if file_path.endswith(".py"):
            env_check_result = self._check_env_usage_without_dotenv(content)
            if env_check_result["needs_load_dotenv"]:
                response["dotenv_reminder"] = env_check_result["message"]
        
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

    async def rename_file(self, project_id: str, old_path: str, new_path: str) -> Dict:
        """Rename/move a file within the project"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        old_full_path = project_path / old_path
        new_full_path = project_path / new_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        if not old_full_path.exists():
            raise HTTPException(404, f"File {old_path} not found")
        
        if new_full_path.exists():
            raise HTTPException(409, f"File {new_path} already exists")
        
        # Create directories for new path if needed
        new_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move the file
        shutil.move(str(old_full_path), str(new_full_path))
        
        logger.info(f"Renamed {old_path} to {new_path} in project {project_id}")
        
        return {
            "status": "renamed",
            "old_path": old_path,
            "new_path": new_path
        }
    
    async def delete_file(self, project_id: str, file_path: str) -> Dict:
        """Delete a file from the project"""
        project_path = LOCAL_PROJECTS_PATH / project_id
        full_path = project_path / file_path
        
        if not project_path.exists():
            raise HTTPException(404, f"Project {project_id} not found")
        
        if not full_path.exists():
            raise HTTPException(404, f"File {file_path} not found")
        
        if full_path.is_dir():
            raise HTTPException(400, f"Cannot delete directory {file_path} using file delete endpoint")
        
        # Delete the file
        full_path.unlink()
        
        logger.info(f"Deleted file {file_path} from project {project_id}")
        
        return {
            "project_id": project_id,
            "file_path": file_path,
            "status": "deleted",
            "message": f"File {file_path} deleted successfully"
        }

    def _check_env_usage_without_dotenv(self, content: str) -> Dict:
        """Check if Python file uses environment variables without load_dotenv()"""
        import re
        
        # Check for common environment variable patterns
        env_patterns = [
            r"os\.environ\[",
            r"os\.environ\.get\(",
            r"getenv\(",
            r"BACKEND_URL",
            r"DATABASE_URL",
            r"API_KEY",
            r"SECRET_KEY"
        ]
        
        # Check if load_dotenv is imported and called
        has_dotenv_import = bool(re.search(r"from\s+dotenv\s+import\s+load_dotenv", content) or
                                re.search(r"import\s+dotenv", content))
        has_dotenv_call = bool(re.search(r"load_dotenv\(\)", content) or
                              re.search(r"dotenv\.load_dotenv\(\)", content))
        
        # Check if any environment variable patterns are found
        uses_env_vars = any(re.search(pattern, content) for pattern in env_patterns)
        
        needs_load_dotenv = uses_env_vars and not (has_dotenv_import and has_dotenv_call)
        
        if needs_load_dotenv:
            message = "💡 ENVIRONMENT VARIABLES DETECTED:\n"
            message += "Your Python file appears to use environment variables but doesn't load them.\n"
            message += "To access environment variables like BACKEND_URL:\n\n"
            message += "1. Add at the top of your file:\n"
            message += "   from dotenv import load_dotenv\n"
            message += "   load_dotenv()\n\n"
            message += "2. Then you can use:\n"
            message += "   import os\n"
            message += "   backend_url = os.environ.get('BACKEND_URL')\n\n"
            message += "3. Install python-dotenv if needed:\n"
            message += "   pip install python-dotenv"
            
            return {
                "needs_load_dotenv": True,
                "message": message
            }
        
        return {"needs_load_dotenv": False}

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

class RenameFileRequest(BaseModel):
    new_path: Optional[str] = None
    new_name: Optional[str] = None
    
    @validator('new_name', 'new_path')
    def at_least_one_required(cls, v, values):
        if not v and not values.get('new_path') and not values.get('new_name'):
            raise ValueError("Either new_path or new_name must be provided")
        return v

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

@app.patch("/api/projects/{project_id}/files/{file_path:path}/rename")
async def rename_project_file(project_id: str, file_path: str, request: RenameFileRequest):
    """Rename/move a file within the project"""
    # Handle both new_path and new_name in the request
    # new_name is typically just the filename, new_path is the full path
    if request.new_path:
        new_path = request.new_path
    elif request.new_name:
        # If only new_name is provided, keep the file in the same directory
        import os
        dir_path = os.path.dirname(file_path)
        new_path = os.path.join(dir_path, request.new_name) if dir_path else request.new_name
    else:
        raise HTTPException(400, "Either new_path or new_name must be provided")
    
    result = await project_manager.rename_file(project_id, file_path, new_path)
    return result

@app.delete("/api/projects/{project_id}/files/{file_path:path}")
async def delete_project_file(project_id: str, file_path: str):
    """Delete a file from the project"""
    result = await project_manager.delete_file(project_id, file_path)
    return result

@app.post("/api/projects/{project_id}/execute")
async def execute_command(project_id: str, request: CommandRequest):
    """Execute a command in the project directory with server management restrictions"""
    print(f"🚀 EXECUTE: Starting command execution for project {project_id}")
    print(f"📝 EXECUTE: Command: '{request.command}'")
    print(f"📁 EXECUTE: Working directory: '{request.cwd}'")
    
    try:
        # Validate project exists
        project_path = LOCAL_PROJECTS_PATH / project_id
        print(f"🔍 EXECUTE: Checking if project path exists: {project_path}")
        if not project_path.exists():
            print(f"❌ EXECUTE: Project path does not exist: {project_path}")
            raise HTTPException(404, f"Project {project_id} not found")
        print(f"✅ EXECUTE: Project path exists")
        
        # Check if this project has managed servers running
        print(f"🔍 EXECUTE: Checking project status for server management...")
        project_status = project_manager.get_project_status(project_id)
        is_running = project_status.get("container_status") in ["running", "backend_running", "frontend_running"]
        frontend_port = project_status.get("frontend_port")
        backend_port = project_status.get("backend_port")
        
        print(f"📊 EXECUTE: Project status - is_running: {is_running}")
        print(f"📊 EXECUTE: Frontend port: {frontend_port}")
        print(f"📊 EXECUTE: Backend port: {backend_port}")
        
        # Block server start/stop commands and curl commands
        blocked_patterns = [
            r"uvicorn.*app.*--host.*--port",
            r"python\s+app\.py",  # Only block "python app.py", not test files
            r"npm.*run.*dev",
            r"npm.*start",
            r"yarn.*dev",
            r"yarn.*start",
            r"node.*server",
            r"fastapi.*dev",
            r"flask.*run",
            r"django.*runserver",
            r"curl\s"  # Block curl commands for testing
        ]
        
        import re
        command_lower = request.command.lower()
        print(f"🔍 EXECUTE: Checking command against blocked patterns...")
        print(f"🔍 EXECUTE: Command (lowercase): '{command_lower}'")
        
        for pattern in blocked_patterns:
            if re.search(pattern, command_lower):
                print(f"🚫 EXECUTE: Command matches blocked pattern: {pattern}")
                
                # Special handling for curl commands
                if pattern == r"curl\s":
                    print(f"🚫 EXECUTE: Curl command blocked for testing")
                    return CommandResponse(
                        output="🚫 CURL COMMAND BLOCKED FOR TESTING\n\n" +
                               "❌ curl commands are not allowed for API testing.\n\n" +
                               "✅ PROPER TESTING APPROACH:\n" +
                               "• Create a comprehensive test file (e.g., 'backend/test_api.py')\n" +
                               "• Use Python requests library or httpx for HTTP testing\n" +
                               "• Include proper error handling and response validation\n" +
                               "• Test all endpoints systematically with different scenarios\n" +
                               "• Add assertions to verify expected behavior\n\n" +
                               "💡 EXAMPLE TEST FILE STRUCTURE:\n" +
                               "```python\n" +
                               "import requests\n" +
                               "import os\n\n" +
                               "BASE_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')\n\n" +
                               "def test_get_contacts():\n" +
                               "    response = requests.get(f'{BASE_URL}/contacts/')\n" +
                               "    assert response.status_code == 200\n" +
                               "    return response.json()\n\n" +
                               "if __name__ == '__main__':\n" +
                               "    print('Testing API endpoints...')\n" +
                               "    contacts = test_get_contacts()\n" +
                               "    print(f'Found {len(contacts)} contacts')\n" +
                               "```\n\n" +
                               "🔧 Run your test file with: python backend/test_api.py",
                        error="",
                        exit_code=1
                    )
                
                # Provide helpful guidance instead of executing
                guidance_msg = "🚫 SERVER COMMAND BLOCKED\n\n"
                
                if is_running:
                    print(f"ℹ️ EXECUTE: Servers are running, providing running server guidance")
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
                    print(f"ℹ️ EXECUTE: Servers are not running, providing startup guidance")
                    guidance_msg += f"❌ Your project servers are not running.\n"
                    guidance_msg += f"📋 TO START SERVERS:\n"
                    guidance_msg += f"• Use the 'Start Preview' button or API endpoint\n"
                    guidance_msg += f"• This will properly start both frontend and backend with error checking\n"
                    guidance_msg += f"• Manual server commands are blocked to prevent port conflicts\n"
                
                guidance_msg += f"\n💡 DEBUGGING TIP:\n"
                guidance_msg += f"If the API is not responding, create a simple test file to trigger error checking:\n"
                guidance_msg += f"Example: Create 'backend/debug_test.py' with 'import app' to see any import errors"
                
                print(f"🚫 EXECUTE: Returning blocked command response")
                return CommandResponse(
                    success=False,
                    output=guidance_msg,
                    error="Server command blocked - servers are managed automatically",
                    exit_code=1
                )
        
        print(f"✅ EXECUTE: Command passed server blocking check")
        
        # Block python commands if backend is not running
        python_match = re.search(r'\bpython\d*\b', command_lower)
        print(f"🔍 EXECUTE: Python pattern match: {python_match is not None}, is_running: {is_running}")
        if python_match and not is_running:
            print(f"🚫 EXECUTE: Python command detected but backend is not running")
            guidance_msg = "🚫 PYTHON COMMAND BLOCKED\n\n"
            guidance_msg += f"❌ Backend server is not running yet.\n"
            guidance_msg += f"📋 TO RUN PYTHON COMMANDS:\n"
            guidance_msg += f"• First start the backend server using the 'start_backend' action command\n"
            guidance_msg += f"• This ensures the virtual environment is properly set up\n"
            guidance_msg += f"• Then you can run Python commands with the correct environment\n"
            guidance_msg += f"\n💡 ACCESSING THE BACKEND API:\n"
            guidance_msg += f"• Use the BACKEND_URL environment variable to access the backend API\n"
            guidance_msg += f"• Example: urllib.request.urlopen(os.environ['BACKEND_URL'] + '/api/endpoint')\n"
            guidance_msg += f"• The BACKEND_URL will be automatically set when backend starts\n"
            guidance_msg += f"\n💡 WHY THIS RESTRICTION:\n"
            guidance_msg += f"• Python commands need the virtual environment to work correctly\n"
            guidance_msg += f"• The backend startup process creates and configures the venv\n"
            guidance_msg += f"• Running Python before this setup may cause import errors\n"
            
            print(f"🚫 EXECUTE: Returning blocked Python command response")
            return CommandResponse(
                success=False,
                output=guidance_msg,
                error="Python command blocked - backend server must be running first",
                exit_code=1
            )
        
        print(f"✅ EXECUTE: Command passed Python blocking check")
        
        # Determine target directory
        print(f"🔍 EXECUTE: Determining target directory based on cwd: '{request.cwd}'")
        if request.cwd == "backend":
            work_dir = project_path / "backend"
            print(f"📁 EXECUTE: Using backend directory: {work_dir}")
        elif request.cwd == "frontend":
            work_dir = project_path / "frontend"
            print(f"📁 EXECUTE: Using frontend directory: {work_dir}")
        else:
            # Default to project root
            work_dir = project_path
            print(f"📁 EXECUTE: Using project root directory: {work_dir}")
        
        logger.info(f"Executing command '{request.command}' in {work_dir}")
        print(f"💻 EXECUTE: Running command '{request.command}' in {work_dir}")
        
        # Modify command to use virtual environment if running in backend
        command_to_run = request.command
        if request.cwd == "backend":
            print(f"🔍 EXECUTE: Backend directory detected, checking for virtual environment...")
            # Check if venv exists in backend directory (consistent with start_dev_server)
            venv_activate = work_dir / "venv" / "bin" / "activate"
            print(f"🔍 EXECUTE: Checking for venv activate script: {venv_activate}")
            if venv_activate.exists():
                # Use the same pattern as start_dev_server: source venv and run command
                command_to_run = f"source venv/bin/activate && {request.command}"
                logger.info(f"Using virtual environment: {command_to_run}")
                print(f"🐍 EXECUTE: Using virtual environment: {command_to_run}")
            else:
                print(f"⚠️ EXECUTE: Virtual environment not found, running command without venv")
        else:
            print(f"ℹ️ EXECUTE: Not in backend directory, running command as-is")
        
        print(f"🚀 EXECUTE: About to execute command with 30 second timeout")
        print(f"📝 EXECUTE: Final command: '{command_to_run}'")
        print(f"📁 EXECUTE: Final working directory: {work_dir}")
        
        # Execute command locally with timeout
        result = subprocess.run(
            command_to_run,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for user commands
        )
        
        print(f"✅ EXECUTE: Command execution completed")
        print(f"📊 EXECUTE: Exit code: {result.returncode}")
        print(f"📊 EXECUTE: Stdout length: {len(result.stdout) if result.stdout else 0} characters")
        print(f"📊 EXECUTE: Stderr length: {len(result.stderr) if result.stderr else 0} characters")
        
        # Combine stdout and stderr for full output
        full_output = ""
        if result.stdout:
            print(f"📤 EXECUTE: Adding stdout to output")
            full_output += result.stdout
        if result.stderr:
            print(f"📤 EXECUTE: Adding stderr to output")
            if full_output:
                full_output += "\n"
            full_output += result.stderr
        
        # Print the command output for debugging
        print(f"📊 EXECUTE: Command completed with exit code: {result.returncode}")
        print(f"📄 EXECUTE: Output length: {len(full_output)} characters")
        if full_output:
            print(f"📝 EXECUTE: Command output:\n{'-'*50}")
            print(full_output)
            print(f"{'-'*50}")
        else:
            print("📝 EXECUTE: No output from command")
        
        success = result.returncode == 0
        print(f"📊 EXECUTE: Command success status: {success}")
        
        # Check if this was a Python command and add load_dotenv reminder
        enhanced_output = full_output
        python_match = re.search(r'\bpython\d*\b', command_lower)
        if python_match and success:
            dotenv_reminder = "\n\n💡 ENVIRONMENT VARIABLES REMINDER:\n"
            dotenv_reminder += "If your Python script needs to access environment variables (like BACKEND_URL):\n"
            dotenv_reminder += "1. Add: from dotenv import load_dotenv\n"
            dotenv_reminder += "2. Add: load_dotenv() at the top of your script\n"
            dotenv_reminder += "3. Then use: os.environ.get('BACKEND_URL')\n"
            dotenv_reminder += "4. Install if needed: pip install python-dotenv\n"
            enhanced_output += dotenv_reminder

        response = CommandResponse(
            success=success,
            output=enhanced_output,
            error=result.stderr if result.returncode != 0 else None,
            exit_code=result.returncode
        )
        
        print(f"✅ EXECUTE: Returning response with success={response.success}")
        return response
        
    except subprocess.TimeoutExpired:
        print("⏰ EXECUTE: Command timed out after 30 seconds")
        return CommandResponse(
            success=False,
            output="",
            error="Command timed out after 30 seconds",
            exit_code=-1
        )
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        print(f"❌ EXECUTE: Failed to execute command: {e}")
        print(f"❌ EXECUTE: Exception type: {type(e).__name__}")
        import traceback
        print(f"❌ EXECUTE: Traceback:\n{traceback.format_exc()}")
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

@app.get("/api/projects/{project_id}/error-check")
async def check_project_errors(project_id: str):
    """Run comprehensive error checks for both backend (Python) and frontend (TypeScript) simultaneously"""
    logger.info(f"Running comprehensive error checks for project {project_id}")
    
    # Validate project exists
    project_path = LOCAL_PROJECTS_PATH / project_id
    if not project_path.exists():
        raise HTTPException(404, f"Project {project_id} not found")
    
    backend_path = project_path / "backend"
    frontend_path = project_path / "frontend"
    
    # Initialize results structure
    results = {
        "project_id": project_id,
        "timestamp": datetime.now().isoformat(),
        "backend": {
            "exists": backend_path.exists(),
            "errors": "",
            "status": {"executed": False, "success": False, "error": None},
            "error_count": 0
        },
        "frontend": {
            "exists": frontend_path.exists(),
            "errors": "",
            "status": {"executed": False, "success": False, "error": None},
            "error_count": 0
        },
        "summary": {
            "total_errors": 0,
            "backend_has_errors": False,
            "frontend_has_errors": False,
            "overall_status": "unknown"
        }
    }
    
    # Run both error checks simultaneously using asyncio
    async def run_python_check():
        """Async wrapper for Python error check"""
        if backend_path.exists():
            try:
                # Run the existing Python error check method
                python_result = project_manager._run_python_error_check(project_id)
                results["backend"]["errors"] = python_result.get("python_errors", "")
                results["backend"]["status"] = python_result.get("python_check_status", {
                    "executed": False, "success": False, "error": "No status returned"
                })
                
                # Count errors
                error_text = results["backend"]["errors"]
                if error_text and error_text.strip():
                    # Count error lines (rough estimate)
                    error_lines = [line for line in error_text.split('\n') if 'error:' in line.lower() or 'traceback' in line.lower()]
                    results["backend"]["error_count"] = len(error_lines) if error_lines else 1
                
                logger.info(f"Python error check completed for {project_id}: {results['backend']['error_count']} errors")
            except Exception as e:
                results["backend"]["status"] = {"executed": False, "success": False, "error": str(e)}
                results["backend"]["errors"] = f"Failed to run Python error check: {str(e)}"
                results["backend"]["error_count"] = 1
                logger.error(f"Python error check failed for {project_id}: {e}")
    
    async def run_typescript_check():
        """Async wrapper for TypeScript error check"""
        if frontend_path.exists():
            try:
                # Run the existing TypeScript error check method
                ts_result = project_manager._run_typescript_error_check(project_id)
                results["frontend"]["errors"] = ts_result.get("ts_errors", "")
                results["frontend"]["status"] = ts_result.get("ts_check_status", {
                    "executed": False, "success": False, "error": "No status returned"
                })
                
                # Count errors
                error_text = results["frontend"]["errors"]
                if error_text and error_text.strip():
                    # Count TypeScript errors more accurately
                    error_lines = [line for line in error_text.split('\n') if 'error TS' in line or 'Error:' in line]
                    results["frontend"]["error_count"] = len(error_lines) if error_lines else 1
                
                logger.info(f"TypeScript error check completed for {project_id}: {results['frontend']['error_count']} errors")
            except Exception as e:
                results["frontend"]["status"] = {"executed": False, "success": False, "error": str(e)}
                results["frontend"]["errors"] = f"Failed to run TypeScript error check: {str(e)}"
                results["frontend"]["error_count"] = 1
                logger.error(f"TypeScript error check failed for {project_id}: {e}")
    
    # Run both checks concurrently
    try:
        await asyncio.gather(run_python_check(), run_typescript_check())
        
        # Calculate summary
        results["summary"]["backend_has_errors"] = (
            results["backend"]["error_count"] > 0 or 
            not results["backend"]["status"].get("success", False)
        )
        results["summary"]["frontend_has_errors"] = (
            results["frontend"]["error_count"] > 0 or 
            not results["frontend"]["status"].get("success", False)
        )
        results["summary"]["total_errors"] = results["backend"]["error_count"] + results["frontend"]["error_count"]
        
        # Determine overall status
        if results["summary"]["total_errors"] == 0 and results["backend"]["status"].get("success", True) and results["frontend"]["status"].get("success", True):
            results["summary"]["overall_status"] = "clean"
        elif results["summary"]["backend_has_errors"] and results["summary"]["frontend_has_errors"]:
            results["summary"]["overall_status"] = "both_have_errors"
        elif results["summary"]["backend_has_errors"]:
            results["summary"]["overall_status"] = "backend_has_errors"
        elif results["summary"]["frontend_has_errors"]:
            results["summary"]["overall_status"] = "frontend_has_errors"
        else:
            results["summary"]["overall_status"] = "unknown"
        
        logger.info(f"Error check completed for {project_id}: {results['summary']['overall_status']} ({results['summary']['total_errors']} total errors)")
        
    except Exception as e:
        logger.error(f"Error during comprehensive error check for {project_id}: {e}")
        results["summary"]["overall_status"] = "check_failed"
        results["summary"]["error"] = str(e)
    
    return results

@app.post("/api/projects/{project_id}/ast-analyze")
async def analyze_project_ast(project_id: str, target: str = "backend", focus: str = "all"):
    """Run AST structural analysis on project code"""
    logger.info(f"Running AST analysis for project {project_id}, target: {target}, focus: {focus}")
    
    # Validate project exists
    project_path = LOCAL_PROJECTS_PATH / project_id
    if not project_path.exists():
        raise HTTPException(404, f"Project {project_id} not found")
    
    # Validate target parameter
    if target not in ["backend", "frontend"]:
        raise HTTPException(400, f"Invalid target '{target}'. Must be 'backend' or 'frontend'")
    
    # Validate focus parameter
    valid_focus = ["routes", "imports", "env", "database", "structure", "all"]
    if focus not in valid_focus:
        raise HTTPException(400, f"Invalid focus '{focus}'. Must be one of: {', '.join(valid_focus)}")
    
    target_path = project_path / target
    if not target_path.exists():
        raise HTTPException(404, f"{target.capitalize()} directory not found in project {project_id}")
    
    try:
        # Copy AST analyzer to target directory if it doesn't exist
        analyzer_path = target_path / "ast-analyzer.py"
        boilerplate_analyzer = LOCAL_BACKEND_BOILERPLATE_PATH / "ast-analyzer.py"
        
        if not analyzer_path.exists() and boilerplate_analyzer.exists():
            import shutil
            shutil.copy(boilerplate_analyzer, analyzer_path)
            logger.info(f"Copied AST analyzer to {analyzer_path}")
        
        # Run AST analysis
        cmd = ["python3", "ast-analyzer.py", ".", target, focus]
        logger.info(f"Running AST analysis command: {' '.join(cmd)} in {target_path}")
        
        result = subprocess.run(
            cmd,
            cwd=str(target_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse the JSON output from stdout
            try:
                output_lines = result.stdout.strip().split('\n')
                json_start = -1
                for i, line in enumerate(output_lines):
                    if line.startswith('{'):
                        json_start = i
                        break
                
                if json_start >= 0:
                    json_output = '\n'.join(output_lines[json_start:])
                    analysis_result = json.loads(json_output)
                    
                    logger.info(f"AST analysis completed for {project_id}: {analysis_result.get('summary', {}).get('files_analyzed', 0)} files analyzed")
                    
                    # Add metadata
                    analysis_result["project_id"] = project_id
                    analysis_result["timestamp"] = datetime.now().isoformat()
                    analysis_result["success"] = True
                    
                    return analysis_result
                else:
                    logger.warning(f"AST analyzer did not return valid JSON output for {project_id}")
                    return {
                        "project_id": project_id,
                        "timestamp": datetime.now().isoformat(),
                        "success": False,
                        "error": "AST analyzer did not return valid JSON",
                        "raw_output": result.stdout
                    }
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AST analyzer JSON output for {project_id}: {e}")
                return {
                    "project_id": project_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": f"JSON parsing error: {e}",
                    "raw_output": result.stdout
                }
        else:
            logger.error(f"AST analyzer failed for {project_id} with exit code {result.returncode}")
            return {
                "project_id": project_id,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": f"AST analyzer failed with exit code {result.returncode}",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"AST analysis timed out for {project_id}")
        return {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": "AST analysis timed out after 30 seconds"
        }
    except Exception as e:
        logger.error(f"Error during AST analysis for {project_id}: {e}")
        return {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": f"AST analysis error: {str(e)}"
        }

@app.get("/api/projects/{project_id}/check-logs")
async def check_project_logs(
    project_id: str, 
    service: str = "backend", 
    include_new_only: bool = True
):
    """Get logs for a project service with checkpoint tracking"""
    logger.info(f"Checking logs for project {project_id}, service: {service}, new_only: {include_new_only}")
    
    # Validate project exists (special handling for frontend console logs)
    project_path = LOCAL_PROJECTS_PATH / project_id
    if not project_path.exists():
        # For frontend service, allow generic "frontend-console" project
        if service == "frontend" and project_id in ["frontend-console", "current-frontend"]:
            # Use "frontend-console" as fallback for frontend logs
            actual_project_id = "frontend-console"
        else:
            raise HTTPException(404, f"Project {project_id} not found")
    else:
        actual_project_id = project_id
    
    # Validate service parameter
    if service not in ["backend", "frontend"]:
        raise HTTPException(400, f"Invalid service '{service}'. Must be 'backend' or 'frontend'")
    
    try:
        # Get logs from project manager
        log_result = project_manager.get_logs(actual_project_id, service, include_new_only)
        
        # Add metadata
        log_result.update({
            "project_id": project_id,
            "service": service,
            "timestamp": datetime.now().isoformat(),
            "include_new_only": include_new_only
        })
        
        # Check if service is running
        if project_id in project_manager.processes:
            process_info = project_manager.processes[project_id]
            service_process = process_info.get(f'{service}_process')
            log_result['service_running'] = service_process is not None and service_process.poll() is None
            
            if service == "backend":
                log_result['backend_port'] = process_info.get('backend_port')
                log_result['backend_url'] = f"http://localhost:{process_info.get('backend_port')}" if process_info.get('backend_port') else None
            elif service == "frontend":
                log_result['frontend_port'] = process_info.get('frontend_port')
                log_result['frontend_url'] = f"http://localhost:{process_info.get('frontend_port')}" if process_info.get('frontend_port') else None
        else:
            log_result['service_running'] = False
        
        logger.info(f"Retrieved {log_result['new_lines']} new lines from {log_result['total_lines']} total for {project_id} {service}")
        return log_result
        
    except Exception as e:
        logger.error(f"Error checking logs for {project_id} {service}: {e}")
        raise HTTPException(500, f"Failed to check logs: {str(e)}")

class FrontendLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    url: str
    userAgent: Optional[str] = None

class FrontendLogBatch(BaseModel):
    project_id: str
    logs: List[FrontendLogEntry]
    immediate: bool = False

@app.post("/api/frontend-logs")
async def receive_frontend_logs(request: Request):
    """Receive frontend console logs and store them"""
    try:
        # Parse the request body
        body = await request.json()
        
        # Handle both batch and single log formats
        if "logs" in body:
            # Batch format from our console capture script
            log_batch = FrontendLogBatch(**body)
            project_id = log_batch.project_id
            log_entries = log_batch.logs
        else:
            # Single log format (backward compatibility)
            log_entry = FrontendLogEntry(**body)
            project_id = "frontend-console"
            log_entries = [log_entry]
            
            # Try to find active frontend project for single format
            for pid, process_info in project_manager.processes.items():
                if process_info.get('frontend_process') and process_info['frontend_process'].poll() is None:
                    frontend_port = process_info.get('frontend_port')
                    if frontend_port and f"localhost:{frontend_port}" in log_entry.url:
                        project_id = pid
                        break
        
        # Get log file path (create logs directory if needed)
        logs_dir = Path("/Users/shanjairaj/local-projects/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime("%Y%m%d")
        log_file_path = logs_dir / f"{project_id}_frontend_{today}.log"
        
        # Initialize log file if it's new
        if not log_file_path.exists():
            with open(log_file_path, 'w') as f:
                f.write(f"===== FRONTEND CONSOLE LOG CAPTURE STARTED =====\n")
                f.write(f"Project: {project_id}\n")
                f.write(f"Service: frontend\n") 
                f.write(f"URL: {log_entries[0].url if log_entries else 'N/A'}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write("==================================================\n\n")
        
        # Write all log entries to file
        logs_written = 0
        with open(log_file_path, 'a', buffering=1) as f:
            for log_entry in log_entries:
                # Format log entry with better formatting
                formatted_log = f"[{log_entry.timestamp}] [{log_entry.level.upper()}] {log_entry.message}"
                if hasattr(log_entry, 'stack') and log_entry.stack:
                    formatted_log += f"\nStack: {log_entry.stack}"
                f.write(formatted_log + '\n')
                logs_written += 1
        
        return {
            "status": "success", 
            "logged": True,
            "project_id": project_id,
            "logs_written": logs_written,
            "log_file": str(log_file_path)
        }
        
    except Exception as e:
        logger.error(f"Error receiving frontend log: {e}")
        raise HTTPException(500, f"Failed to log frontend entry: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Local Projects API on port {port}")
    uvicorn.run("local-api:app", host="0.0.0.0", port=port, reload=True)