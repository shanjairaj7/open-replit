#!/usr/bin/env python3
"""
Debug script to test Azure upload failures and understand why 
the bulk file creation failed for horizon-543-56f69
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


def test_azure_connection():
    """Test basic Azure connectivity"""
    print("🔍 Testing Azure Blob Storage connection...")
    
    try:
        storage = AzureBlobStorage()
        
        # Test basic operations
        test_content = "Test file content"
        test_path = "test/debug_file.txt"
        project_id = "test-project"
        
        print(f"📤 Testing upload...")
        upload_success = storage.upload_file(project_id, test_path, test_content)
        
        if upload_success:
            print(f"✅ Upload successful")
            
            # Test download
            print(f"📥 Testing download...")
            downloaded = storage.download_file(project_id, test_path)
            
            if downloaded == test_content:
                print(f"✅ Download successful - content matches")
                
                # Clean up
                storage.delete_file(project_id, test_path)
                print(f"🗑️ Cleanup successful")
                return True
            else:
                print(f"❌ Download failed or content mismatch")
                return False
        else:
            print(f"❌ Upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Azure connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulk_upload_simulation():
    """Simulate the bulk upload that failed for horizon-543-56f69"""
    print("\n🧪 Simulating bulk upload scenario...")
    
    # Simulate the files that should have been created
    test_files = [
        ("frontend/src/pages/DealsPage.tsx", "import React from 'react';\n\nexport default function DealsPage() {\n  return <div>Deals Page</div>;\n}" * 100),
        ("frontend/src/pages/AuditLogPage.tsx", "import React from 'react';\n\nexport default function AuditLogPage() {\n  return <div>Audit Log Page</div>;\n}" * 30),
        ("backend/routes/crm.py", "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get('/health')\ndef health():\n    return {'status': 'ok'}\n" * 150),
    ]
    
    project_id = "debug-test-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    storage = AzureBlobStorage()
    
    print(f"📁 Testing bulk upload to project: {project_id}")
    
    results = []
    for file_path, content in test_files:
        print(f"📤 Uploading {file_path} ({len(content)} chars)...")
        
        try:
            success = storage.upload_file(project_id, file_path, content)
            results.append((file_path, success, len(content)))
            
            if success:
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed")
                
        except Exception as e:
            print(f"  💥 Exception: {e}")
            results.append((file_path, False, len(content)))
    
    # Summary
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\n📊 Bulk upload results: {successful}/{total} successful")
    
    if successful == total:
        print("✅ All uploads successful - Azure is working fine")
        
        # Clean up
        for file_path, _, _ in results:
            storage.delete_file(project_id, file_path)
        print("🗑️ Test files cleaned up")
        
    else:
        print("❌ Some uploads failed - this matches the horizon-543-56f69 issue")
        
    return successful == total


def check_azure_limits_and_constraints():
    """Check for Azure limits that might cause upload failures"""
    print("\n🔍 Checking Azure limits and constraints...")
    
    storage = AzureBlobStorage()
    
    # Test large file upload (Azure has a 4.75 TB limit, but let's test reasonable sizes)
    large_content = "x" * (1024 * 1024)  # 1MB file
    project_id = "limit-test-" + datetime.now().strftime("%H%M%S")
    
    print(f"📤 Testing 1MB file upload...")
    success = storage.upload_file(project_id, "large_test.txt", large_content)
    
    if success:
        print("✅ Large file upload successful")
        storage.delete_file(project_id, "large_test.txt")
    else:
        print("❌ Large file upload failed - size limit issue?")
    
    # Test rapid successive uploads (rate limiting?)
    print(f"📤 Testing rapid successive uploads...")
    rapid_success = 0
    for i in range(5):
        success = storage.upload_file(project_id, f"rapid_{i}.txt", f"content_{i}")
        if success:
            rapid_success += 1
            storage.delete_file(project_id, f"rapid_{i}.txt")
    
    print(f"✅ Rapid uploads: {rapid_success}/5 successful")
    
    if rapid_success < 5:
        print("⚠️  Rate limiting might be an issue")
    
    return success and rapid_success == 5


def analyze_horizon_project_state():
    """Analyze the actual horizon-543-56f69 project state"""
    print("\n🔍 Analyzing actual horizon-543-56f69 project state...")
    
    project_id = "horizon-543-56f69"
    storage = AzureBlobStorage()
    
    # Get list of existing files
    existing_files = storage.list_files(project_id)
    print(f"📂 Found {len(existing_files)} existing files")
    
    # Check if we can upload to this project
    test_file = "debug_upload_test.txt"
    test_content = f"Debug test at {datetime.now().isoformat()}"
    
    print(f"📤 Testing upload to existing project...")
    upload_success = storage.upload_file(project_id, test_file, test_content)
    
    if upload_success:
        print("✅ Upload to existing project successful")
        
        # Download to verify
        downloaded = storage.download_file(project_id, test_file)
        if downloaded == test_content:
            print("✅ Download verification successful")
            storage.delete_file(project_id, test_file)
        else:
            print("❌ Download verification failed")
    else:
        print("❌ Upload to existing project failed")
        print("🤔 This suggests the project might have permission issues")
    
    return upload_success


if __name__ == "__main__":
    print("🚀 Debugging Azure Upload Failures")
    print("=" * 50)
    
    # Run all tests
    connection_ok = test_azure_connection()
    bulk_ok = test_bulk_upload_simulation() if connection_ok else False
    limits_ok = check_azure_limits_and_constraints() if connection_ok else False
    project_ok = analyze_horizon_project_state() if connection_ok else False
    
    print("\n📊 Debug Summary:")
    print(f"   Basic connection: {'✅' if connection_ok else '❌'}")
    print(f"   Bulk upload test: {'✅' if bulk_ok else '❌'}")
    print(f"   Azure limits test: {'✅' if limits_ok else '❌'}")
    print(f"   Project state test: {'✅' if project_ok else '❌'}")
    
    if all([connection_ok, bulk_ok, limits_ok, project_ok]):
        print("\n🤔 All tests pass - the failure might have been:")
        print("   1. Temporary network issue during bulk upload")
        print("   2. Azure service outage at the time")
        print("   3. Memory/resource constraints during processing")
        print("   4. Race condition in bulk processing")
    else:
        print("\n🚨 Found issues that could explain the original failure")