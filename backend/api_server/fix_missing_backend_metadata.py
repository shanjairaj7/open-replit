#!/usr/bin/env python3
"""
Fix missing backend deployment metadata for projects that got corrupted
"""

import sys
sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')

from cloud_storage import get_cloud_storage
from datetime import datetime

def fix_backend_metadata():
    """Restore missing backend deployment metadata"""
    
    project_id = "horizon-541-0f2e2"
    backend_url = "https://shanjairajdev--horizon-541-0f2e2-backend-fastapi-app.modal.run"
    app_name = "horizon-541-0f2e2-backend"
    secret_name = "horizon-541-0f2e2-backend-secrets"
    
    print(f"🔧 Fixing backend metadata for: {project_id}")
    print(f"🌐 Backend URL: {backend_url}")
    
    cloud_storage = get_cloud_storage()
    if not cloud_storage:
        print("❌ Cloud storage not available")
        return
    
    try:
        # Load existing metadata
        existing_metadata = cloud_storage.load_project_metadata(project_id) or {}
        print(f"📖 Loaded existing metadata with keys: {list(existing_metadata.keys())}")
        
        # Add the missing backend deployment info
        backend_deployment_info = {
            "backend_deployment": {
                "status": "deployed",
                "url": backend_url,
                "docs_url": f"{backend_url}/docs",
                "app_name": app_name,
                "secret_name": secret_name,
                "secret_keys": ["SECRET_KEY", "DATABASE_NAME", "APP_TITLE", "APP_DESCRIPTION"],
                "deployed_at": datetime.now().isoformat(),
                "last_deployment": datetime.now().isoformat()
            }
        }
        
        # Merge with existing metadata
        updated_metadata = {**existing_metadata, **backend_deployment_info}
        
        print(f"🔄 Adding backend deployment info...")
        
        # Save the updated metadata
        success = cloud_storage.save_project_metadata(project_id, updated_metadata)
        
        if success:
            print(f"✅ Successfully restored backend deployment metadata!")
            
            # Test the fix
            print(f"🧪 Testing the fix...")
            from base_test_azure_hybrid import BoilerplatePersistentGroq
            
            test_groq = BoilerplatePersistentGroq(project_id=project_id, project_name="test")
            backend_info = test_groq._get_backend_deployment_info()
            
            print(f"📊 Test result:")
            print(f"   Status: {backend_info.get('status')}")
            print(f"   URL: {backend_info.get('url')}")
            
            if backend_info.get('status') == 'success' and backend_info.get('url'):
                print(f"🎉 SUCCESS! Backend deployment info is now correctly detected!")
            else:
                print(f"❌ Fix didn't work: {backend_info}")
        else:
            print(f"❌ Failed to save metadata")
            
    except Exception as e:
        print(f"💥 Error fixing metadata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_backend_metadata()