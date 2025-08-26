"""
Project Pool Manager - Maintains hot-loaded projects for instant allocation

This system pre-creates projects with GitHub boilerplates cloned to Azure,
ensuring streaming API can immediately start processing without waiting for repo cloning.

Architecture:
- Pool of 5 pre-warmed projects
- Minimum 2 available projects at all times  
- Background worker maintains pool size
- Project lifecycle: created → available → allocated → active → archived
"""

import os
import json
import time
import uuid
import asyncio
import threading
import tempfile
import shutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from cloud_storage import AzureBlobStorage


class ProjectStatus(Enum):
    """Project lifecycle states"""
    CREATING = "creating"      # Being set up (cloning repos)
    AVAILABLE = "available"    # Ready to be allocated
    ALLOCATED = "allocated"    # Assigned to a conversation
    ACTIVE = "active"          # In use by streaming API
    ARCHIVED = "archived"      # Completed, kept for history


@dataclass
class PooledProject:
    """Represents a pre-warmed project in the pool"""
    project_id: str
    created_at: str
    status: ProjectStatus
    allocated_at: Optional[str] = None
    allocated_to_conversation: Optional[str] = None
    frontend_repo: str = "https://github.com/shanjairaj7/frontend-boilerplate.git"
    backend_repo: str = "https://github.com/shanjairaj7/backend-boilerplate.git"
    metadata_saved: bool = False
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PooledProject':
        data['status'] = ProjectStatus(data['status'])
        return cls(**data)


