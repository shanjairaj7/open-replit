"""
Azure Cosmos DB integration for project logs and network requests storage.
Handles real-time logging with rolling 100-item limit per project per type.
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions


class HorizonCosmosDB:
    """Azure Cosmos DB client for project logs and network requests storage"""
    
    def __init__(self):
        """Initialize Cosmos DB client with connection string"""
        # Cosmos DB connection details
        self.connection_string = "AccountEndpoint=https://horizon-cosmosdb.documents.azure.com:443/;AccountKey=QoyHML4AT7Btuo9ENkqKgif3Shd4FExwTBAoYD5QS3WTXtyDvxVV1JVNGD9KUggUfYm4OrIw6FMoACDb0MHylQ==;"
        self.database_name = "horizon-db"
        self.container_name = "project-logs"
        
        # Initialize client
        self.client = CosmosClient.from_connection_string(self.connection_string)
        self.database = self.client.get_database_client(self.database_name)
        self.container = self.database.get_container_client(self.container_name)
        
        # No cleanup tracking needed - let TTL handle it
        print("🎯 Using TTL-based cleanup for optimal performance")
        
        print(f"✅ Connected to Cosmos DB: {self.database_name}/{self.container_name}")
    
    def store_log_entry(self, project_id: str, log_type: str, entry_data: dict) -> bool:
        """
        Store a single log/network entry (optimized for speed)
        
        Args:
            project_id: Project identifier
            log_type: Either "logs" or "network"  
            entry_data: The log/network data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create document with minimal required fields for speed
            document = {
                "id": f"{project_id}_{log_type}_{entry_data['timestamp']}_{hash(str(entry_data)) % 10000}",
                "project_id": project_id,
                "log_type": log_type,
                "timestamp": entry_data['timestamp'],
                "data": entry_data
            }
            
            # Insert the document (ultra-fast, no cleanup needed - TTL handles it)
            self.container.create_item(body=document)
            
            return True
            
        except exceptions.CosmosResourceExistsError:
            return True  # Consider this success since document exists
            
        except Exception as e:
            print(f"❌ Error storing {log_type} entry for project {project_id}: {e}")
            return False
    
    def get_entries(self, project_id: str, log_type: str, limit: int = 100) -> List[dict]:
        """
        Get entries for a project and type
        
        Args:
            project_id: Project identifier
            log_type: Either "logs" or "network"
            limit: Maximum number of entries to return
            
        Returns:
            List of entry data dictionaries
        """
        try:
            # Cosmos DB SQL doesn't support OFFSET/FETCH, so we get all and limit in Python
            query = """
                SELECT c.data FROM c 
                WHERE c.project_id = @project_id AND c.log_type = @log_type 
                ORDER BY c.timestamp DESC
            """
            
            parameters = [
                {"name": "@project_id", "value": project_id},
                {"name": "@log_type", "value": log_type}
            ]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit  # Limit at query level
            ))
            
            # Extract just the data portion and limit to requested amount
            result = [item['data'] for item in items[:limit]]
            return result
            
        except Exception as e:
            print(f"❌ Error retrieving {log_type} entries for project {project_id}: {e}")
            return []
    
    def get_entry_count(self, project_id: str, log_type: str) -> int:
        """Get the count of entries for a project and type"""
        try:
            query = f"""
                SELECT VALUE COUNT(1) FROM c 
                WHERE c.project_id = @project_id AND c.log_type = @log_type
            """
            
            parameters = [
                {"name": "@project_id", "value": project_id},
                {"name": "@log_type", "value": log_type}
            ]
            
            result = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            return result[0] if result else 0
            
        except Exception as e:
            print(f"❌ Error counting {log_type} entries for project {project_id}: {e}")
            return 0


# Global instance
_cosmos_client = None

def get_cosmos_client() -> HorizonCosmosDB:
    """Get or create global Cosmos DB client instance"""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = HorizonCosmosDB()
    return _cosmos_client


def test_cosmos_connection():
    """Test Cosmos DB connection and basic operations"""
    try:
        cosmos = get_cosmos_client()
        
        # Test storing an entry
        test_data = {
            "timestamp": int(datetime.now().timestamp() * 1000),
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": "Test log entry",
            "logType": "info"
        }
        
        success = cosmos.store_log_entry("test-project", "logs", test_data)
        if success:
            print("✅ Cosmos DB test successful")
            
            # Get count
            count = cosmos.get_entry_count("test-project", "logs")
            print(f"📊 Test project has {count} log entries")
            
            return True
        else:
            print("❌ Cosmos DB test failed")
            return False
            
    except Exception as e:
        print(f"❌ Cosmos DB test error: {e}")
        return False


if __name__ == "__main__":
    # Run test
    test_cosmos_connection()