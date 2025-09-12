#!/usr/bin/env python3
"""
Test script for Cloudflare deployment functionality
Downloads a real project from Azure storage and tests the deployment process
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json
from typing import Dict, Optional
from pathlib import Path

# Add parent directory to path to import cloud_storage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cloud_storage import AzureBlobStorage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_env_file(content: str) -> Dict[str, str]:
    """Parse .env file content and return environment variables"""
    env_vars = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            # Remove quotes if present
            value = value.strip().strip('"').strip("'")
            env_vars[key.strip()] = value
    return env_vars

def test_cloudflare_deployment(project_id: str = None):
    """Test the complete Cloudflare deployment process"""
    
    print("🧪 Testing Cloudflare Pages Deployment")
    print("=" * 50)
    
    # Get project ID from command line or use default
    if not project_id:
        if len(sys.argv) > 1:
            project_id = sys.argv[1].strip()
        else:
            project_id = "horizon-693-77b80"  # Default fallback
    
    print(f"🎯 Using project ID: {project_id}")
    
    # Check required environment variables
    required_env_vars = {
        'CLOUDFLARE_API_TOKEN': 'Cloudflare API Token',
        'CLOUDFLARE_ACCOUNT_ID': 'Cloudflare Account ID'
    }
    
    missing_vars = []
    for var, description in required_env_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {description}")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(var)
        print("\n📝 Please set these environment variables in your .env file:")
        print("   CLOUDFLARE_API_TOKEN=your-token-here")
        print("   CLOUDFLARE_ACCOUNT_ID=your-account-id-here")
        print("\n🔗 Get credentials from:")
        print("   API Token: https://dash.cloudflare.com/profile/api-tokens")
        print("   Account ID: Found in your Cloudflare dashboard sidebar")
        return False
    
    print("✅ Environment variables configured")
    
    # Initialize cloud storage directly
    storage = AzureBlobStorage()
    print("✅ Azure storage initialized")
    
    # Download project frontend to temporary directory
    print(f"\n⬇️ Downloading frontend files for {project_id}...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            frontend_dir = os.path.join(temp_dir, "frontend")
            os.makedirs(frontend_dir, exist_ok=True)
            
            # Download all frontend files
            frontend_files = storage.list_files(project_id, "frontend/")
            downloaded_count = 0
            env_vars_from_project = {}
            
            for file_path in frontend_files:
                content = storage.download_file(project_id, file_path)
                if content is not None:
                    # Remove 'frontend/' prefix for local storage
                    local_path = file_path[9:]  # Remove 'frontend/'
                    full_local_path = os.path.join(frontend_dir, local_path)
                    
                    # Create directories if needed
                    os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                    
                    # Write file
                    with open(full_local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Extract environment variables from .env file
                    if local_path == '.env':
                        env_vars_from_project = parse_env_file(content)
                        print(f"📄 Found .env file with {len(env_vars_from_project)} variables")
                    
                    downloaded_count += 1
            
            print(f"✅ Downloaded {downloaded_count} frontend files")
            
            if downloaded_count == 0:
                print("❌ No frontend files to deploy")
                return False
            
            # Show extracted environment variables
            if env_vars_from_project:
                print(f"\n🔧 Environment variables from project .env:")
                for key, value in env_vars_from_project.items():
                    # Hide sensitive values
                    display_value = "***hidden***" if any(word in key.lower() for word in ['token', 'key', 'secret', 'password']) else value
                    print(f"   {key}={display_value}")
            
            # Test the deployment function
            print(f"\n🚀 Testing deployment function...")
            
            # Create unique project name based on project ID
            project_name = f"deploy-{project_id.replace('_', '-').lower()}"
            
            # Test payload using real environment variables from the project
            test_payload = {
                "project_name": project_name,
                "environment": "production",
                "env_vars": env_vars_from_project,  # Use real env vars from project
                "force_rebuild": False
            }
            
            result = deploy_cloudflare_test(frontend_dir, test_payload)
            
            print(f"\n📋 Deployment Result:")
            print(f"   Status: {result.get('status', 'unknown')}")
            if result.get('status') == 'success':
                print(f"   🌐 Deployment URL: {result.get('deployment_url', 'N/A')}")
                print(f"   🔗 Preview URL: {result.get('preview_url', 'N/A')}")
                print(f"   🏷️ Project Name: {result.get('project_name', 'N/A')}")
                print(f"   🔧 Environment: {result.get('environment', 'N/A')}")
            elif result.get('status') == 'error':
                print(f"   ❌ Error Type: {result.get('error_type', 'unknown')}")
                print(f"   📝 Message: {result.get('message', 'N/A')}")
                if result.get('suggestions'):
                    print(f"   💡 Suggestions:")
                    for suggestion in result['suggestions']:
                        print(f"      - {suggestion}")
            
            # Show logs
            if result.get('logs'):
                print(f"\n📋 Deployment Logs:")
                for log in result['logs']:
                    print(f"   {log}")
            
            return result.get('status') == 'success'
    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def deploy_cloudflare_test(frontend_path: str, payload: dict) -> dict:
    """Test version of the Cloudflare deployment function from updated-worker.py"""
    
    project_name = payload["project_name"]
    environment = payload.get("environment", "production")
    env_vars = payload.get("env_vars", {})
    force_rebuild = payload.get("force_rebuild", False)
    
    # Get Cloudflare credentials from environment
    cf_token = os.getenv('CLOUDFLARE_API_TOKEN')
    cf_account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    
    if not cf_token or not cf_account_id:
        return {
            "status": "error",
            "error_type": "missing_credentials", 
            "message": "Cloudflare API token or Account ID not configured in environment variables",
            "suggestions": [
                "Set CLOUDFLARE_API_TOKEN environment variable",
                "Set CLOUDFLARE_ACCOUNT_ID environment variable"
            ]
        }
    
    deployment_logs = []
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_dir = os.path.join(temp_dir, "deploy")
            
            # Copy frontend files to temporary directory
            deployment_logs.append("📂 Copying frontend files to temporary build directory")
            print(f"Copying {frontend_path} to {deploy_dir}")
            shutil.copytree(frontend_path, deploy_dir)
            
            # Create environment file with custom variables
            if env_vars:
                deployment_logs.append(f"🔧 Creating environment file with {len(env_vars)} variables")
                env_content = ["NODE_ENV=production"]
                
                for key, value in env_vars.items():
                    # For Vite applications, use VITE_ prefix for client-side variables
                    if not key.startswith(('VITE_', 'REACT_APP_', 'NEXT_PUBLIC_', 'VUE_APP_')):
                        key = f"VITE_{key}"
                    env_content.append(f"{key}={value}")
                
                env_file_path = os.path.join(deploy_dir, '.env.production')
                with open(env_file_path, 'w') as f:
                    f.write('\n'.join(env_content))
                print(f"Created environment file: {env_file_path}")
            
            # Detect and run build process
            package_json_path = os.path.join(deploy_dir, 'package.json')
            build_dir = deploy_dir
            
            # Skip local build - let Cloudflare Pages handle it
            deployment_logs.append("📁 Skipping local build - Cloudflare Pages will handle build process")
            
            # Setup deployment environment
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
                # Project might already exist, which is fine
                if "already exists" not in create_result.stderr.lower():
                    deployment_logs.append(f"⚠️ Project creation warning: {create_result.stderr}")
                else:
                    deployment_logs.append(f"📋 Project {project_name} already exists")
            else:
                deployment_logs.append(f"✅ Created project: {project_name}")
            
            # Deploy to Cloudflare Pages using Wrangler
            deployment_logs.append(f"🚀 Deploying to Cloudflare Pages: {project_name}")
            
            wrangler_cmd = [
                'npx', 'wrangler', 'pages', 'deploy', build_dir,
                '--project-name', project_name,
                '--branch', environment
            ]
            
            print(f"Running deployment command: {' '.join(wrangler_cmd)}")
            
            deploy_result = subprocess.run(
                wrangler_cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                env=deployment_env,
                timeout=600  # 10 minutes
            )
            
            # Parse deployment output
            stdout_lines = deploy_result.stdout.split('\n') if deploy_result.stdout else []
            stderr_lines = deploy_result.stderr.split('\n') if deploy_result.stderr else []
            
            all_output = stdout_lines + stderr_lines
            deployment_logs.extend([line for line in all_output if line.strip()])
            
            if deploy_result.returncode == 0:
                # Extract URLs from deployment output
                deployment_url = None
                preview_url = None
                
                for line in all_output:
                    if 'https://' in line and '.pages.dev' in line:
                        if not deployment_url:
                            deployment_url = line.strip()
                        elif not preview_url and line != deployment_url:
                            preview_url = line.strip()
                
                # Fallback URL construction if not found in output
                if not deployment_url:
                    deployment_url = f"https://{project_name}.pages.dev"
                
                deployment_logs.append(f"✅ Deployment successful!")
                
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
                    "message": "Cloudflare Pages deployment failed",
                    "logs": deployment_logs,
                    "suggestions": [
                        "Check Cloudflare API token permissions",
                        "Verify project name is available",
                        "Review deployment logs for specific errors",
                        "Try redeploying with force_rebuild=true"
                    ]
                }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Deployment timed out",
            "logs": deployment_logs + ["⏱️ Deployment process timed out after 10 minutes"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unexpected_error",
            "message": f"Unexpected error during deployment: {str(e)}",
            "logs": deployment_logs + [f"Error: {str(e)}"]
        }

if __name__ == "__main__":
    print("🧪 Cloudflare Pages Deployment Test")
    print("Usage: python test_cloudflare_deployment.py [project_id]")
    print("Example: python test_cloudflare_deployment.py horizon-123-abc45")
    print()
    
    success = test_cloudflare_deployment()
    sys.exit(0 if success else 1)