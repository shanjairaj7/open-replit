#!/usr/bin/env python3

import requests
import json
import time

def test_error_streaming():
    """Test to see what the error message is"""
    print("🧪 Testing to see error details...")
    
    url = "http://localhost:8082/chat/stream"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": "Just say hello",
        "conversation_id": None,
        "project_id": None
    }
    
    print(f"📡 Sending simple request to {url}")
    
    try:
        # Send streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)
        
        print(f"📊 Response status: {response.status_code}")
        print("🌊 Raw streaming response:")
        print("=" * 80)
        
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                line_str = line.decode('utf-8')
                print(f"[{chunk_count:03d}] RAW: {line_str}")
                
                # Stop after reasonable number of chunks
                if chunk_count >= 20:
                    print(f"⏹️ Stopping after {chunk_count} chunks")
                    break
                    
        print("=" * 80)
        print(f"✅ Test completed! Received {chunk_count} chunks")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_error_streaming()