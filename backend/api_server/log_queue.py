"""
Fast background queue system for logs and network requests.
Fire-and-forget approach with immediate API responses.
"""

import json
import threading
import time
from queue import Queue
from typing import Dict, Any
from datetime import datetime


class FastLogQueue:
    """Ultra-fast background queue for storing logs and network requests"""
    
    def __init__(self, max_queue_size=10000):
        """Initialize the fast queue system"""
        self.queue = Queue(maxsize=max_queue_size)
        self.worker_thread = None
        self.running = True
        
        # Start background worker
        self._start_worker()
        
        print(f"🚀 FastLogQueue initialized with max size: {max_queue_size}")
    
    def add_entry(self, project_id: str, log_type: str, entry_data: Dict[Any, Any]) -> bool:
        """
        Add entry to queue (immediate return, no waiting)
        
        Args:
            project_id: Project identifier
            log_type: Either "logs" or "network"
            entry_data: The data to store
            
        Returns:
            bool: True if queued successfully, False if queue is full
        """
        try:
            # Create queue item
            queue_item = {
                "project_id": project_id,
                "log_type": log_type,
                "entry_data": entry_data,
                "queued_at": datetime.now().isoformat()
            }
            
            # Add to queue (non-blocking)
            self.queue.put_nowait(queue_item)
            return True
            
        except:
            # Queue is full, drop the entry (or implement overflow handling)
            print(f"⚠️ Queue full, dropping {log_type} entry for {project_id}")
            return False
    
    def _start_worker(self):
        """Start the background worker thread"""
        self.worker_thread = threading.Thread(target=self._background_worker, daemon=True)
        self.worker_thread.start()
        print("🔄 Background worker started")
    
    def _background_worker(self):
        """Background thread that processes the queue"""
        from cosmos_db import get_cosmos_client
        
        # Initialize Cosmos DB client once for the worker
        try:
            cosmos = get_cosmos_client()
            print("✅ Background worker connected to Cosmos DB")
        except Exception as e:
            print(f"❌ Background worker failed to connect to Cosmos DB: {e}")
            return
        
        batch_size = 50  # Process in batches for efficiency
        batch = []
        
        while self.running:
            try:
                # Get items from queue (with timeout)
                while len(batch) < batch_size:
                    try:
                        item = self.queue.get(timeout=1.0)  # Wait up to 1 second
                        batch.append(item)
                        self.queue.task_done()
                    except:
                        break  # Timeout or queue empty
                
                # Process batch if we have items
                if batch:
                    self._process_batch(cosmos, batch)
                    batch = []
                
            except Exception as e:
                print(f"❌ Background worker error: {e}")
                time.sleep(1)  # Brief pause on error
    
    def _process_batch(self, cosmos, batch):
        """Process a batch of queue items"""
        success_count = 0
        error_count = 0
        
        for item in batch:
            try:
                project_id = item["project_id"]
                log_type = item["log_type"]
                entry_data = item["entry_data"]
                
                # Store in Cosmos DB
                success = cosmos.store_log_entry(project_id, log_type, entry_data)
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing queue item: {e}")
        
        if success_count > 0 or error_count > 0:
            print(f"📊 Batch processed: {success_count} success, {error_count} errors")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "queue_size": self.queue.qsize(),
            "running": self.running,
            "worker_alive": self.worker_thread.is_alive() if self.worker_thread else False
        }
    
    def shutdown(self):
        """Gracefully shutdown the queue"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("🛑 FastLogQueue shutdown")


# Global queue instance
_log_queue = None

def get_log_queue() -> FastLogQueue:
    """Get or create global log queue instance"""
    global _log_queue
    if _log_queue is None:
        _log_queue = FastLogQueue()
    return _log_queue


if __name__ == "__main__":
    # Test the queue
    queue = get_log_queue()
    
    # Add test entries
    for i in range(5):
        queue.add_entry("test-project", "logs", {
            "timestamp": int(time.time() * 1000),
            "message": f"Test log {i}",
            "logType": "info"
        })
    
    print(f"Queue stats: {queue.get_stats()}")
    time.sleep(3)
    print("Test complete")