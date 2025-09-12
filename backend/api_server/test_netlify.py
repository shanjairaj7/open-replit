#!/usr/bin/env python3
import os
import sys
import json
import requests
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from cloud_storage import AzureBlobStorage

def deploy_to_netlify(project_id: str, project_name: str):
    netlify_token = os.getenv('NETLIFY_TOKEN')
    
    if not netlify_token:
        print("❌ NETLIFY_TOKEN environment variable not set!")
        print("Get token from https://app.netlify.com/user/applications")
        return
    
    print(f"🚀 Deploying {project_id} to Netlify...")
    
    # Download files
    storage = AzureBlobStorage()
    frontend_files = storage.list_files(project_id, "frontend/")
    
    if not frontend_files:
        print("❌ No frontend files found")
        return
    
    files = {}
    for file_path in frontend_files:
        content = storage.download_file(project_id, file_path)
        if content:
            local_path = file_path[9:]  # Remove 'frontend/' prefix
            files[local_path] = content
    
    print(f"📦 Collected {len(files)} files")
    
    # Add SPA redirect files for client-side routing
    files["_redirects"] = "/*    /index.html   200"
    files["netlify.toml"] = '''[build]
  publish = "dist"
  command = "npm run build"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200'''
    
    print("📝 Added SPA redirect configuration")
    
    # Create zip
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            for file_path, content in files.items():
                zipf.writestr(file_path, content.encode('utf-8'))
        
        # Deploy
        headers = {"Authorization": f"Bearer {netlify_token}"}
        
        # Create site
        site_data = {"name": project_name}
        site_resp = requests.post("https://api.netlify.com/api/v1/sites", headers=headers, json=site_data)
        
        if site_resp.status_code != 201:
            print(f"❌ Failed to create site: {site_resp.text}")
            return
        
        site_id = site_resp.json()["id"]
        print(f"✅ Created site: {site_id}")
        
        # Deploy zip
        with open(temp_zip.name, 'rb') as f:
            deploy_resp = requests.post(
                f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
                headers={"Authorization": f"Bearer {netlify_token}", "Content-Type": "application/zip"},
                data=f.read()
            )
        
        os.unlink(temp_zip.name)
        
        if deploy_resp.status_code not in [200, 201]:
            print(f"❌ Deploy failed: {deploy_resp.text}")
            return
        
        deploy_data = deploy_resp.json()
        url = deploy_data.get("ssl_url")
        print(f"🎉 SUCCESS! Deployed to: {url}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_netlify.py <project_id> [project_name]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else f"app-{project_id}"
    
    deploy_to_netlify(project_id, project_name)