"""
New tools implementation for the codebase platform.
Future tools go here, existing tools stay in base_test_azure_hybrid.py
"""

from typing import Dict, List, Optional, Any
from cloud_storage import AzureBlobStorage

class ToolsManager:
    def __init__(self, cloud_storage: AzureBlobStorage, project_id: str, read_files_tracker: set, read_files_persistent: set):
        print(f"==> Initializing ToolsManager for project: {project_id}")
        self.cloud_storage = cloud_storage
        self.project_id = project_id
        self.read_files_tracker = read_files_tracker
        self.read_files_persistent = read_files_persistent
        print(f"==> Read files tracker has {len(read_files_tracker)} current session files")
        print(f"==> Persistent read files has {len(read_files_persistent)} total files")
        print("==> ToolsManager ready")

    def handle_list_files(self, action: dict) -> dict:
        """Handle list_files action - lists project files with optional path filtering"""
        print(f"==> List files action triggered")
        path = action.get('path', '')
        print(f"   Path filter: '{path}' (empty = all files)")
        
        try:
            if not self.cloud_storage:
                print("❌ No cloud storage available")
                return {"status": "error", "message": "Cloud storage not available"}
            
            files = self.cloud_storage.list_files(self.project_id, path)
            print(f"==> Found {len(files)} files")
            
            if len(files) > 0:
                print("   Files found:")
                for i, file in enumerate(files[:5]):  # Show first 5 files
                    print(f"     {i+1}. {file}")
                if len(files) > 5:
                    print(f"     ... and {len(files) - 5} more files")
            
            return {
                "status": "success", 
                "files": files,
                "count": len(files),
                "path_filter": path or "all files"
            }
            
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return {"status": "error", "message": str(e)}

    def handle_integration_docs(self, action: dict) -> dict:
        """Handle integration_docs action - list, search, or read integration documentation"""
        print(f"==> Integration docs action triggered")
        operation = action.get('operation', '')
        print(f"   Operation: {operation}")
        
        if operation == 'list':
            return self._handle_integration_docs_list()
        elif operation == 'search':
            query = action.get('query', '')
            return self._handle_integration_docs_search(query)
        elif operation == 'read':
            doc_name = action.get('doc_name', '')
            return self._handle_integration_docs_read(doc_name)
        else:
            print(f"❌ Unknown integration_docs operation: {operation}")
            return {"status": "error", "message": f"Unknown operation: {operation}"}
    
    def _handle_integration_docs_list(self) -> dict:
        """List all available integration documentation"""
        print("==> Listing all integration docs")
        try:
            if hasattr(self.cloud_storage, 'list_docs'):
                docs = self.cloud_storage.list_docs()
                print(f"   Found {len(docs)} docs")
                return {"status": "success", "docs": docs}
            else:
                print("❌ Docs functionality not implemented in cloud storage")
                return {"status": "error", "message": "Docs not implemented yet"}
        except Exception as e:
            print(f"❌ Error listing docs: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_integration_docs_search(self, query: str) -> dict:
        """Search integration documentation by query"""
        print(f"==> Searching integration docs for: '{query}'")
        try:
            if hasattr(self.cloud_storage, 'search_docs'):
                results = self.cloud_storage.search_docs(query)
                print(f"   Found {len(results)} matching docs")
                return {"status": "success", "query": query, "results": results}
            else:
                print("❌ Docs search not implemented in cloud storage")
                return {"status": "error", "message": "Docs search not implemented yet"}
        except Exception as e:
            print(f"❌ Error searching docs: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_integration_docs_read(self, doc_name: str) -> dict:
        """Read specific integration documentation"""
        print(f"==> Reading integration doc: '{doc_name}'")
        try:
            if hasattr(self.cloud_storage, 'download_doc'):
                content = self.cloud_storage.download_doc(doc_name)
                if content:
                    print(f"   Doc loaded: {len(content)} characters")
                    return {"status": "success", "doc_name": doc_name, "content": content}
                else:
                    print(f"   Doc not found: {doc_name}")
                    return {"status": "error", "message": f"Document '{doc_name}' not found"}
            else:
                print("❌ Docs read not implemented in cloud storage")
                return {"status": "error", "message": "Docs read not implemented yet"}
        except Exception as e:
            print(f"❌ Error reading doc: {e}")
            return {"status": "error", "message": str(e)}