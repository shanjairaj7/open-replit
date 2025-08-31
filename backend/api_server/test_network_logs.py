#!/usr/bin/env python3
"""
Test script for network logs functionality
"""

import time
import requests
from log_queue import get_log_queue

def test_network_logs():
    """Add some test network request data and test the endpoint"""
    print("🧪 Testing network logs functionality")
    
    # Get the log queue
    queue = get_log_queue()
    
    # Add some test network request entries
    test_network_requests = [
        {
            "timestamp": int(time.time() * 1000),
            "time": time.strftime("%H:%M:%S"),
            "method": "GET",
            "url": "https://api.example.com/users",
            "status": 200,
            "responseTime": 245
        },
        {
            "timestamp": int(time.time() * 1000) + 1000,
            "time": time.strftime("%H:%M:%S"),
            "method": "POST",
            "url": "https://api.example.com/login",
            "status": 401,
            "responseTime": 150
        },
        {
            "timestamp": int(time.time() * 1000) + 2000,
            "time": time.strftime("%H:%M:%S"),
            "method": "GET", 
            "url": "https://api.example.com/dashboard",
            "status": 500,
            "responseTime": 3000
        },
        {
            "timestamp": int(time.time() * 1000) + 3000,
            "time": time.strftime("%H:%M:%S"),
            "method": "PUT",
            "url": "https://api.example.com/profile",
            "status": 204,
            "responseTime": 180
        }
    ]
    
    # Add the test network requests
    for i, request_data in enumerate(test_network_requests):
        success = queue.add_entry("test-project", "network", request_data)
        if success:
            print(f"✅ Added test network request {i+1}")
        else:
            print(f"❌ Failed to add test network request {i+1}")
    
    print(f"📊 Queue stats: {queue.get_stats()}")
    
    # Wait for background processing
    print("⏳ Waiting for background processing...")
    time.sleep(5)
    
    # Test the endpoint
    print("🔍 Testing network logs endpoint...")
    try:
        response = requests.get("http://localhost:8084/test-project/logs/network?limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Network logs endpoint working!")
            print(f"📊 Retrieved {data.get('returned_count', 0)} entries")
            print(f"📊 Total stored: {data.get('total_count', 0)}")
            
            entries = data.get('entries', [])
            for entry in entries:
                method = entry.get('method', 'GET')
                url = entry.get('url', '')
                status = entry.get('status', 0)
                response_time = entry.get('responseTime', 0)
                print(f"  • {method} {url} - {status} ({response_time}ms)")
                
        else:
            print(f"❌ Network logs endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing network logs endpoint: {e}")

if __name__ == "__main__":
    test_network_logs()