"""
Cloudflare Pages deployment service
Downloads frontend from Azure storage and deploys to Cloudflare Pages
"""

import os
import tempfile
import shutil
import subprocess
from typing import Dict, Optional
from pathlib import Path

from cloud_storage import AzureBlobStorage

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

def deploy_frontend_to_cloudflare(project_id: str, project_name: str = None, environment: str = "production", custom_env_vars: Dict[str, str] = None) -> dict:
    """
    Deploy frontend to Cloudflare Pages
    
    Args:
        project_id: Azure storage project ID
        project_name: Cloudflare project name (auto-generated if None)
        environment: Deployment environment (production/staging)
        custom_env_vars: Additional environment variables (merged with project .env)
        
    Returns:
        dict: Deployment result with status, URLs, and logs
    """
    
    # Get Cloudflare credentials
    cf_token = os.getenv('CLOUDFLARE_API_TOKEN')
    cf_account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    
    if not cf_token or not cf_account_id:
        return {
            "status": "error",
            "error_type": "missing_credentials", 
            "message": "Cloudflare API token or Account ID not configured",
            "suggestions": [
                "Set CLOUDFLARE_API_TOKEN environment variable",
                "Set CLOUDFLARE_ACCOUNT_ID environment variable"
            ]
        }
    
    # Generate project name if not provided
    if not project_name:
        project_name = f"deploy-{project_id.replace('_', '-').lower()}"
    
    deployment_logs = []
    storage = AzureBlobStorage()
    
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
            
            for file_path in frontend_files:
                content = storage.download_file(project_id, file_path)
                if content is not None:
                    local_path = file_path[9:]  # Remove 'frontend/' prefix
                    full_local_path = os.path.join(frontend_dir, local_path)
                    
                    os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                    
                    with open(full_local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Extract environment variables from .env file
                    if local_path == '.env':
                        env_vars_from_project = parse_env_file(content)
                        deployment_logs.append(f"📄 Found .env file with {len(env_vars_from_project)} variables")
                    
                    downloaded_count += 1
            
            deployment_logs.append(f"✅ Downloaded {downloaded_count} frontend files")
            
            # Merge environment variables (custom overrides project)
            final_env_vars = {**env_vars_from_project}
            if custom_env_vars:
                final_env_vars.update(custom_env_vars)
                deployment_logs.append(f"🔧 Merged {len(custom_env_vars)} custom environment variables")
            
            return _deploy_to_cloudflare(frontend_dir, {
                "project_name": project_name,
                "environment": environment,
                "env_vars": final_env_vars,
                "force_rebuild": False
            }, cf_token, cf_account_id, deployment_logs)
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": "deployment_failed",
            "message": f"Deployment failed: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }

def _deploy_to_cloudflare(frontend_path: str, payload: dict, cf_token: str, cf_account_id: str, deployment_logs: list) -> dict:
    """Internal deployment function"""
    
    project_name = payload["project_name"]
    environment = payload.get("environment", "production")
    env_vars = payload.get("env_vars", {})
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_dir = os.path.join(temp_dir, "deploy")
            
            # Copy frontend files
            deployment_logs.append("📂 Copying frontend files to build directory")
            shutil.copytree(frontend_path, deploy_dir)
            
            # Create environment file
            if env_vars:
                deployment_logs.append(f"🔧 Creating environment file with {len(env_vars)} variables")
                env_content = ["NODE_ENV=production"]
                
                for key, value in env_vars.items():
                    if not key.startswith(('VITE_', 'REACT_APP_', 'NEXT_PUBLIC_', 'VUE_APP_')):
                        key = f"VITE_{key}"
                    env_content.append(f"{key}={value}")
                
                env_file_path = os.path.join(deploy_dir, '.env.production')
                with open(env_file_path, 'w') as f:
                    f.write('\n'.join(env_content))
            
            # Skip local build - let Cloudflare Pages handle it
            build_dir = deploy_dir
            deployment_logs.append("📁 Skipping local build - Cloudflare Pages will handle build process")
            
            deployment_env = os.environ.copy()
            deployment_env.update({
                'PATH': f"/opt/homebrew/opt/node@20/bin:{os.environ.get('PATH', '')}:/usr/local/bin",
                'CLOUDFLARE_API_TOKEN': cf_token,
                'CLOUDFLARE_ACCOUNT_ID': cf_account_id,
                'NODE_ENV': 'production'
            })
            
            # Create Cloudflare Pages project first
            deployment_logs.append(f"🏗️ Creating Cloudflare Pages project: {project_name}")
            
            create_cmd = [
                'npx', 'wrangler', 'pages', 'project', 'create', project_name,
                '--production-branch', environment
            ]
            
            create_result = subprocess.run(
                create_cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                env=deployment_env,
                timeout=120
            )
            
            if create_result.returncode != 0:
                if "already exists" not in create_result.stderr.lower():
                    deployment_logs.append(f"⚠️ Project creation warning: {create_result.stderr}")
                else:
                    deployment_logs.append(f"📋 Project {project_name} already exists")
            else:
                deployment_logs.append(f"✅ Created project: {project_name}")
            
            # Deploy to Cloudflare Pages
            deployment_logs.append(f"🚀 Deploying to Cloudflare Pages: {project_name}")
            
            wrangler_cmd = [
                'npx', 'wrangler', 'pages', 'deploy', build_dir,
                '--project-name', project_name,
                '--branch', environment
            ]
            
            deploy_result = subprocess.run(
                wrangler_cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                env=deployment_env,
                timeout=600
            )
            
            # Parse output
            all_output = []
            if deploy_result.stdout:
                all_output.extend(deploy_result.stdout.split('\n'))
            if deploy_result.stderr:
                all_output.extend(deploy_result.stderr.split('\n'))
            
            deployment_logs.extend([line for line in all_output if line.strip()])
            
            if deploy_result.returncode == 0:
                # Extract URLs
                deployment_url = None
                preview_url = None
                
                for line in all_output:
                    if 'https://' in line and '.pages.dev' in line:
                        if not deployment_url:
                            deployment_url = line.strip()
                        elif not preview_url and line != deployment_url:
                            preview_url = line.strip()
                
                if not deployment_url:
                    deployment_url = f"https://{project_name}.pages.dev"
                
                deployment_logs.append("✅ Deployment successful!")
                
                return {
                    "status": "success",
                    "deployment_url": deployment_url,
                    "preview_url": preview_url,
                    "project_name": project_name,
                    "environment": environment,
                    "logs": deployment_logs
                }
            else:
                return {
                    "status": "error",
                    "error_type": "deployment_failed",
                    "message": "Cloudflare deployment failed",
                    "logs": deployment_logs,
                    "suggestions": [
                        "Check Cloudflare API token permissions",
                        "Verify project name is available",
                        "Try redeploying with different project name"
                    ]
                }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Deployment timed out",
            "logs": deployment_logs + ["⏱️ Deployment timed out after 10 minutes"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unexpected_error",
            "message": f"Unexpected deployment error: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }