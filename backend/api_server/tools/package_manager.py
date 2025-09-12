"""
Package manager utility for handling npm and pip install commands.
Automatically extracts packages and adds them to requirements.txt or package.json.
"""

import re
import json
import asyncio
from typing import List, Tuple, Optional, Dict
from pathlib import Path


class PackageManager:
    """Handles package extraction and dependency file updates"""
    
    def __init__(self, cloud_storage=None, project_id: str = None):
        """
        Initialize package manager.
        
        Args:
            cloud_storage: AzureBlobStorage instance for file operations
            project_id: Current project ID
        """
        self.cloud_storage = cloud_storage
        self.project_id = project_id
    
    def extract_packages_from_command(self, command: str) -> Optional[Dict]:
        """
        Extract package names with versions from pip install or npm install commands.
        
        Args:
            command: The install command string
            
        Returns:
            Dict with package_type and packages list, or None if not an install command
        """
        if not command:
            return None
            
        # Check for pip install command (including compound commands)
        pip_match = re.search(r'pip(?:3)?\s+install\s+(.+?)(?:\s*&&|\s*;|$)', command)
        if pip_match:
            packages_str = pip_match.group(1)
            packages = self._extract_pip_packages(packages_str)
            if packages:
                return {
                    'type': 'pip',
                    'packages': packages
                }
        
        # Check for npm install command (including compound commands)
        npm_match = re.search(r'npm\s+install\s+(.+?)(?:\s*&&|\s*;|$)', command)
        if npm_match:
            packages_str = npm_match.group(1)
            packages = self._extract_npm_packages(packages_str)
            if packages:
                return {
                    'type': 'npm',
                    'packages': packages
                }
        
        return None
    
    def _extract_pip_packages(self, packages_str: str) -> List[Tuple[str, Optional[str]]]:
        """
        Extract pip packages with their version specifiers.
        
        Returns:
            List of tuples (package_name, version_specifier)
        """
        packages = []
        
        for part in packages_str.split():
            # Skip flags (start with -)
            if part.startswith('-'):
                continue
            
            # Match package with version specifier
            version_match = re.match(r'^([a-zA-Z0-9\-_\.]+)((?:[<>=!]+)[\d\.]+(?:\.\*)?)?$', part)
            if version_match:
                package_name = version_match.group(1)
                version_spec = version_match.group(2) if version_match.group(2) else None
                packages.append((package_name, version_spec))
            elif not part.startswith('-'):
                # Package without version
                packages.append((part, None))
        
        return packages
    
    def _extract_npm_packages(self, packages_str: str) -> List[Tuple[str, Optional[str]]]:
        """
        Extract npm packages with their version specifiers.
        
        Returns:
            List of tuples (package_name, version)
        """
        packages = []
        
        for part in packages_str.split():
            # Skip flags (start with -) but keep scoped packages (@org/package)
            if part.startswith('-') and not part.startswith('-@'):
                continue
            
            # Handle scoped packages with version (@org/package@version)
            if part.startswith('@'):
                # Check if it has a version after the second @
                at_count = part.count('@')
                if at_count > 1:
                    # @org/package@version format
                    last_at_index = part.rfind('@')
                    package_name = part[:last_at_index]
                    version = part[last_at_index+1:]
                    packages.append((package_name, version))
                else:
                    # @org/package format (no version)
                    packages.append((part, None))
            elif '@' in part:
                # Regular package with version (package@version)
                package_name, version = part.split('@', 1)
                packages.append((package_name, version))
            else:
                # Regular package without version
                packages.append((part, None))
        
        return packages
    
    async def update_dependency_files(self, command: str, working_dir: Optional[str] = None) -> Optional[str]:
        """
        Update requirements.txt or package.json based on install command.
        
        Args:
            command: The install command
            working_dir: Working directory (frontend, backend, or None for root)
            
        Returns:
            Success message or None if no updates needed
        """
        package_info = self.extract_packages_from_command(command)
        if not package_info:
            return None
        
        if not self.cloud_storage or not self.project_id:
            print("⚠️ Package manager: No cloud storage or project ID configured")
            return None
        
        if package_info['type'] == 'pip':
            return await self._update_requirements_txt(package_info['packages'], working_dir)
        elif package_info['type'] == 'npm':
            return await self._update_package_json(package_info['packages'], working_dir)
        
        return None
    
    async def _update_requirements_txt(self, packages: List[Tuple[str, Optional[str]]], working_dir: Optional[str]) -> Optional[str]:
        """
        Update requirements.txt with new packages.
        
        Args:
            packages: List of (package_name, version_specifier) tuples
            working_dir: Working directory
            
        Returns:
            Success message or None
        """
        # PIP packages ALWAYS go to backend/requirements.txt
        req_file_path = 'backend/requirements.txt'
        
        try:
            # Download existing requirements.txt
            existing_content = self.cloud_storage.download_file(self.project_id, req_file_path)
            if existing_content is None:
                existing_content = ""
            
            # Parse existing requirements
            existing_packages = {}
            for line in existing_content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse package name from line
                    match = re.match(r'^([a-zA-Z0-9\-_\.]+)', line)
                    if match:
                        pkg_name = match.group(1)
                        existing_packages[pkg_name.lower()] = line
            
            # Add new packages
            added_packages = []
            for package_name, version_spec in packages:
                pkg_key = package_name.lower()
                if pkg_key not in existing_packages:
                    # Add new package
                    if version_spec:
                        new_line = f"{package_name}{version_spec}"
                    else:
                        new_line = package_name
                    existing_packages[pkg_key] = new_line
                    added_packages.append(new_line)
                    print(f"📦 Adding to requirements.txt: {new_line}")
            
            if added_packages:
                # Rebuild requirements.txt content
                new_content = '\n'.join(sorted(existing_packages.values())) + '\n'
                
                # Upload updated file
                success = self.cloud_storage.upload_file(
                    self.project_id,
                    req_file_path,
                    new_content,
                    is_new_file=(existing_content == "")
                )
                
                if success:
                    return f"Added {len(added_packages)} package(s) to {req_file_path}: {', '.join(added_packages)}"
                else:
                    print(f"❌ Failed to update {req_file_path}")
            else:
                print(f"ℹ️ All packages already in {req_file_path}")
            
        except Exception as e:
            print(f"❌ Error updating requirements.txt: {e}")
        
        return None
    
    async def _update_package_json(self, packages: List[Tuple[str, Optional[str]]], working_dir: Optional[str]) -> Optional[str]:
        """
        Update package.json with new packages.
        
        Args:
            packages: List of (package_name, version) tuples
            working_dir: Working directory
            
        Returns:
            Success message or None
        """
        # NPM packages ALWAYS go to frontend/package.json
        pkg_file_path = 'frontend/package.json'
        
        try:
            # Download existing package.json
            existing_content = self.cloud_storage.download_file(self.project_id, pkg_file_path)
            if existing_content is None:
                # Create minimal package.json if it doesn't exist
                package_json = {
                    "name": "project",
                    "version": "1.0.0",
                    "dependencies": {}
                }
            else:
                package_json = json.loads(existing_content)
            
            # Ensure dependencies section exists
            if 'dependencies' not in package_json:
                package_json['dependencies'] = {}
            
            # Add new packages
            added_packages = []
            for package_name, version in packages:
                if package_name not in package_json['dependencies']:
                    # Add new package with version or use "*" for latest
                    if version:
                        package_json['dependencies'][package_name] = version
                    else:
                        # Use "*" which means any version (npm will install latest)
                        # Alternatively could use "^" prefix when running npm install
                        package_json['dependencies'][package_name] = "*"
                    added_packages.append(f"{package_name}@{version or '*'}")
                    print(f"📦 Adding to package.json: {package_name}@{version or '*'}")
            
            if added_packages:
                # Upload updated file
                new_content = json.dumps(package_json, indent=2)
                success = self.cloud_storage.upload_file(
                    self.project_id,
                    pkg_file_path,
                    new_content,
                    is_new_file=(existing_content is None)
                )
                
                if success:
                    return f"Added {len(added_packages)} package(s) to {pkg_file_path}: {', '.join(added_packages)}"
                else:
                    print(f"❌ Failed to update {pkg_file_path}")
            else:
                print(f"ℹ️ All packages already in {pkg_file_path}")
            
        except Exception as e:
            print(f"❌ Error updating package.json: {e}")
        
        return None