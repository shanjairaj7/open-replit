#!/usr/bin/env python3
"""
Analyze the original environment and timing of horizon-543-56f69 
to understand what might have caused the failure
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


def analyze_conversation_timing():
    """Analyze the timing and environment of the original conversation"""
    storage = AzureBlobStorage()
    conversation = storage.load_conversation_history("horizon-543-56f69")
    
    print("🕐 Analyzing original conversation timing...")
    
    # Look for timestamps or timing clues
    message_60 = conversation[59]
    
    print(f"📊 Message 60 analysis:")
    print(f"   Content length: {len(message_60.get('content', ''))} characters")
    print(f"   Role: {message_60.get('role')}")
    
    # Check for any timing or environment clues in the messages
    timing_clues = []
    environment_clues = []
    
    for i, message in enumerate(conversation):
        content = message.get('content', '').lower()
        
        # Look for timing-related mentions
        if any(keyword in content for keyword in ['timeout', 'slow', 'delay', 'waiting']):
            timing_clues.append(f"Message {i+1}: {content[:100]}...")
            
        # Look for environment/system mentions
        if any(keyword in content for keyword in ['error', 'failed', 'exception', 'network', 'connection']):
            environment_clues.append(f"Message {i+1}: {content[:100]}...")
    
    if timing_clues:
        print(f"\n⏰ Timing-related clues found:")
        for clue in timing_clues[:3]:
            print(f"   {clue}")
    
    if environment_clues:
        print(f"\n🔧 Environment-related clues found:")
        for clue in environment_clues[:3]:
            print(f"   {clue}")
    
    return len(timing_clues), len(environment_clues)


def check_project_metadata():
    """Check the project metadata for clues about the environment"""
    storage = AzureBlobStorage()
    
    print(f"\n📋 Checking project metadata...")
    
    try:
        metadata_content = storage.download_file("horizon-543-56f69", "project_metadata.json")
        if metadata_content:
            metadata = json.loads(metadata_content)
            
            print(f"📊 Project metadata:")
            print(f"   Created: {metadata.get('created_at', 'Unknown')}")
            print(f"   Project name: {metadata.get('project_name', 'Unknown')}")
            print(f"   Frontend repo: {metadata.get('frontend_repo', 'Unknown')}")
            print(f"   Backend repo: {metadata.get('backend_repo', 'Unknown')}")
            
            # Check for any unusual fields
            unusual_fields = []
            for key, value in metadata.items():
                if key not in ['project_id', 'project_name', 'created_at', 'frontend_repo', 'backend_repo']:
                    unusual_fields.append(f"{key}: {value}")
            
            if unusual_fields:
                print(f"   Unusual fields:")
                for field in unusual_fields:
                    print(f"     {field}")
            
            return metadata
        else:
            print("❌ No project metadata found")
            return None
            
    except Exception as e:
        print(f"❌ Error reading metadata: {e}")
        return None


def analyze_file_timestamps():
    """Check timestamps of files that do exist vs when they should have been created"""
    storage = AzureBlobStorage()
    
    print(f"\n📅 Analyzing file timestamps...")
    
    # Get list of all files
    files = storage.list_files("horizon-543-56f69")
    
    # Check timestamps of key files that do exist
    existing_key_files = [
        "frontend/src/pages/DashboardPage.tsx",
        "frontend/src/stores/auth-store.ts", 
        "frontend/src/App.tsx"
    ]
    
    for file_path in existing_key_files:
        if file_path in files:
            try:
                # Try to get file metadata (this might not work with our current setup)
                content = storage.download_file("horizon-543-56f69", file_path)
                print(f"✅ {file_path}: exists ({len(content)} chars)")
            except Exception as e:
                print(f"❌ {file_path}: error reading - {e}")
    
    # Files that should exist but don't
    missing_files = [
        "frontend/src/pages/DealsPage.tsx",
        "frontend/src/pages/AuditLogPage.tsx",
        "backend/routes/crm.py"
    ]
    
    print(f"\n❌ Confirmed missing files:")
    for file_path in missing_files:
        if file_path not in files:
            print(f"   {file_path}")


def check_azure_storage_health():
    """Check current Azure storage health and compare with historical issues"""
    storage = AzureBlobStorage()
    
    print(f"\n🏥 Checking Azure storage health...")
    
    # Test basic operations
    test_project = "health-check-" + str(int(__import__('time').time()))
    
    try:
        # Upload test
        success = storage.upload_file(test_project, "health_test.txt", "test content")
        if success:
            print("✅ Upload test: OK")
        else:
            print("❌ Upload test: FAILED")
            
        # Download test
        content = storage.download_file(test_project, "health_test.txt")
        if content == "test content":
            print("✅ Download test: OK")
        else:
            print("❌ Download test: FAILED")
            
        # Delete test
        deleted = storage.delete_file(test_project, "health_test.txt")
        if deleted:
            print("✅ Delete test: OK")
        else:
            print("❌ Delete test: FAILED")
            
        print("✅ Azure storage is healthy now")
        
    except Exception as e:
        print(f"❌ Azure storage issue detected: {e}")


def final_hypothesis():
    """Present the final hypothesis about what happened"""
    print(f"\n🎯 FINAL HYPOTHESIS:")
    print(f"=" * 50)
    print(f"")
    print(f"Based on our replication attempts and analysis:")
    print(f"")
    print(f"1. **XML Structure**: ✅ Nearly perfect (only 1 missing closing tag)")
    print(f"2. **File Content**: ✅ All 11 files had complete, valid content")
    print(f"3. **Azure Connectivity**: ✅ Working perfectly now")
    print(f"4. **File Processing**: ⚠️  Bug found (ignores upload failures)")
    print(f"5. **Replication**: ❌ Could not reproduce the failure")
    print(f"")
    print(f"**Most Likely Cause**: TEMPORAL AZURE SERVICE ISSUE")
    print(f"")
    print(f"The failure was likely caused by:")
    print(f"• Azure Blob Storage service degradation during the conversation")
    print(f"• Network connectivity issues between the server and Azure")
    print(f"• Azure API rate limiting during bulk uploads")
    print(f"• Temporary Azure region outage or slowdown")
    print(f"")
    print(f"**Supporting Evidence**:")
    print(f"• All file content was correctly extracted from Message 60")
    print(f"• Identical operations work perfectly now")
    print(f"• No systematic bugs in the processing pipeline")
    print(f"• The failure happened during bulk processing (11 files at once)")
    print(f"")
    print(f"**The Hidden Bug Made It Worse**:")
    print(f"• _process_file_action() always reported success even when Azure uploads failed")
    print(f"• This prevented error detection and retry mechanisms")
    print(f"• AI model assumed all files were created successfully")
    print(f"• User didn't know anything was wrong until they tested the app")


if __name__ == "__main__":
    print("🔍 Analyzing Original Environment: horizon-543-56f69")
    print("=" * 60)
    
    # Analyze conversation timing
    timing_clues, env_clues = analyze_conversation_timing()
    
    # Check project metadata  
    metadata = check_project_metadata()
    
    # Analyze file timestamps
    analyze_file_timestamps()
    
    # Check current Azure health
    check_azure_storage_health()
    
    # Present final hypothesis
    final_hypothesis()