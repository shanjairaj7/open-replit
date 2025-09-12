"""
Starter Kit Manager
Manages adding starter kits to projects from Azure Storage templates
"""

from typing import Dict, List, Optional
from cloud_storage import AzureBlobStorage
import os

class StarterKitManager:
    """Manages starter kit operations"""
    
    def __init__(self, cloud_storage: AzureBlobStorage):
        self.cloud_storage = cloud_storage
        
        # Available starter kits with their metadata
        self.available_kits = {
            "stripe": {
                "name": "Stripe Payment Integration",
                "description": "Complete Stripe payment and subscription system with payment links",
                "target": "backend",  # backend or frontend
                "folder_name": "stripe_kit"
            }
        }
    
    def list_available_kits(self) -> Dict[str, Dict]:
        """List all available starter kits"""
        return self.available_kits
    
    def get_kit_info(self, kit_name: str) -> Optional[Dict]:
        """Get information about a specific starter kit"""
        return self.available_kits.get(kit_name)
    
    def add_starter_kit(self, project_id: str, kit_name: str, target: str = None) -> Dict:
        """
        Add a starter kit to a project
        
        Args:
            project_id: The project ID to add the kit to
            kit_name: Name of the starter kit (e.g., 'stripe')
            target: 'backend' or 'frontend' (optional, will use kit default)
        
        Returns:
            Dict with success status, message, and details
        """
        print(f"🛠️ Adding starter kit '{kit_name}' to project '{project_id}'")
        
        # Validate kit exists
        if kit_name not in self.available_kits:
            return {
                "success": False,
                "error": f"Starter kit '{kit_name}' not found",
                "available_kits": list(self.available_kits.keys())
            }
        
        kit_info = self.available_kits[kit_name]
        
        # Determine target (backend/frontend)
        if target is None:
            target = kit_info.get("target", "backend")
        
        if target not in ["backend", "frontend"]:
            return {
                "success": False,
                "error": f"Invalid target '{target}'. Must be 'backend' or 'frontend'"
            }
        
        folder_name = kit_info.get("folder_name", f"{kit_name}_kit")
        
        print(f"📍 Target: {target}")
        print(f"📁 Folder: {folder_name}")
        
        try:
            # Check if kit already exists in project
            existing_files = self.cloud_storage.list_files(project_id, f"{target}/{folder_name}/")
            
            if existing_files:
                return {
                    "success": False,
                    "error": f"Starter kit '{kit_name}' already exists in {target}/{folder_name}",
                    "existing_files": len(existing_files)
                }
            
            # Get starter kit template files from Azure
            template_files = self.cloud_storage.list_files("templates", f"starter-kits/{kit_name}/")
            
            if not template_files:
                return {
                    "success": False,
                    "error": f"Starter kit template '{kit_name}' not found in Azure Storage",
                    "message": "Template may not be uploaded yet"
                }
            
            print(f"📦 Found {len(template_files)} template files")
            
            # Copy all template files to project
            copied_files = 0
            failed_files = 0
            
            for template_file in template_files:
                # Download template file content (template_file already includes the starter-kits/stripe/ prefix)
                template_content = self.cloud_storage.download_file("templates", template_file)
                
                if template_content is None:
                    print(f"  ❌ Failed to download template: {template_file}")
                    failed_files += 1
                    continue
                
                # Extract just the filename from the full template path
                filename = template_file.split('/')[-1]  # Get just the filename part
                
                # Upload to project with proper path (using just filename)
                project_file_path = f"{target}/{folder_name}/{filename}"
                
                if self.cloud_storage.upload_file(project_id, project_file_path, template_content, is_new_file=True):
                    print(f"  ✅ Copied: {filename}")
                    copied_files += 1
                else:
                    print(f"  ❌ Failed to copy: {filename}")
                    failed_files += 1
            
            # Prepare result
            if copied_files > 0:
                result = {
                    "success": True,
                    "kit_name": kit_name,
                    "target": target,
                    "folder_name": folder_name,
                    "copied_files": copied_files,
                    "failed_files": failed_files,
                    "message": f"Successfully added {kit_name} starter kit to {target}/{folder_name}",
                    "next_steps": self._get_kit_next_steps(kit_name)
                }
                
                print(f"🎉 Starter kit '{kit_name}' added successfully!")
                print(f"📊 Files: {copied_files} copied, {failed_files} failed")
                
                return result
            else:
                return {
                    "success": False,
                    "error": f"No files were copied successfully",
                    "failed_files": failed_files
                }
            
        except Exception as e:
            print(f"❌ Error adding starter kit: {e}")
            return {
                "success": False,
                "error": f"Exception while adding starter kit: {str(e)}"
            }
    
    def _get_kit_next_steps(self, kit_name: str) -> List[str]:
        """Get next steps instructions for a specific kit"""
        if kit_name == "stripe":
            return [
                "Add STRIPE_SECRET_KEY to Dashboard → Backend → Keys",
                "Add STRIPE_PUBLISHABLE_KEY to Dashboard → Backend → Keys", 
                "Read the README.md in the stripe_kit folder for customization options",
                "The kit automatically creates database tables and API routes",
                "Use /stripe/create-payment-link endpoint in your frontend"
            ]
        
        return [
            f"Check the documentation in the {kit_name}_kit folder",
            "Configure any required environment variables",
            "Follow the setup instructions in the README"
        ]

# Global starter kit manager instance
_starter_kit_manager = None

def get_starter_kit_manager(cloud_storage: AzureBlobStorage) -> StarterKitManager:
    """Get or create the global starter kit manager instance"""
    global _starter_kit_manager
    if _starter_kit_manager is None:
        _starter_kit_manager = StarterKitManager(cloud_storage)
    return _starter_kit_manager

def test_starter_kit_functions():
    """Test starter kit functions"""
    print("🧪 Testing Starter Kit Functions...")
    
    try:
        from cloud_storage import get_cloud_storage
        storage = get_cloud_storage()
        
        if not storage:
            print("❌ Could not initialize cloud storage")
            return False
        
        manager = get_starter_kit_manager(storage)
        
        # Test listing available kits
        kits = manager.list_available_kits()
        print(f"📦 Available kits: {list(kits.keys())}")
        
        # Test kit info
        stripe_info = manager.get_kit_info("stripe")
        print(f"🔍 Stripe kit info: {stripe_info}")
        
        print("✅ Basic starter kit functions work!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_starter_kit_functions()