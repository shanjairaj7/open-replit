"""
Netlify Deployment API Module

Handles frontend deployment to Netlify for projects stored in Azure Storage.
"""

import os
import tempfile
import subprocess
import shutil
import json
from pathlib import Path
from cloud_storage import AzureBlobStorage
from datetime import datetime

def deploy_frontend_to_netlify(project_id: str) -> dict:
    """
    Deploy frontend to Netlify using auto-detected configuration
    
    Args:
        project_id: The project ID in Azure Storage
        
    Returns:
        dict: Deployment result with netlify_url, backend_url, etc.
        
    Raises:
        Exception: If deployment fails at any step
    """
    print(f"🚀 Starting Netlify deployment for project: {project_id}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use your Netlify token
    netlify_token = os.getenv('NETLIFY_AUTH_TOKEN', 'nfp_zSYp8Dy1iDW6b94tLkwajKtcw3vgv47t85be')
    
    env = os.environ.copy()
    env['NETLIFY_AUTH_TOKEN'] = netlify_token
    
    temp_dir = None
    try:
        # 1. Download project from Azure Storage
        print(f"🔄 Downloading project {project_id} from Azure Storage...")
        temp_dir = download_project_from_azure(project_id)
        frontend_dir = f"{temp_dir}/frontend"
        
        # 2. Read existing .env file (no changes needed!)
        env_vars = read_frontend_env_file(frontend_dir)
        backend_url = env_vars.get('VITE_APP_BACKEND_URL', 'not-found')
        
        print(f"📋 Auto-detected backend URL: {backend_url}")
        print(f"📋 Found {len(env_vars)} environment variables")
        
        # 3. Create SPA redirects file for Netlify
        create_spa_redirects(frontend_dir)
        
        # 4. Install dependencies
        install_dependencies(frontend_dir)
        
        # 5. Build project
        build_project(frontend_dir)
        
        # 6. Deploy to Netlify
        site_name = generate_site_name(project_id)
        deployment_result = deploy_to_netlify(f"{frontend_dir}/dist", site_name, env)
        
        result = {
            "status": "success",
            "netlify_url": deployment_result["url"],
            "site_name": site_name,
            "project_id": project_id,
            "backend_url": backend_url,
            "env_vars": len(env_vars),
            "deployed_at": datetime.now().isoformat(),
            "temp_dir": temp_dir
        }
        
        print(f"\n🎉 DEPLOYMENT SUCCESSFUL!")
        print(f"📱 Live URL: {result['netlify_url']}")
        print(f"🔗 Backend: {result['backend_url']}")
        print(f"🏷️  Site: {result['site_name']}")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return result
    
    except Exception as e:
        error_msg = f"Deployment failed: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("🧹 Cleaned up temporary files")

def read_frontend_env_file(frontend_dir: str) -> dict:
    """
    Read ALL variables from frontend .env file without modifications
    
    Args:
        frontend_dir: Path to frontend directory
        
    Returns:
        dict: All environment variables from .env file
    """
    env_file = Path(frontend_dir) / '.env'
    env_vars = {}
    
    if not env_file.exists():
        print("⚠️  No .env file found in frontend directory")
        return env_vars
    
    print("📄 Reading frontend .env file...")
    
    with open(env_file, 'r', encoding='utf-8') as f:
        line_count = 0
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                try:
                    # Handle values with = signs in them
                    key, value = line.split('=', 1)
                    # Remove surrounding quotes if present
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
                    line_count += 1
                except Exception as e:
                    print(f"⚠️  Skipping malformed line {line_num}: {line} ({e})")
    
    # Print found variables (hide sensitive ones)
    print(f"✅ Found {len(env_vars)} environment variables:")
    for key, value in sorted(env_vars.items()):
        if any(word in key.lower() for word in ['token', 'key', 'secret', 'password', 'auth']):
            print(f"   {key}=***hidden***")
        else:
            print(f"   {key}={value}")
    
    return env_vars

def download_project_from_azure(project_id: str) -> str:
    """
    Download complete project from Azure Storage
    
    Args:
        project_id: The project ID to download
        
    Returns:
        str: Path to temporary directory with downloaded files
        
    Raises:
        Exception: If project not found or download fails
    """
    storage = AzureBlobStorage()
    temp_dir = tempfile.mkdtemp(prefix=f"deploy_{project_id}_")
    
    print(f"📂 Created temporary directory: {temp_dir}")
    
    try:
        # Get project structure from Azure
        structure = storage.get_project_structure(project_id)
        all_files = structure.get('all_files', [])
        
        if not all_files:
            raise Exception(f"Project '{project_id}' not found in Azure Storage or has no files")
        
        print(f"📋 Project has {len(all_files)} files")
        
        # Download each file
        downloaded_count = 0
        failed_count = 0
        
        for file_path in all_files:
            try:
                print(f"📥 Downloading: {file_path}")
                content = storage.download_file(project_id, file_path)
                
                if content:
                    # Create local file path
                    local_path = Path(temp_dir) / file_path
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file content
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    downloaded_count += 1
                else:
                    print(f"⚠️  Empty content for: {file_path}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"❌ Failed to download {file_path}: {e}")
                failed_count += 1
        
        print(f"✅ Downloaded {downloaded_count} files")
        if failed_count > 0:
            print(f"⚠️  Failed to download {failed_count} files")
        
        # Verify frontend directory exists
        frontend_path = Path(temp_dir) / "frontend"
        if not frontend_path.exists():
            raise Exception(f"No 'frontend' directory found in project {project_id}")
        
        # Check for package.json
        package_json = frontend_path / "package.json"
        if not package_json.exists():
            raise Exception(f"No package.json found in frontend directory")
        
        print("✅ Frontend directory structure validated")
        return temp_dir
        
    except Exception as e:
        # Cleanup on failure
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise e

def create_spa_redirects(frontend_dir: str):
    """
    Create _redirects file for Netlify SPA routing
    
    Args:
        frontend_dir: Path to frontend directory
    """
    print("📝 Creating SPA redirect configuration...")
    
    # Create public directory if it doesn't exist
    public_dir = Path(frontend_dir) / "public"
    public_dir.mkdir(exist_ok=True)
    
    # Create _redirects file
    redirects_file = public_dir / "_redirects"
    redirects_content = "/* /index.html 200\n"
    
    with open(redirects_file, 'w') as f:
        f.write(redirects_content)
    
    print("✅ Created _redirects file for SPA routing")

def install_dependencies(frontend_dir: str):
    """
    Install npm dependencies
    
    Args:
        frontend_dir: Path to frontend directory
        
    Raises:
        Exception: If npm install fails
    """
    print("📦 Installing npm dependencies...")
    
    # Check if package.json exists
    package_json = Path(frontend_dir) / "package.json"
    if not package_json.exists():
        raise Exception("package.json not found in frontend directory")
    
    try:
        result = subprocess.run(
            ['npm', 'install', '--production=false'],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"npm install failed with exit code {result.returncode}:\n{result.stderr}")
        
        # Check if node_modules was created
        node_modules = Path(frontend_dir) / "node_modules"
        if not node_modules.exists():
            raise Exception("npm install succeeded but node_modules directory not found")
        
        print("✅ Dependencies installed successfully")
        
    except subprocess.TimeoutExpired:
        raise Exception("npm install timed out after 5 minutes")
    except FileNotFoundError:
        raise Exception("npm command not found. Please install Node.js and npm")

def build_project(frontend_dir: str):
    """
    Build the frontend project
    
    Args:
        frontend_dir: Path to frontend directory
        
    Raises:
        Exception: If build fails
    """
    print("🔨 Building frontend project...")
    
    try:
        result = subprocess.run(
            ['npm', 'run', 'build'],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Build failed with exit code {result.returncode}:\n{result.stderr}")
        
        # Verify dist directory was created
        dist_path = Path(frontend_dir) / 'dist'
        if not dist_path.exists():
            raise Exception("Build completed but no 'dist' directory found")
        
        # Check if dist has files
        dist_files = list(dist_path.rglob('*'))
        if not dist_files:
            raise Exception("Build completed but dist directory is empty")
        
        print(f"✅ Build completed successfully ({len(dist_files)} files in dist/)")
        
    except subprocess.TimeoutExpired:
        raise Exception("Build timed out after 5 minutes")

def generate_site_name(project_id: str) -> str:
    """
    Generate clean site name for Netlify
    
    Args:
        project_id: Original project ID
        
    Returns:
        str: Clean site name for Netlify
    """
    # Convert project_id to netlify-friendly name
    clean_name = project_id.lower().replace('_', '-').replace(' ', '-')
    # Remove any invalid characters
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%m%d%H%M")
    return f"app-{clean_name}-{timestamp}"

def deploy_to_netlify(dist_dir: str, site_name: str, env: dict) -> dict:
    """
    Deploy build files to Netlify
    
    Args:
        dist_dir: Path to built files directory
        site_name: Name for the Netlify site
        env: Environment variables including NETLIFY_AUTH_TOKEN
        
    Returns:
        dict: Deployment result with URL and site info
        
    Raises:
        Exception: If deployment fails
    """
    print(f"🚀 Deploying to Netlify as '{site_name}'...")
    
    try:
        # Check if Netlify CLI is installed
        try:
            subprocess.run(['netlify', '--version'], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise Exception("Netlify CLI not found. Install with: npm install -g netlify-cli")
        
        # Deploy using create-site approach (creates and deploys in one command)
        print("🆕 Creating site and deploying draft...")
        
        # First, create site and deploy draft
        draft_result = subprocess.run([
            'netlify', 'deploy',
            '--create-site', site_name,
            '--dir', dist_dir
        ], capture_output=True, text=True, env=env, timeout=300)
        
        if draft_result.returncode != 0:
            raise Exception(f"Draft deployment failed: {draft_result.stderr}\n\nOutput: {draft_result.stdout}")
        
        print("📤 Promoting to production...")
        
        # Now deploy to production
        prod_result = subprocess.run([
            'netlify', 'deploy',
            '--prod'
        ], capture_output=True, text=True, env=env, timeout=300)
        
        if prod_result.returncode != 0:
            raise Exception(f"Production deployment failed: {prod_result.stderr}\n\nOutput: {prod_result.stdout}")
        
        # Parse the production output to extract the URL
        output_lines = prod_result.stdout.split('\n') + prod_result.stderr.split('\n')
        deploy_url = None
        
        # Look for production URL patterns
        for line in output_lines:
            if 'Production deploy is live' in line or 'Deployed to production URL:' in line:
                continue
            elif f'https://{site_name}.netlify.app' in line:
                import re
                url_match = re.search(r'https://[^\s]+\.netlify\.app[^\s]*', line)
                if url_match:
                    deploy_url = url_match.group(0)
                    break
        
        # Fallback - construct expected URL
        if not deploy_url:
            deploy_url = f"https://{site_name}.netlify.app"
        
        print(f"✅ Successfully deployed to: {deploy_url}")
        
        return {
            "url": deploy_url,
            "site_id": site_name,
            "deploy_id": "production",
            "site_name": site_name
        }
        
    except subprocess.TimeoutExpired:
        raise Exception("Netlify deployment timed out after 5 minutes")
    except Exception as e:
        raise Exception(f"Netlify deployment failed: {str(e)}")