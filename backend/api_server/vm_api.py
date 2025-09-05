"""
Machine VM API integration for direct file operations and terminal commands.
Handles synchronization with the development environment VM.
"""

import os
import json
import aiohttp
import asyncio
from typing import Dict, Optional, Any


class MachineVMAPI:
    """Machine VM API client for development environment operations"""
    
    def __init__(self):
        """Initialize VM API configuration"""
        self.base_url = os.getenv('VM_API_BASE_URL', 'http://llm-agent-api.eastus.cloudapp.azure.com:8000')
        self.timeout = 30  # seconds for file operations
        self.command_timeout = 120  # seconds for terminal commands
    
    async def sync_project(self, project_id: str, force_refresh: bool = False) -> bool:
        """Sync entire project from Azure storage to VM cache"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "force_refresh": force_refresh
                }
                
                async with session.post(f"{self.base_url}/sync", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ VM Project Sync: {result.get('status', 'unknown')} - {result.get('total_files', 0)} files")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ VM Project Sync failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            print(f"⚠️ VM Project Sync error: {str(e)}")
            return False
    
    async def create_file(self, project_id: str, file_path: str, content: str, working_dir: str = None, overwrite: bool = True) -> dict:
        """Create file on VM using dedicated /file/create endpoint"""
        try:
            # Parse working_dir and file_path
            working_dir, relative_path = self._parse_file_path(file_path, working_dir)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "file_path": relative_path,
                    "content": content,
                    "working_dir": working_dir,
                    "overwrite": overwrite
                }
                
                print(f"📝 Creating file on VM: {file_path}")
                
                async with session.post(f"{self.base_url}/file/create", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success", False):
                            print(f"✅ VM File created: {file_path}")
                        else:
                            print(f"❌ VM File create failed: {result.get('error', 'Unknown error')}")
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ VM File create request failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "working_directory": "",
                            "file_path": relative_path
                        }
                        
        except Exception as e:
            print(f"⚠️ VM File create error for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "working_directory": "",
                "file_path": file_path
            }
    
    async def update_file(self, project_id: str, file_path: str, content: str, working_dir: str = None, create_if_missing: bool = True) -> dict:
        """Update file on VM using dedicated /file/update endpoint"""
        try:
            # Parse working_dir and file_path
            working_dir, relative_path = self._parse_file_path(file_path, working_dir)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "file_path": relative_path,
                    "content": content,
                    "working_dir": working_dir,
                    "create_if_missing": create_if_missing
                }
                
                print(f"📝 Updating file on VM: {file_path}")
                
                async with session.post(f"{self.base_url}/file/update", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success", False):
                            print(f"✅ VM File updated: {file_path}")
                        else:
                            print(f"❌ VM File update failed: {result.get('error', 'Unknown error')}")
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ VM File update request failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "working_directory": "",
                            "file_path": relative_path
                        }
                        
        except Exception as e:
            print(f"⚠️ VM File update error for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "working_directory": "",
                "file_path": file_path
            }
    
    async def delete_file(self, project_id: str, file_path: str, working_dir: str = None) -> dict:
        """Delete file on VM using dedicated /file/delete endpoint"""
        try:
            # Parse working_dir and file_path
            working_dir, relative_path = self._parse_file_path(file_path, working_dir)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "file_path": relative_path,
                    "working_dir": working_dir
                }
                
                print(f"🗑️ Deleting file on VM: {file_path}")
                
                async with session.post(f"{self.base_url}/file/delete", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success", False):
                            print(f"✅ VM File deleted: {file_path}")
                        else:
                            print(f"❌ VM File delete failed: {result.get('error', 'Unknown error')}")
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ VM File delete request failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "working_directory": "",
                            "file_path": relative_path,
                            "deleted": False
                        }
                        
        except Exception as e:
            print(f"⚠️ VM File delete error for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "working_directory": "",
                "file_path": file_path,
                "deleted": False
            }
    
    async def read_file(self, project_id: str, file_path: str, working_dir: str = None) -> dict:
        """Read file from VM using /file/read endpoint"""
        try:
            # Parse working_dir and file_path
            working_dir, relative_path = self._parse_file_path(file_path, working_dir)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "file_path": relative_path,
                    "working_dir": working_dir
                }
                
                print(f"📖 Reading file from VM: {file_path}")
                
                async with session.post(f"{self.base_url}/file/read", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("exists", False):
                            print(f"✅ Read from VM: {file_path} ({result.get('size', 0)} bytes)")
                        else:
                            print(f"📄 File not found on VM: {file_path}")
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ VM File read failed: {response.status} - {error_text}")
                        return {
                            "content": "",
                            "error": f"HTTP {response.status}: {error_text}",
                            "exists": False,
                            "working_directory": "",
                            "file_path": relative_path
                        }
                        
        except Exception as e:
            print(f"⚠️ VM File read error for {file_path}: {str(e)}")
            return {
                "content": "",
                "error": f"Request error: {str(e)}",
                "exists": False,
                "working_directory": "",
                "file_path": file_path
            }
    
    async def execute_command(self, project_id: str, command: str, working_dir: str = None) -> Dict[str, Any]:
        """Execute terminal command on VM"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.command_timeout)) as session:
                payload = {
                    "project_id": project_id,
                    "command": command,
                    "working_dir": working_dir
                }
                
                print(f"💻 Executing on VM: {command} (in {working_dir or 'root'})")
                
                async with session.post(f"{self.base_url}/execute", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ VM Command completed: {command}")
                        return {
                            "success": True,
                            "stdout": result.get("stdout", ""),
                            "stderr": result.get("stderr", ""),
                            "return_code": result.get("return_code", 0),
                            "working_directory": result.get("working_directory", "")
                        }
                    else:
                        error_text = await response.text()
                        print(f"❌ VM Command failed: {response.status} - {error_text}")
                        return {
                            "stdout": "",
                            "stderr": f"HTTP {response.status}: {error_text}",
                            "return_code": response.status if response.status != 200 else 1,
                            "working_directory": ""
                        }
                        
        except Exception as e:
            print(f"⚠️ VM Command error: {str(e)}")
            return {
                "stdout": "",
                "stderr": f"Request error: {str(e)}",
                "return_code": 1,
                "working_directory": ""
            }
    
    
    def _parse_file_path(self, file_path: str, working_dir: str = None) -> tuple[str, str]:
        """Parse file path to determine working_dir and relative path"""
        if working_dir is not None:
            return working_dir, file_path
        
        # Auto-detect working_dir from file path
        if file_path.startswith('frontend/'):
            return 'frontend', file_path[9:]  # Remove 'frontend/' prefix
        elif file_path.startswith('backend/'):
            return 'backend', file_path[8:]   # Remove 'backend/' prefix
        else:
            return None, file_path  # Root directory


# Global instance for use across the application
vm_api = MachineVMAPI()