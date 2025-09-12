"""
Vercel deployment service using REST API
Deploys frontend React/Vite apps to Vercel with zero configuration
"""

import os
import tempfile
import shutil
import subprocess
import requests
import json
import tarfile
import hashlib
from typing import Dict, Optional, List
from pathlib import Path
import time
import base64

from cloud_storage import AzureBlobStorage

class VercelDeployer:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.vercel.com"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
    def create_deployment(self, files: Dict[str, str], name: str, project_name: str = None) -> dict:
        """
        Create a new deployment on Vercel using the correct API workflow
        
        Args:
            files: Dict of file paths to file contents
            name: Deployment name
            project_name: Optional project name
            
        Returns:
            Deployment response
        """
        
        # Step 1: Upload all files first and get their SHA hashes
        uploaded_files = {}
        upload_errors = []
        
        for file_path, content in files.items():
            clean_path = file_path.lstrip('/')
            
            # Calculate SHA1 digest
            content_bytes = content.encode('utf-8')
            file_hash = hashlib.sha1(content_bytes).hexdigest()
            
            # Upload file to Vercel with proper digest header
            upload_response = requests.post(
                f"{self.base_url}/v2/files",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/octet-stream",
                    "x-vercel-digest": file_hash
                },
                data=content_bytes
            )
            
            if upload_response.status_code in [200, 201]:
                file_data = upload_response.json()
                uploaded_files[clean_path] = {
                    "file": clean_path,
                    "size": len(content.encode('utf-8'))
                }
            else:
                upload_errors.append(f"Failed to upload {clean_path}: Status {upload_response.status_code} - {upload_response.text}")
                print(f"DEBUG: Upload failed for {clean_path}: {upload_response.status_code} - {upload_response.text}")
        
        if upload_errors:
            return {
                "status": "error",
                "message": "File upload failed",
                "errors": upload_errors
            }
        
        # Step 2: Create deployment with uploaded file references
        file_objects = list(uploaded_files.values())
        
        payload = {
            "name": name,
            "files": file_objects,
            "projectSettings": {
                "framework": "vite",
                "buildCommand": "npm run build",
                "outputDirectory": "dist",
                "installCommand": "npm install"
            },
            "target": "production"
        }
        
        if project_name:
            payload["project"] = project_name
            
        response = requests.post(
            f"{self.base_url}/v13/deployments",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            return {
                "status": "error",
                "message": f"Failed to create deployment: {response.text}",
                "status_code": response.status_code
            }
            
        deployment_data = response.json()
        deployment_id = deployment_data.get("id")
        
        if not deployment_id:
            return {
                "status": "error", 
                "message": "No deployment ID returned"
            }
        
        # Step 3: Wait for deployment to complete
        deployment_url = None
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(3)
            
            status_response = requests.get(
                f"{self.base_url}/v13/deployments/{deployment_id}",
                headers=self.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                state = status_data.get("readyState", "")
                
                if state == "READY":
                    deployment_url = status_data.get("url")
                    if deployment_url and not deployment_url.startswith("http"):
                        deployment_url = f"https://{deployment_url}"
                    break
                elif state == "ERROR":
                    return {
                        "status": "error",
                        "message": "Deployment failed during build",
                        "deployment_id": deployment_id
                    }
                    
            attempt += 1
        
        if not deployment_url:
            return {
                "status": "error", 
                "message": "Deployment timed out",
                "deployment_id": deployment_id
            }
            
        return {
            "status": "success",
            "deployment_url": deployment_url,
            "deployment_id": deployment_id,
            "project_name": project_name or name
        }

def parse_env_file(content: str) -> Dict[str, str]:
    """Parse .env file content and return environment variables"""
    env_vars = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            value = value.strip().strip('"').strip("'")
            env_vars[key.strip()] = value
    return env_vars

def deploy_frontend_to_vercel(project_id: str, project_name: str = None, environment: str = "production", custom_env_vars: Dict[str, str] = None) -> dict:
    """
    Deploy frontend to Vercel
    
    Args:
        project_id: Azure storage project ID
        project_name: Vercel project name (auto-generated if None)
        environment: Deployment environment (production/staging)
        custom_env_vars: Additional environment variables
        
    Returns:
        dict: Deployment result with status, URLs, and logs
    """
    
    # Get Vercel API token
    vercel_token = os.getenv('VERCEL_TOKEN')
    
    if not vercel_token:
        return {
            "status": "error",
            "error_type": "missing_credentials",
            "message": "Vercel API token not configured",
            "suggestions": [
                "Set VERCEL_TOKEN environment variable",
                "Get token from https://vercel.com/account/tokens"
            ]
        }
    
    # Generate project name if not provided
    if not project_name:
        project_name = f"app-{project_id.replace('_', '-').lower()}"
    
    deployment_logs = []
    storage = AzureBlobStorage()
    deployer = VercelDeployer(vercel_token)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            frontend_dir = os.path.join(temp_dir, "frontend")
            os.makedirs(frontend_dir, exist_ok=True)
            
            # Download all frontend files from Azure
            deployment_logs.append(f"📂 Downloading frontend files for project {project_id}")
            frontend_files = storage.list_files(project_id, "frontend/")
            
            if not frontend_files:
                return {
                    "status": "error",
                    "error_type": "no_frontend_files", 
                    "message": f"No frontend files found for project {project_id}",
                    "logs": deployment_logs
                }
            
            downloaded_count = 0
            env_vars_from_project = {}
            files_for_vercel = {}
            
            for file_path in frontend_files:
                content = storage.download_file(project_id, file_path)
                if content is not None:
                    local_path = file_path[9:]  # Remove 'frontend/' prefix
                    
                    # Store file for Vercel deployment
                    files_for_vercel[local_path] = content
                    
                    # Extract environment variables from .env file
                    if local_path == '.env':
                        env_vars_from_project = parse_env_file(content)
                        deployment_logs.append(f"📄 Found .env file with {len(env_vars_from_project)} variables")
                    
                    downloaded_count += 1
            
            deployment_logs.append(f"✅ Downloaded {downloaded_count} frontend files")
            
            # Add vercel.json for SPA configuration
            vercel_config = {
                "rewrites": [
                    {"source": "/(.*)", "destination": "/index.html"}
                ]
            }
            files_for_vercel["vercel.json"] = json.dumps(vercel_config, indent=2)
            deployment_logs.append("📝 Added vercel.json for SPA routing")
            
            # Merge environment variables
            final_env_vars = {**env_vars_from_project}
            if custom_env_vars:
                final_env_vars.update(custom_env_vars)
                deployment_logs.append(f"🔧 Merged {len(custom_env_vars)} custom environment variables")
            
            # Deploy to Vercel
            deployment_logs.append(f"🚀 Deploying to Vercel: {project_name}")
            
            result = deployer.create_deployment(
                files=files_for_vercel,
                name=project_name,
                project_name=project_name
            )
            
            if result["status"] == "success":
                deployment_logs.append("✅ Deployment successful!")
                return {
                    "status": "success",
                    "deployment_url": result["deployment_url"],
                    "deployment_id": result["deployment_id"],
                    "project_name": result["project_name"],
                    "environment": environment,
                    "logs": deployment_logs
                }
            else:
                deployment_logs.append(f"❌ Deployment failed: {result.get('message', 'Unknown error')}")
                return {
                    "status": "error",
                    "error_type": "deployment_failed",
                    "message": result.get("message", "Vercel deployment failed"),
                    "logs": deployment_logs,
                    "suggestions": [
                        "Check Vercel API token permissions",
                        "Verify project configuration",
                        "Try with different project name"
                    ]
                }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": "deployment_failed",
            "message": f"Deployment failed: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }

if __name__ == "__main__":
    # Test deployment
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vercel_deployment.py <project_id> [project_name]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🚀 Testing Vercel deployment for project: {project_id}")
    
    result = deploy_frontend_to_vercel(
        project_id=project_id,
        project_name=project_name
    )
    
    print(f"\n📊 Deployment Result:")
    print(json.dumps(result, indent=2))