class BoilerplateCache:
    """Smart caching system for boilerplate repositories"""
    
    def __init__(self, cache_dir: str = "/tmp/boilerplate_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.frontend_repo = "https://github.com/shanjairaj7/frontend-boilerplate.git"
        self.backend_repo = "https://github.com/shanjairaj7/backend-boilerplate.git"
        self.frontend_path = self.cache_dir / "frontend-boilerplate"
        self.backend_path = self.cache_dir / "backend-boilerplate"
        self.cache_lock = threading.Lock()
        
        print(f"📂 Boilerplate cache initialized at: {self.cache_dir}")
    
    def _clone_repo_once(self, repo_url: str, target_path: Path) -> bool:
        """Clone repository with 2-hour cache expiration"""
        try:
            # Check if cache exists and is still valid (2 hours)
            if target_path.exists():
                cache_age = time.time() - target_path.stat().st_mtime
                cache_hours = cache_age / 3600
                
                if cache_hours < 2.0:
                    print(f"♻️ Reusing cached boilerplate: {target_path} (age: {cache_hours:.1f}h)")
                    return True
                else:
                    print(f"🕐 Cache expired for {target_path} (age: {cache_hours:.1f}h) - refreshing...")
                    # Remove old cache
                    shutil.rmtree(target_path, ignore_errors=True)
            
            print(f"📡 Cloning fresh boilerplate {repo_url} to {target_path}")
            
            # Clone repository
            result = subprocess.run([
                'git', 'clone', repo_url, str(target_path)
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Successfully cached boilerplate: {target_path}")
                return True
            else:
                print(f"❌ Failed to clone {repo_url}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error caching boilerplate {repo_url}: {e}")
            return False
    
    def ensure_boilerplates_cached(self) -> Tuple[bool, bool]:
        """Ensure both boilerplates are cached locally with 2-hour expiration"""
        with self.cache_lock:
            print(f"🔍 Checking boilerplate cache status...")
            frontend_ready = self._clone_repo_once(self.frontend_repo, self.frontend_path)
            backend_ready = self._clone_repo_once(self.backend_repo, self.backend_path)
            
            if frontend_ready and backend_ready:
                print(f"✅ Both boilerplates ready in cache")
            else:
                print(f"⚠️ Cache issues: frontend={frontend_ready}, backend={backend_ready}")
            
            return frontend_ready, backend_ready
    
    def get_cache_status(self) -> Dict[str, any]:
        """Get detailed cache status information"""
        status = {
            "cache_dir": str(self.cache_dir),
            "frontend": {"exists": False, "age_hours": None, "valid": False},
            "backend": {"exists": False, "age_hours": None, "valid": False}
        }
        
        for name, path in [("frontend", self.frontend_path), ("backend", self.backend_path)]:
            if path.exists():
                cache_age = time.time() - path.stat().st_mtime
                cache_hours = cache_age / 3600
                status[name].update({
                    "exists": True,
                    "age_hours": round(cache_hours, 1),
                    "valid": cache_hours < 2.0
                })
        
        return status
    
    def upload_cached_boilerplate_to_project(self, cloud_storage: AzureBlobStorage, 
                                           project_id: str, boilerplate_type: str) -> bool:
        """Upload cached boilerplate files to a specific project"""
        try:
            if boilerplate_type == "frontend":
                source_path = self.frontend_path
            elif boilerplate_type == "backend":
                source_path = self.backend_path
            else:
                raise ValueError(f"Invalid boilerplate type: {boilerplate_type}")
            
            if not source_path.exists():
                print(f"❌ Cached {boilerplate_type} boilerplate not found: {source_path}")
                return False
            
            print(f"📤 Uploading cached {boilerplate_type} boilerplate to {project_id}")
            
            # Upload all files from cached boilerplate
            uploaded_files = 0
            skipped_files = 0
            
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    # Skip git and other system files
                    relative_path = file_path.relative_to(source_path)
                    relative_str = str(relative_path).replace('\\', '/')
                    
                    if self._should_skip_file(relative_str):
                        skipped_files += 1
                        continue
                    
                    try:
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Upload to project with boilerplate_type prefix
                        cloud_path = f"{boilerplate_type}/{relative_str}"
                        
                        if cloud_storage.upload_file(project_id, cloud_path, content):
                            uploaded_files += 1
                        
                    except Exception as e:
                        print(f"⚠️ Failed to upload {relative_str}: {str(e)}")
                        skipped_files += 1
            
            print(f"✅ {boilerplate_type.title()} upload complete: {uploaded_files} files uploaded, {skipped_files} skipped")
            return uploaded_files > 0
            
        except Exception as e:
            print(f"❌ Error uploading cached {boilerplate_type}: {e}")
            return False
    
    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped during upload"""
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


class ProjectPoolManager:
    """Manages the pool of pre-warmed projects"""
    
    def __init__(self):
        self.cloud_storage = AzureBlobStorage()
        self.boilerplate_cache = BoilerplateCache()
        self.pool_size = 5
        self.min_available = 2
        self.pool: Dict[str, PooledProject] = {}
        self.lock = threading.Lock()
        self.background_worker_running = False
        self.maintenance_interval = 30  # seconds
        
        # Ensure boilerplates are cached on startup
        print(f"🚀 Ensuring boilerplates are cached...")
        frontend_ready, backend_ready = self.boilerplate_cache.ensure_boilerplates_cached()
        
        if frontend_ready and backend_ready:
            print(f"✅ Both boilerplates cached and ready for rapid deployment")
        else:
            print(f"⚠️ Some boilerplates failed to cache: frontend={frontend_ready}, backend={backend_ready}")
        
        # Load existing pool from cloud storage
        self._load_pool_from_storage()
        
        print(f"🏊‍♂️ ProjectPoolManager initialized")
        print(f"📊 Current pool status: {self.get_pool_stats()}")
        
        # Start background maintenance worker immediately to maintain pool autonomously
        self._ensure_background_worker()
    
    def _generate_pooled_project_id(self) -> str:
        """Generate unique project ID for pooled projects - simple format for URLs"""
        # Use shorter format: horizon-123-da08s
        unique_num = str(int(datetime.now().timestamp()))[-3:]  # Last 3 digits of timestamp
        unique_id = uuid.uuid4().hex[:5]  # 5 char hex
        return f"horizon-{unique_num}-{unique_id}"
    
    def _load_pool_from_storage(self) -> None:
        """Load existing project pool from Azure storage"""
        try:
            # Check if pool metadata exists
            pool_metadata = self.cloud_storage.download_file("system", "project_pool.json")
            
            if pool_metadata:
                pool_data = json.loads(pool_metadata)
                
                # Reconstruct pool from metadata
                for project_data in pool_data.get("projects", []):
                    project = PooledProject.from_dict(project_data)
                    self.pool[project.project_id] = project
                
                print(f"📂 Loaded {len(self.pool)} projects from pool storage")
            else:
                print(f"📂 No existing project pool found, starting fresh")
                
        except Exception as e:
            print(f"⚠️ Error loading project pool from storage: {e}")
            self.pool = {}
    
    def _save_pool_to_storage(self) -> None:
        """Save current project pool state to Azure storage"""
        try:
            pool_data = {
                "last_updated": datetime.now().isoformat(),
                "pool_size": len(self.pool),
                "projects": [project.to_dict() for project in self.pool.values()]
            }
            
            pool_json = json.dumps(pool_data, indent=2)
            success = self.cloud_storage.upload_file("system", "project_pool.json", pool_json)
            
            if success:
                print(f"💾 Saved project pool state ({len(self.pool)} projects)")
            else:
                print(f"❌ Failed to save project pool state")
                
        except Exception as e:
            print(f"❌ Error saving project pool: {e}")
    
    def _create_pooled_project(self) -> Optional[PooledProject]:
        """Create a new project with GitHub boilerplates pre-cloned"""
        project_id = self._generate_pooled_project_id()
        
        try:
            print(f"🚀 Creating pooled project: {project_id}")
            
            # Create project object
            project = PooledProject(
                project_id=project_id,
                created_at=datetime.now().isoformat(),
                status=ProjectStatus.CREATING
            )
            
            # Add to pool immediately (marked as CREATING)
            with self.lock:
                self.pool[project_id] = project
            
            # Upload cached boilerplates to Azure (much faster!)
            print(f"📤 Uploading cached boilerplates for {project_id}...")
            frontend_success = self.boilerplate_cache.upload_cached_boilerplate_to_project(
                self.cloud_storage, project_id, "frontend"
            )
            
            backend_success = self.boilerplate_cache.upload_cached_boilerplate_to_project(
                self.cloud_storage, project_id, "backend"
            )
            
            if frontend_success and backend_success:
                # Save project metadata
                metadata = {
                    "project_id": project_id,
                    "project_name": project_id,
                    "created_at": project.created_at,
                    "frontend_repo": project.frontend_repo,
                    "backend_repo": project.backend_repo,
                    "creation_method": "project_pool_prewarmed",
                    "status": "available_in_pool",
                    "pool_created": True
                }
                
                metadata_success = self.cloud_storage.save_project_metadata(project_id, metadata)
                
                if metadata_success:
                    # Mark project as available
                    with self.lock:
                        project.status = ProjectStatus.AVAILABLE
                        project.metadata_saved = True
                    
                    print(f"✅ Pooled project ready: {project_id}")
                    print(f"📁 Frontend: Cloned from {project.frontend_repo}")
                    print(f"📁 Backend: Cloned from {project.backend_repo}")
                    
                    return project
                else:
                    print(f"⚠️ Project files created but metadata save failed for {project_id}")
            
            # If we get here, something failed
            print(f"❌ Failed to create pooled project: {project_id}")
            with self.lock:
                if project_id in self.pool:
                    del self.pool[project_id]
            
            return None
            
        except Exception as e:
            print(f"❌ Error creating pooled project {project_id}: {e}")
            with self.lock:
                if project_id in self.pool:
                    del self.pool[project_id]
            return None
    
    def get_available_project(self, conversation_id: str, user_request: str) -> Optional[str]:
        """Allocate an available project from the pool"""
        with self.lock:
            # Find first available project
            for project_id, project in self.pool.items():
                if project.status == ProjectStatus.AVAILABLE:
                    # Allocate this project
                    project.status = ProjectStatus.ALLOCATED
                    project.allocated_at = datetime.now().isoformat()
                    project.allocated_to_conversation = conversation_id
                    
                    print(f"🎯 Allocated pooled project: {project_id} to conversation: {conversation_id}")
                    print(f"📝 User request: {user_request[:50]}...")
                    
                    # Save updated pool state
                    self._save_pool_to_storage()
                    
                    # Background worker runs continuously, no trigger needed
                    return project_id
            
            # No available projects
            print(f"⚠️ No available projects in pool! Creating emergency project...")
            return None
    
    def mark_project_active(self, project_id: str) -> None:
        """Mark allocated project as active (in use)"""
        with self.lock:
            if project_id in self.pool:
                self.pool[project_id].status = ProjectStatus.ACTIVE
                print(f"🟢 Project {project_id} marked as active")
                self._save_pool_to_storage()
    
    def archive_project(self, project_id: str) -> None:
        """Archive completed project"""
        with self.lock:
            if project_id in self.pool:
                self.pool[project_id].status = ProjectStatus.ARCHIVED
                print(f"📦 Project {project_id} archived")
                self._save_pool_to_storage()
    
    def get_pool_stats(self) -> dict:
        """Get current pool statistics"""
        with self.lock:
            stats = {
                "total": len(self.pool),
                "creating": 0,
                "available": 0, 
                "allocated": 0,
                "active": 0,
                "archived": 0
            }
            
            for project in self.pool.values():
                stats[project.status.value] += 1
            
            return stats
    
    async def _async_ensure_background_worker(self) -> None:
        """Ensure background worker is running (async version)"""
        await asyncio.to_thread(self._ensure_background_worker)

    def _ensure_background_worker(self) -> None:
        """Ensure background worker is running"""
        if not self.background_worker_running:
            self.background_worker_running = True
            worker_thread = threading.Thread(target=self._background_maintenance, daemon=True)
            worker_thread.start()
            print(f"🔄 Started background pool maintenance worker")
    
    def _background_maintenance(self) -> None:
        """Background worker to maintain pool size"""
        print(f"🔄 Pool maintenance worker started")
        
        while True:
            try:
                # Get current stats
                stats = self.get_pool_stats()
                
                # Check if we need more available projects
                available_count = stats["available"]
                creating_count = stats["creating"]
                
                print(f"📊 Pool check: {available_count} available, {creating_count} creating, min required: {self.min_available}")
                
                # Create projects if needed
                needed = max(0, self.min_available - (available_count + creating_count))
                
                if needed > 0:
                    print(f"🚀 Creating {needed} new pooled projects to maintain minimum")
                    
                    for i in range(needed):
                        project = self._create_pooled_project()
                        if project:
                            print(f"✅ Created pooled project {i+1}/{needed}: {project.project_id}")
                        else:
                            print(f"❌ Failed to create pooled project {i+1}/{needed}")
                        
                        # Small delay between creations
                        time.sleep(2)
                
                # Refresh boilerplate cache if needed (check every maintenance cycle)
                try:
                    cache_status = self.boilerplate_cache.get_cache_status()
                    if not cache_status["frontend"]["valid"] or not cache_status["backend"]["valid"]:
                        print(f"🔄 Refreshing expired boilerplate cache...")
                        self.boilerplate_cache.ensure_boilerplates_cached()
                except Exception as e:
                    print(f"⚠️ Error checking/refreshing cache: {e}")
                
                # Clean up old archived projects (keep only last 10)
                self._cleanup_archived_projects()
                
                # Save pool state
                self._save_pool_to_storage()
                
                # Wait for next maintenance cycle
                time.sleep(self.maintenance_interval)
                
            except Exception as e:
                print(f"❌ Error in pool maintenance: {e}")
                time.sleep(10)  # Wait before retrying
    
    def _cleanup_archived_projects(self) -> None:
        """Remove old archived projects to prevent pool from growing indefinitely"""
        with self.lock:
            archived_projects = [(pid, p) for pid, p in self.pool.items() 
                               if p.status == ProjectStatus.ARCHIVED]
            
            # Keep only the 10 most recent archived projects
            if len(archived_projects) > 10:
                # Sort by allocated_at (when they were last used)
                archived_projects.sort(key=lambda x: x[1].allocated_at or x[1].created_at, reverse=True)
                
                # Remove the oldest ones
                to_remove = archived_projects[10:]
                for project_id, project in to_remove:
                    print(f"🗑️ Removing old archived project: {project_id}")
                    del self.pool[project_id]
    
    def get_pool_status(self) -> dict:
        """Get detailed pool status for API endpoint"""
        stats = self.get_pool_stats()
        
        # Add detailed project info
        projects_by_status = {}
        for status in ProjectStatus:
            projects_by_status[status.value] = []
        
        with self.lock:
            for project in self.pool.values():
                project_info = {
                    "project_id": project.project_id,
                    "created_at": project.created_at,
                    "allocated_at": project.allocated_at,
                    "conversation_id": project.allocated_to_conversation
                }
                projects_by_status[project.status.value].append(project_info)
        
        return {
            "pool_size": self.pool_size,
            "min_available": self.min_available,
            "stats": stats,
            "projects_by_status": projects_by_status,
            "background_worker_running": self.background_worker_running,
            "last_updated": datetime.now().isoformat()
        }


# Global pool manager instance
_pool_manager = None


def get_pool_manager() -> ProjectPoolManager:
    """Get or create the global pool manager instance"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ProjectPoolManager()
        # Start background worker
        _pool_manager._ensure_background_worker()
    return _pool_manager


# Initialize pool on import
print(f"🏊‍♂️ Initializing Project Pool Manager...")
pool_manager = get_pool_manager()
print(f"✅ Project Pool Manager ready: {pool_manager.get_pool_stats()}")