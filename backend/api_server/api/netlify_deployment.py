"""
Netlify Deployment API Module

Handles frontend deployment to Netlify for projects stored in Azure Storage.
"""

import os
import json
import requests
import tempfile
import zipfile
import subprocess
import shutil
import asyncio
from pathlib import Path
from cloud_storage import AzureBlobStorage

async def update_backend_with_frontend_url(project_id: str, frontend_url: str, storage, deployment_logs):
    """Update backend .env file and Modal secrets with frontend URL"""
    try:
        # Get project metadata to find backend deployment info
        metadata = storage.load_project_metadata(project_id)
        if not metadata:
            raise Exception("No project metadata found")
        
        backend_deployment = metadata.get("backend_deployment")
        if not backend_deployment:
            raise Exception("No backend deployment found")
        
        secret_name = backend_deployment.get("secret_name")
        if not secret_name:
            raise Exception("No Modal secret name found")
        
        deployment_logs.append(f"📋 Found backend secret: {secret_name}")
        
        # Step 1: Update backend .env file
        backend_env_path = "backend/.env"
        existing_env = storage.download_file(project_id, backend_env_path) or ""
        
        # Parse existing .env and add/update FRONTEND_URL
        env_lines = []
        frontend_url_updated = False
        
        for line in existing_env.split('\n'):
            line = line.strip()
            if line.startswith('FRONTEND_URL='):
                env_lines.append(f'FRONTEND_URL={frontend_url}')
                frontend_url_updated = True
            elif line:
                env_lines.append(line)
        
        # Add FRONTEND_URL if not found
        if not frontend_url_updated:
            env_lines.append(f'FRONTEND_URL={frontend_url}')
        
        # Update .env file
        new_env_content = '\n'.join(env_lines) + '\n'
        env_success = storage.upload_file(project_id, backend_env_path, new_env_content)
        
        if env_success:
            deployment_logs.append("✅ Updated backend .env with FRONTEND_URL")
        else:
            deployment_logs.append("⚠️ Failed to update backend .env file")
        
        # Step 2: Update Modal secrets
        deployment_logs.append("🔐 Updating Modal secrets...")
        
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Add parent directory to path
        from streaming_api import create_modal_secrets_standalone, ModalSecretsRequest
        
        # Get all current .env variables
        env_vars = {}
        for line in new_env_content.split('\n'):
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
        
        # Create secrets request with all variables including FRONTEND_URL
        secrets_request = ModalSecretsRequest(
            secret_name=secret_name,
            secrets=env_vars,
            overwrite=True
        )
        
        # Update the secrets
        secrets_result = await create_modal_secrets_standalone(secrets_request)
        
        if secrets_result.status == "success":
            deployment_logs.append(f"✅ Updated Modal secrets ({secrets_result.secret_count} keys)")
        else:
            deployment_logs.append(f"⚠️ Failed to update Modal secrets: {secrets_result.error}")
            
    except Exception as e:
        deployment_logs.append(f"❌ Backend update error: {str(e)}")
        raise e

