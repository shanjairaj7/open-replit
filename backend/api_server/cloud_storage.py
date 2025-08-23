"""
Azure Blob Storage integration for project file management.
Handles all file operations in the cloud for the codebase platform.
"""

import os
import json
import tempfile
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

class AzureBlobStorage:
    """Azure Blob Storage client for project file management"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client with environment variables"""
        
        # Hardcoded Azure Storage credentials for testing
        hardcoded_connection_string = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;BlobEndpoint=https://functionalaistorage.blob.core.windows.net/;FileEndpoint=https://functionalaistorage.file.core.windows.net/;QueueEndpoint=https://functionalaistorage.queue.core.windows.net/;TableEndpoint=https://functionalaistorage.table.core.windows.net/"
        
        # Try environment variable first, fall back to hardcoded
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING', hardcoded_connection_string)
        
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'codebase-projects')
        self.container_client = self.blob_service_client.get_container_client(self.container_name)
        
        # Ensure container exists
        try:
            self.container_client.get_container_properties()
        except ResourceNotFoundError:
            print(f"🔧 Creating Azure container: {self.container_name}")
            self.container_client.create_container()
    
    def _get_blob_path(self, project_id: str, file_path: str) -> str:
        """Convert project file path to Azure blob path"""
        # Normalize path separators for consistency
        file_path = file_path.replace('\\', '/')
        return f"{project_id}/{file_path}"
    
    def upload_file(self, project_id: str, file_path: str, content: str) -> bool:
        """Upload file content to Azure Blob Storage"""
        try:
            blob_path = self._get_blob_path(project_id, file_path)
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Upload with UTF-8 encoding
            from azure.storage.blob import ContentSettings
            blob_client.upload_blob(
                content.encode('utf-8'), 
                overwrite=True,
                content_settings=ContentSettings(content_type='text/plain; charset=utf-8')
            )
            
            print(f"☁️ Uploaded: {blob_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to upload {file_path}: {str(e)}")
            return False
    
    def download_file(self, project_id: str, file_path: str) -> Optional[str]:
        """Download file content from Azure Blob Storage"""
        try:
            blob_path = self._get_blob_path(project_id, file_path)
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Download as text with UTF-8 decoding
            blob_data = blob_client.download_blob()
            content = blob_data.readall().decode('utf-8')
            
            print(f"📖 Read from cloud: {blob_path}")
            return content
            
        except ResourceNotFoundError:
            print(f"📄 File not found: {file_path}")
            return None
        except Exception as e:
            print(f"❌ Failed to download {file_path}: {str(e)}")
            return None
    
    def delete_file(self, project_id: str, file_path: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            blob_path = self._get_blob_path(project_id, file_path)
            blob_client = self.container_client.get_blob_client(blob_path)
            
            blob_client.delete_blob()
            
            print(f"🗑️ Deleted: {blob_path}")
            return True
            
        except ResourceNotFoundError:
            print(f"📄 File not found for deletion: {file_path}")
            return False
        except Exception as e:
            print(f"❌ Failed to delete {file_path}: {str(e)}")
            return False
    
    def list_files(self, project_id: str, prefix: str = "") -> List[str]:
        """List files in project directory with optional prefix filter"""
        try:
            blob_prefix = f"{project_id}/"
            if prefix:
                blob_prefix += prefix
            
            blobs = self.container_client.list_blobs(name_starts_with=blob_prefix)
            
            file_paths = []
            for blob in blobs:
                # Remove project_id prefix to get relative path
                relative_path = blob.name[len(f"{project_id}/"):]
                file_paths.append(relative_path)
            
            print(f"📂 Found {len(file_paths)} files in {project_id}/{prefix}")
            return sorted(file_paths)
            
        except Exception as e:
            print(f"❌ Failed to list files: {str(e)}")
            return []
    
    def file_exists(self, project_id: str, file_path: str) -> bool:
        """Check if file exists in Azure Blob Storage"""
        try:
            blob_path = self._get_blob_path(project_id, file_path)
            blob_client = self.container_client.get_blob_client(blob_path)
            
            blob_client.get_blob_properties()
            return True
            
        except ResourceNotFoundError:
            return False
        except Exception as e:
            print(f"❌ Failed to check file existence {file_path}: {str(e)}")
            return False
    
    def clone_from_github(self, project_id: str, repo_url: str, target_dir: str) -> bool:
        """Clone GitHub repository and upload files to Azure storage"""
        try:
            print(f"📡 Cloning {repo_url} to {project_id}/{target_dir}")
            
            # Create temporary directory for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                clone_path = Path(temp_dir) / "repo"
                
                # Clone repository
                result = subprocess.run([
                    'git', 'clone', repo_url, str(clone_path)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    print(f"❌ Git clone failed: {result.stderr}")
                    return False
                
                # Upload all files from cloned repo
                uploaded_files = 0
                skipped_files = 0
                
                for file_path in clone_path.rglob('*'):
                    if file_path.is_file():
                        # Skip git directory and other system files
                        relative_path = file_path.relative_to(clone_path)
                        relative_str = str(relative_path).replace('\\', '/')
                        
                        if self._should_skip_file(relative_str):
                            skipped_files += 1
                            continue
                        
                        try:
                            # Read file content
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            # Upload to target directory in project
                            target_file_path = f"{target_dir}/{relative_str}"
                            
                            if self.upload_file(project_id, target_file_path, content):
                                uploaded_files += 1
                            
                        except Exception as e:
                            print(f"⚠️ Failed to upload {relative_str}: {str(e)}")
                            skipped_files += 1
                
                print(f"✅ GitHub clone complete: {uploaded_files} files uploaded, {skipped_files} skipped")
                return uploaded_files > 0
                
        except Exception as e:
            print(f"❌ Failed to clone from GitHub: {str(e)}")
            return False
    
    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped during GitHub clone"""
        skip_patterns = [
            '.git/', '__pycache__/', 'node_modules/', '.vscode/', '.idea/',
            'dist/', 'build/', '.next/', '.cache/', 'coverage/', '.nyc_output/',
            'venv/', 'env/', '.env', '.DS_Store', '*.log', '*.tmp'
        ]
        
        file_path_lower = file_path.lower()
        
        for pattern in skip_patterns:
            if pattern.endswith('/') and f"/{pattern}" in f"/{file_path_lower}":
                return True
            elif pattern.startswith('*.') and file_path_lower.endswith(pattern[1:]):
                return True
            elif pattern in file_path_lower:
                return True
        
        return False
    
    def save_conversation_history(self, project_id: str, conversation_history: List[Dict]) -> bool:
        """Save conversation history to cloud storage"""
        try:
            conversation_data = {
                "project_id": project_id,
                "conversation_history": conversation_history,
                "last_updated": datetime.utcnow().isoformat(),
                "message_count": len(conversation_history)
            }
            
            content = json.dumps(conversation_data, indent=2, ensure_ascii=False)
            return self.upload_file(project_id, "conversation_history.json", content)
            
        except Exception as e:
            print(f"❌ Failed to save conversation history: {str(e)}")
            return False
    
    def load_conversation_history(self, project_id: str) -> List[Dict]:
        """Load conversation history from cloud storage"""
        try:
            content = self.download_file(project_id, "conversation_history.json")
            if content:
                data = json.loads(content)
                return data.get("conversation_history", [])
            return []
            
        except Exception as e:
            print(f"❌ Failed to load conversation history: {str(e)}")
            return []
    
    def save_project_metadata(self, project_id: str, metadata: Dict) -> bool:
        """Save project metadata to cloud storage"""
        try:
            metadata_with_timestamp = {
                **metadata,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            content = json.dumps(metadata_with_timestamp, indent=2, ensure_ascii=False)
            return self.upload_file(project_id, "project_metadata.json", content)
            
        except Exception as e:
            print(f"❌ Failed to save project metadata: {str(e)}")
            return False
    
    def load_project_metadata(self, project_id: str) -> Optional[Dict]:
        """Load project metadata from cloud storage"""
        try:
            content = self.download_file(project_id, "project_metadata.json")
            if content:
                return json.loads(content)
            return None
            
        except Exception as e:
            print(f"❌ Failed to load project metadata: {str(e)}")
            return None
    
    def save_conversation_history_streaming(self, project_id: str, streaming_chunks: List[Dict]) -> bool:
        """Save conversation history in streaming format (exact chunks sent to frontend)"""
        try:
            streaming_conversation_data = {
                "project_id": project_id,
                "conversation_streaming_chunks": streaming_chunks,
                "last_updated": datetime.utcnow().isoformat(),
                "streaming_chunks_count": len(streaming_chunks),
                "format": "frontend_streaming_chunks"
            }
            
            content = json.dumps(streaming_conversation_data, indent=2, ensure_ascii=False)
            return self.upload_file(project_id, "conversation_history_streaming.json", content)
            
        except Exception as e:
            print(f"❌ Failed to save streaming conversation history: {str(e)}")
            return False
    
    def load_conversation_history_streaming(self, project_id: str) -> List[Dict]:
        """Load conversation history in streaming format from cloud storage"""
        try:
            content = self.download_file(project_id, "conversation_history_streaming.json")
            if content:
                data = json.loads(content)
                return data.get("conversation_streaming_chunks", [])
            return []
            
        except Exception as e:
            print(f"❌ Failed to load streaming conversation history: {str(e)}")
            return []
    
    def append_streaming_chunk(self, project_id: str, chunk: Dict) -> bool:
        """Append a single streaming chunk to the conversation history streaming format"""
        try:
            # Load existing streaming conversation history
            existing_chunks = self.load_conversation_history_streaming(project_id)
            
            # Append new streaming chunk
            existing_chunks.append(chunk)
            
            # Save updated streaming conversation history
            return self.save_conversation_history_streaming(project_id, existing_chunks)
            
        except Exception as e:
            print(f"❌ Failed to append streaming chunk to conversation history: {str(e)}")
            return False
    
    def save_read_files_tracking(self, project_id: str, read_files_set: set) -> bool:
        """Save read files tracking to cloud storage"""
        try:
            tracking_data = {
                "project_id": project_id,
                "read_files": list(read_files_set),
                "last_updated": datetime.utcnow().isoformat(),
                "file_count": len(read_files_set)
            }
            
            content = json.dumps(tracking_data, indent=2, ensure_ascii=False)
            return self.upload_file(project_id, "read_files_tracking.json", content)
            
        except Exception as e:
            print(f"❌ Failed to save read files tracking: {str(e)}")
            return False
    
    def load_read_files_tracking(self, project_id: str) -> set:
        """Load read files tracking from cloud storage"""
        try:
            content = self.download_file(project_id, "read_files_tracking.json")
            if content:
                data = json.loads(content)
                return set(data.get("read_files", []))
            return set()
            
        except Exception as e:
            print(f"❌ Failed to load read files tracking: {str(e)}")
            return set()
    
    def get_project_structure(self, project_id: str) -> Dict:
        """Get complete project structure from cloud storage"""
        try:
            files = self.list_files(project_id)
            
            structure = {
                "project_id": project_id,
                "total_files": len(files),
                "frontend_files": [f for f in files if f.startswith('frontend/')],
                "backend_files": [f for f in files if f.startswith('backend/')],
                "config_files": [f for f in files if f.endswith('.json')],
                "all_files": files
            }
            
            return structure
            
        except Exception as e:
            print(f"❌ Failed to get project structure: {str(e)}")
            return {"error": str(e)}

# Global instance for easy access (lazy initialization)
cloud_storage = None

def get_cloud_storage():
    """Get or create the global cloud storage instance"""
    global cloud_storage
    if cloud_storage is None:
        try:
            cloud_storage = AzureBlobStorage()
        except Exception as e:
            print(f"⚠️ Could not initialize global cloud storage: {e}")
            return None
    return cloud_storage

# Test functions
def test_cloud_storage():
    """Test cloud storage functionality"""
    print("🧪 Testing Azure Blob Storage...")
    
    test_project_id = "test-project-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    test_content = "# Test File\n\nThis is a test file for Azure Blob Storage integration."
    
    # Test upload
    success = cloud_storage.upload_file(test_project_id, "README.md", test_content)
    if not success:
        print("❌ Upload test failed")
        return False
    
    # Test download
    downloaded_content = cloud_storage.download_file(test_project_id, "README.md")
    if downloaded_content != test_content:
        print("❌ Download test failed")
        return False
    
    # Test file exists
    if not cloud_storage.file_exists(test_project_id, "README.md"):
        print("❌ File exists test failed")
        return False
    
    # Test list files
    files = cloud_storage.list_files(test_project_id)
    if "README.md" not in files:
        print("❌ List files test failed")
        return False
    
    # Test delete
    if not cloud_storage.delete_file(test_project_id, "README.md"):
        print("❌ Delete test failed")
        return False
    
    print("✅ All cloud storage tests passed!")
    return True

if __name__ == "__main__":
    test_cloud_storage()