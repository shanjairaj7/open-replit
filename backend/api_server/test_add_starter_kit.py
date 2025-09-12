#!/usr/bin/env python3
"""
Test script to verify add_starter_kit functionality
"""

from starter_kits import get_starter_kit_manager
from cloud_storage import get_cloud_storage

def test_add_starter_kit():
    """Test adding a starter kit to a test project"""
    
    print("🧪 Testing Add Starter Kit Functionality...")
    
    # Initialize storage and manager
    storage = get_cloud_storage()
    if not storage:
        print("❌ Could not initialize cloud storage")
        return False
    
    manager = get_starter_kit_manager(storage)
    
    # Test project ID
    test_project_id = "test-project-starterkit"
    
    print(f"🎯 Testing with project ID: {test_project_id}")
    
    # Test adding stripe kit
    result = manager.add_starter_kit(
        project_id=test_project_id,
        kit_name="stripe",
        target="backend"
    )
    
    print(f"\n📊 Result:")
    print(f"Success: {result.get('success')}")
    print(f"Message: {result.get('message', result.get('error'))}")
    
    if result.get('success'):
        print(f"Files copied: {result.get('copied_files')}")
        print(f"Files failed: {result.get('failed_files')}")
        print(f"Target location: {result.get('target')}/{result.get('folder_name')}")
        
        print(f"\n📋 Next Steps:")
        for i, step in enumerate(result.get('next_steps', []), 1):
            print(f"  {i}. {step}")
        
        # Verify files were actually added
        print(f"\n🔍 Verifying files were added...")
        project_files = storage.list_files(test_project_id, "backend/stripe_kit/")
        print(f"Found {len(project_files)} files in backend/stripe_kit/:")
        for file in sorted(project_files[:5]):  # Show first 5 files
            print(f"  - {file}")
        
        if len(project_files) > 5:
            print(f"  ... and {len(project_files) - 5} more")
        
        return True
    else:
        print(f"❌ Adding starter kit failed")
        return False

if __name__ == "__main__":
    success = test_add_starter_kit()
    
    if success:
        print("\n✅ Add starter kit test completed successfully!")
    else:
        print("\n❌ Add starter kit test failed!")
    
    exit(0 if success else 1)