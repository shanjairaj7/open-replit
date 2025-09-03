#!/usr/bin/env python3
"""
Documentation Upload Script
Uploads the optimized LLM integration documentation to Azure docs storage
"""

import os
import sys
from pathlib import Path
from cloud_storage import get_cloud_storage

def main():
    """Upload documentation to Azure storage"""
    print("📚 Documentation Upload Script")
    print("=" * 50)
    
    # Initialize cloud storage
    cloud_storage = get_cloud_storage()
    if not cloud_storage:
        print("❌ Failed to initialize cloud storage")
        return False
    
    # Define all documentation files to upload
    llm_docs_dir = Path(__file__).parent.parent / "llm_docs"
    docs_to_upload = [
        ("openai_llm.md", "llm_integration_openai.md"),
        ("exa_ai_search.md", "exa_ai_integration.md"),
    ]
    
    # Read all documentation files
    all_docs_content = {}
    for source_filename, target_name in docs_to_upload:
        source_file = llm_docs_dir / source_filename
        print(f"📄 Source: {source_file}")
        print(f"🎯 Target: {target_name}")
        
        if not source_file.exists():
            print(f"⚠️ Source file not found: {source_file}, skipping...")
            continue
        
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            all_docs_content[target_name] = content
            print(f"✅ Read {source_filename}: {len(content)} characters")
        except Exception as e:
            print(f"❌ Failed to read {source_filename}: {e}")
            continue
    
    if not all_docs_content:
        print("❌ No documentation files could be read")
        return False
    
    print(f"\n📊 Total docs to upload: {len(all_docs_content)}")
    
    # List current docs
    print("\n📋 Current docs in Azure:")
    current_docs = cloud_storage.list_docs()
    for doc in current_docs:
        print(f"  - {doc}")
    
    # Delete all existing docs
    print(f"\n🗑️ Clearing existing docs...")
    if not cloud_storage.delete_all_docs():
        print("⚠️ Warning: Failed to clear some existing docs, continuing anyway...")
    
    # Upload all documentation files
    print(f"\n📤 Uploading {len(all_docs_content)} documentation files...")
    upload_count = 0
    total_chars = 0
    
    for target_name, content in all_docs_content.items():
        print(f"\n📤 Uploading: {target_name}")
        success = cloud_storage.upload_doc(target_name, content)
        
        if success:
            print(f"✅ Successfully uploaded {target_name} ({len(content)} characters)")
            upload_count += 1
            total_chars += len(content)
        else:
            print(f"❌ Failed to upload {target_name}")
    
    # Verify all uploads
    print("\n🔍 Verifying uploads...")
    uploaded_docs = cloud_storage.list_docs()
    print(f"📋 Found {len(uploaded_docs)} documentation files in Azure")
    
    all_verified = True
    for target_name in all_docs_content.keys():
        if target_name in uploaded_docs:
            print(f"✅ Verified: {target_name}")
        else:
            print(f"❌ Missing: {target_name}")
            all_verified = False
    
    if all_verified and upload_count == len(all_docs_content):
        print(f"\n✅ All uploads successful!")
        print(f"📊 Final stats: {upload_count} docs, {total_chars} total characters")
        return True
    else:
        print(f"\n⚠️ Partial upload: {upload_count}/{len(all_docs_content)} succeeded")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)