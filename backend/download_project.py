#!/usr/bin/env python3
import os
import json
import requests
from pathlib import Path

# Configuration
API_URL = "https://projects-api-production-e403.up.railway.app/api/projects/761eaac9-b6c0-4a40-8110-e40c3409778b/files/read"
PROJECT_ID = "761eaac9-b6c0-4a40-8110-e40c3409778b"
OUTPUT_DIR = "/tmp/client-management-system"

# List of files to download
FILES_TO_DOWNLOAD = [
    "package.json",
    "src/pages/Dashboard.tsx",
    "src/types/index.ts",
    "src/components/ui/data-table.tsx",
    "src/components/ui/status-badge.tsx",
    "src/hooks/useDebounce.ts",
    "src/hooks/useLocalStorage.ts",
    "src/lib/utils.ts",
    "vite.config.ts",
    "tsconfig.json",
    "index.html",
    # Add more common project files
    "src/App.tsx",
    "src/main.tsx",
    "src/index.css",
    "src/App.css",
    ".gitignore",
    "README.md",
    "package-lock.json",
    "postcss.config.js",
    "tailwind.config.js",
    "src/components/layout/Layout.tsx",
    "src/components/layout/Header.tsx",
    "src/components/layout/Sidebar.tsx",
    "src/pages/Home.tsx",
    "src/pages/Settings.tsx",
    "src/router.tsx",
    "src/routes.tsx",
    "src/components/ui/button.tsx",
    "src/components/ui/input.tsx",
    "src/components/ui/card.tsx",
    "src/components/ui/dialog.tsx",
    "src/components/ui/select.tsx",
    "src/components/ui/table.tsx",
    "src/components/ui/tabs.tsx",
    "src/components/ui/toast.tsx",
    "src/components/ui/toaster.tsx",
    "src/components/ui/use-toast.ts",
    "src/lib/api.ts",
    "src/lib/constants.ts",
    "src/store/index.ts",
    "src/styles/globals.css",
    "components.json",
    ".env.example",
    "src/vite-env.d.ts"
]

def download_file(file_path):
    """Download a single file from the API"""
    try:
        # Prepare the request
        headers = {"Content-Type": "application/json"}
        data = {"file_path": file_path}
        
        print(f"Downloading: {file_path}")
        response = requests.post(API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if "content" in result:
                # Create the full path
                full_path = Path(OUTPUT_DIR) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(result["content"])
                
                print(f"✓ Downloaded: {file_path}")
                return True
            else:
                print(f"✗ Failed to download {file_path}: No content in response")
                print(f"Response: {result}")
                return False
        else:
            print(f"✗ Failed to download {file_path}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error downloading {file_path}: {str(e)}")
        return False

def discover_more_files():
    """Try to discover more files by checking common directories"""
    additional_files = []
    
    # Common directories to check
    directories = [
        "src/components",
        "src/pages",
        "src/hooks",
        "src/utils",
        "src/services",
        "src/context",
        "src/assets",
        "public"
    ]
    
    # This would require a list endpoint which we don't have
    # So we'll just try common patterns
    return additional_files

def main():
    """Main function to download all files"""
    print(f"Starting download to {OUTPUT_DIR}")
    print(f"Project ID: {PROJECT_ID}")
    print("-" * 50)
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Download all files
    successful = 0
    failed = 0
    
    for file_path in FILES_TO_DOWNLOAD:
        if download_file(file_path):
            successful += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Download complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Files saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()