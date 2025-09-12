#!/usr/bin/env python3
"""
Upload Stripe Kit to Azure Storage
This script uploads the stripe_kit folder to Azure Blob Storage as a starter kit template
"""

import os
import sys
from pathlib import Path
from cloud_storage import AzureBlobStorage

def upload_stripe_kit_to_azure():
    """Upload the stripe_kit folder to Azure Storage as a starter kit template"""
    
    # Path to the stripe_kit folder
    stripe_kit_path = Path(__file__).parent.parent.parent.parent / "downloaded_projects" / "horizon-693-77b80" / "backend" / "stripe_kit"
    
    print(f"🔍 Looking for stripe_kit at: {stripe_kit_path}")
    
    if not stripe_kit_path.exists():
        print(f"❌ Stripe kit not found at: {stripe_kit_path}")
        return False
    
    # Initialize Azure storage
    try:
        storage = AzureBlobStorage()
        print("✅ Azure storage initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Azure storage: {e}")
        return False
    
    # Upload all files in the stripe_kit folder
    uploaded_files = 0
    failed_files = 0
    
    print(f"📤 Starting upload of stripe_kit files...")
    
    for file_path in stripe_kit_path.rglob('*'):
        if file_path.is_file():
            # Get relative path from stripe_kit root
            relative_path = file_path.relative_to(stripe_kit_path)
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Upload to Azure with special starter-kits prefix
                azure_path = f"starter-kits/stripe/{relative_path}"
                
                if storage.upload_file("templates", azure_path, content):
                    print(f"  ✅ Uploaded: {relative_path}")
                    uploaded_files += 1
                else:
                    print(f"  ❌ Failed to upload: {relative_path}")
                    failed_files += 1
                    
            except Exception as e:
                print(f"  ❌ Error reading/uploading {relative_path}: {e}")
                failed_files += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"  ✅ Uploaded: {uploaded_files} files")
    print(f"  ❌ Failed: {failed_files} files")
    
    if uploaded_files > 0:
        print(f"🎉 Stripe kit successfully uploaded to Azure Storage!")
        print(f"📍 Location: templates/starter-kits/stripe/")
        return True
    else:
        print(f"💥 No files were uploaded successfully")
        return False

if __name__ == "__main__":
    print("🚀 Uploading Stripe Kit to Azure Storage...")
    success = upload_stripe_kit_to_azure()
    
    if success:
        print("\n✅ Upload completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Upload failed!")
        sys.exit(1)