def deploy_frontend_to_netlify(project_id: str, project_name: str = None) -> dict:
    netlify_token = os.getenv('NETLIFY_TOKEN', 'nfp_zSYp8Dy1iDW6b94tLkwajKtcw3vgv47t85be')
    
    if not netlify_token:
        return {
            "status": "error",
            "error_type": "missing_credentials",
            "message": "Netlify API token not configured",
            "suggestions": [
                "Set NETLIFY_TOKEN environment variable",
                "Get token from https://app.netlify.com/user/applications"
            ]
        }
    
    # Generate unique project name with timestamp to avoid conflicts
    import time
    timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
    if not project_name:
        project_name = f"app-{project_id.replace('_', '-').lower()}-{timestamp}"
    else:
        # Even if project_name is provided, add timestamp to ensure uniqueness
        project_name = f"{project_name}-{timestamp}"
    
    deployment_logs = []
    storage = AzureBlobStorage()
    temp_dir = None
    
    try:
        # Create temp directory for project
        temp_dir = tempfile.mkdtemp(prefix=f"netlify_deploy_{project_id}_")
        frontend_dir = os.path.join(temp_dir, "frontend")
        os.makedirs(frontend_dir, exist_ok=True)
        
        deployment_logs.append(f"📂 Downloading frontend files for project {project_id}")
        frontend_files = storage.list_files(project_id, "frontend/")
        
        if not frontend_files:
            return {
                "status": "error",
                "error_type": "no_frontend_files", 
                "message": f"No frontend files found for project {project_id}",
                "logs": deployment_logs
            }
        
        # Download all files to local filesystem
        downloaded_count = 0
        for file_path in frontend_files:
            content = storage.download_file(project_id, file_path)
            if content:
                local_path = file_path[9:]  # Remove 'frontend/' prefix
                full_local_path = os.path.join(frontend_dir, local_path)
                
                # Create directories if needed
                os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                
                # Write file content
                with open(full_local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                downloaded_count += 1
        
        deployment_logs.append(f"✅ Downloaded {downloaded_count} frontend files")
        
        # Install dependencies
        deployment_logs.append("📦 Installing dependencies...")
        install_result = subprocess.run(['npm', 'install', '--include=dev'], 
                                      cwd=frontend_dir, capture_output=True, text=True, timeout=300)
        if install_result.returncode != 0:
            return {
                "status": "error",
                "error_type": "install_failed",
                "message": f"npm install failed: {install_result.stderr}",
                "logs": deployment_logs
            }
        
        # Build the project  
        deployment_logs.append("🔨 Building project...")
        build_result = subprocess.run(['npm', 'run', 'build'], 
                                    cwd=frontend_dir, capture_output=True, text=True, timeout=300)
        if build_result.returncode != 0:
            return {
                "status": "error",
                "error_type": "build_failed",
                "message": f"npm run build failed: {build_result.stderr}",
                "logs": deployment_logs
            }
        
        # Check if dist directory was created
        dist_dir = os.path.join(frontend_dir, "dist")
        if not os.path.exists(dist_dir):
            return {
                "status": "error", 
                "error_type": "no_dist_folder",
                "message": "Build completed but no dist folder found",
                "logs": deployment_logs
            }
            
        deployment_logs.append("✅ Build completed successfully")
        
        # Create zip from dist folder only
        files = {}
        for root, dirs, filenames in os.walk(dist_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, dist_dir)
                with open(full_path, 'r', encoding='utf-8') as f:
                    files[relative_path] = f.read()
        
        # Add SPA redirect files for client-side routing
        files["_redirects"] = "/*    /index.html   200"
        
        deployment_logs.append(f"📦 Packaged {len(files)} built files")
        deployment_logs.append("📝 Added SPA redirect configuration")
        
        # Create zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
                for file_path, content in files.items():
                    zipf.writestr(file_path, content.encode('utf-8'))
            
            # Deploy to Netlify
            headers = {"Authorization": f"Bearer {netlify_token}"}
            
            # Create site
            site_data = {"name": project_name}
            site_resp = requests.post("https://api.netlify.com/api/v1/sites", headers=headers, json=site_data)
            
            if site_resp.status_code != 201:
                return {
                    "status": "error",
                    "error_type": "site_creation_failed",
                    "message": f"Failed to create site: {site_resp.text}",
                    "logs": deployment_logs
                }
            
            site_id = site_resp.json()["id"]
            deployment_logs.append(f"✅ Created site: {site_id}")
            
            # Deploy zip
            with open(temp_zip.name, 'rb') as f:
                deploy_resp = requests.post(
                    f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
                    headers={"Authorization": f"Bearer {netlify_token}", "Content-Type": "application/zip"},
                    data=f.read()
                )
            
            os.unlink(temp_zip.name)
            
            if deploy_resp.status_code not in [200, 201]:
                return {
                    "status": "error",
                    "error_type": "deployment_failed",
                    "message": f"Deploy failed: {deploy_resp.text}",
                    "logs": deployment_logs
                }
            
            deploy_data = deploy_resp.json()
            deployment_url = deploy_data.get("ssl_url")
            
            if deployment_url:
                deployment_logs.append("✅ Deployment successful!")
                
                # Update backend secrets and .env with frontend URL
                try:
                    deployment_logs.append("🔗 Updating backend with frontend URL...")
                    # Run the async function in a new event loop
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If we're already in an event loop, use run_in_executor
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run, 
                                    update_backend_with_frontend_url(project_id, deployment_url, storage, deployment_logs)
                                )
                                future.result()
                        else:
                            loop.run_until_complete(update_backend_with_frontend_url(project_id, deployment_url, storage, deployment_logs))
                    except RuntimeError:
                        # No event loop, create a new one
                        asyncio.run(update_backend_with_frontend_url(project_id, deployment_url, storage, deployment_logs))
                    
                    deployment_logs.append("✅ Backend updated with frontend URL")
                except Exception as e:
                    deployment_logs.append(f"⚠️ Failed to update backend: {str(e)}")
                    print(f"Warning: Could not update backend with frontend URL: {e}")
                
                return {
                    "status": "success",
                    "deployment_url": deployment_url,
                    "site_id": site_id,
                    "project_name": project_name,
                    "logs": deployment_logs
                }
            else:
                return {
                    "status": "error",
                    "error_type": "no_url_returned",
                    "message": "Deployment succeeded but no URL was returned",
                    "logs": deployment_logs
                }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": "deployment_failed", 
            "message": f"Deployment failed: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up temporary files from {temp_dir}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python netlify_deployment.py <project_id> [project_name]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🚀 Testing Netlify deployment for project: {project_id}")
    
    result = deploy_frontend_to_netlify(
        project_id=project_id,
        project_name=project_name
    )
    
    print(f"\n📊 Deployment Result:")
    print(json.dumps(result, indent=2))