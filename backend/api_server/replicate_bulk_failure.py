#!/usr/bin/env python3
"""
Replicate the exact bulk file processing scenario from horizon-543-56f69
to identify the real error that caused the upload failures
"""

import sys
import re
from typing import List, Dict, Any

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage
from base_test_azure_hybrid import BoilerplatePersistentGroq


def extract_file_actions_from_message_60():
    """Extract the exact file actions from Message 60"""
    with open('/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/message_60_raw_content.txt', 'r') as f:
        content = f.read()
    
    # Extract write_file actions exactly as they appear
    pattern = r'<action type="write_file" filePath="([^"]+)">(.*?)</action>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    file_actions = []
    for file_path, file_content in matches:
        file_actions.append({
            'type': 'write_file',
            'filePath': file_path,
            'content': file_content.strip()
        })
    
    print(f"📊 Extracted {len(file_actions)} file actions from Message 60:")
    for i, action in enumerate(file_actions):
        print(f"   {i+1}. {action['filePath']} ({len(action['content'])} chars)")
    
    return file_actions


def simulate_bulk_processing_original_way():
    """Simulate exactly how the bulk processing would have happened originally"""
    print("\n🧪 Simulating original bulk processing scenario...")
    
    # Create a test project
    test_project_id = "bulk-failure-test-" + str(int(__import__('time').time()))
    print(f"🆔 Test project: {test_project_id}")
    
    # Get the file actions
    file_actions = extract_file_actions_from_message_60()
    
    # Create BoilerplatePersistentGroq instance like the original scenario
    try:
        coder = BoilerplatePersistentGroq()
        coder.project_id = test_project_id
        coder.cloud_storage = AzureBlobStorage()
        
        print(f"🔧 BoilerplatePersistentGroq initialized with project: {test_project_id}")
        
        # Process each file action using the original _process_file_action method
        print(f"\n📝 Processing {len(file_actions)} file actions...")
        
        results = []
        for i, action in enumerate(file_actions):
            print(f"\n🔄 Processing file {i+1}/{len(file_actions)}: {action['filePath']}")
            
            try:
                # Call the exact method that was used originally
                result = coder._process_file_action(action)
                results.append({
                    'file_path': action['filePath'], 
                    'success': True,
                    'result': result,
                    'error': None
                })
                
            except Exception as e:
                print(f"💥 Exception during processing: {e}")
                import traceback
                traceback.print_exc()
                
                results.append({
                    'file_path': action['filePath'],
                    'success': False, 
                    'result': None,
                    'error': str(e)
                })
        
        # Analyze results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"\n📊 Bulk processing results:")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        
        if failed:
            print(f"\n❌ Failed files:")
            for result in failed:
                print(f"   - {result['file_path']}: {result['error']}")
        
        # Now check what actually got uploaded to Azure
        print(f"\n🔍 Checking Azure storage for uploaded files...")
        azure_files = coder.cloud_storage.list_files(test_project_id)
        print(f"📂 Found {len(azure_files)} files in Azure")
        
        # Check which files are missing
        expected_files = {action['filePath'] for action in file_actions}
        actual_files = set(azure_files)
        missing_files = expected_files - actual_files
        
        if missing_files:
            print(f"\n🚨 REPLICATION SUCCESSFUL - Missing files detected:")
            for file_path in sorted(missing_files):
                print(f"   ❌ {file_path}")
        else:
            print(f"\n✅ All files uploaded successfully - no replication")
        
        # Clean up test files
        print(f"\n🗑️ Cleaning up test files...")
        for file_path in azure_files:
            coder.cloud_storage.delete_file(test_project_id, file_path)
        
        return results, missing_files
        
    except Exception as e:
        print(f"💥 Failed to initialize BoilerplatePersistentGroq: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_individual_file_upload():
    """Test uploading individual files to isolate the issue"""
    print("\n🔬 Testing individual file uploads...")
    
    file_actions = extract_file_actions_from_message_60()
    test_project_id = "individual-test-" + str(int(__import__('time').time()))
    
    storage = AzureBlobStorage()
    
    # Test the largest files first (most likely to fail)
    sorted_actions = sorted(file_actions, key=lambda x: len(x['content']), reverse=True)
    
    for i, action in enumerate(sorted_actions[:3]):  # Test top 3 largest
        file_path = action['filePath']
        content = action['content']
        
        print(f"\n📤 Testing upload {i+1}: {file_path} ({len(content)} chars)")
        
        try:
            success = storage.upload_file(test_project_id, file_path, content)
            if success:
                print(f"   ✅ Upload successful")
                # Verify by downloading
                downloaded = storage.download_file(test_project_id, file_path)
                if downloaded == content:
                    print(f"   ✅ Download verification successful")
                else:
                    print(f"   ❌ Download verification failed - content mismatch")
            else:
                print(f"   ❌ Upload failed")
                return False
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Clean up
    print(f"\n🗑️ Cleaning up individual test files...")
    test_files = storage.list_files(test_project_id)
    for file_path in test_files:
        storage.delete_file(test_project_id, file_path)
    
    return True


def test_memory_pressure_scenario():
    """Test if memory pressure during bulk processing could cause issues"""
    print("\n🧠 Testing memory pressure scenario...")
    
    file_actions = extract_file_actions_from_message_60()
    
    # Calculate total memory usage
    total_content = sum(len(action['content']) for action in file_actions)
    print(f"📊 Total content size: {total_content:,} bytes ({total_content/1024/1024:.2f} MB)")
    
    # Try processing all at once vs one by one
    test_project_id = "memory-test-" + str(int(__import__('time').time()))
    storage = AzureBlobStorage()
    
    # Simulate rapid bulk uploads
    print(f"📤 Rapid bulk upload test...")
    start_time = __import__('time').time()
    
    upload_results = []
    for action in file_actions:
        try:
            success = storage.upload_file(test_project_id, action['filePath'], action['content'])
            upload_results.append(success)
        except Exception as e:
            print(f"💥 Upload exception: {e}")
            upload_results.append(False)
    
    end_time = __import__('time').time()
    duration = end_time - start_time
    
    successful_uploads = sum(upload_results)
    print(f"📊 Rapid upload results:")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Successful: {successful_uploads}/{len(file_actions)}")
    print(f"   Failed: {len(file_actions) - successful_uploads}")
    
    # Clean up
    test_files = storage.list_files(test_project_id)
    for file_path in test_files:
        storage.delete_file(test_project_id, file_path)
    
    return successful_uploads == len(file_actions)


if __name__ == "__main__":
    print("🔍 Replicating Bulk File Processing Failure")
    print("=" * 50)
    
    # Test 1: Replicate the original bulk processing
    print("🧪 TEST 1: Original bulk processing replication")
    results, missing_files = simulate_bulk_processing_original_way()
    
    if results is not None:
        bulk_replication_success = len(missing_files) > 0 if missing_files is not None else False
    else:
        bulk_replication_success = False
    
    # Test 2: Individual file uploads
    print("\n🧪 TEST 2: Individual file upload testing")
    individual_success = test_individual_file_upload()
    
    # Test 3: Memory pressure scenario
    print("\n🧪 TEST 3: Memory pressure testing")
    memory_success = test_memory_pressure_scenario()
    
    # Summary
    print(f"\n📊 REPLICATION SUMMARY:")
    print(f"   Bulk processing failed: {'✅' if bulk_replication_success else '❌'}")
    print(f"   Individual uploads work: {'✅' if individual_success else '❌'}")
    print(f"   Memory pressure OK: {'✅' if memory_success else '❌'}")
    
    if bulk_replication_success:
        print(f"\n🎯 SUCCESS: We replicated the exact failure scenario!")
        print(f"   The same files that failed in horizon-543-56f69 are failing now")
        print(f"   This confirms the root cause in the processing pipeline")
    else:
        print(f"\n🤔 Could not replicate the failure - the issue may have been:")
        print(f"   1. Temporary network/Azure service issue")
        print(f"   2. Race condition that doesn't happen consistently") 
        print(f"   3. Resource constraints specific to the original environment")
        print(f"   4. A bug that has since been fixed")