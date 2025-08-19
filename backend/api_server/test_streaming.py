#!/usr/bin/env python3

import requests
import json
import time

def test_streaming_api():
    """Test the streaming API with a simple request"""
    print("🧪 Testing streaming API with a simple request...")
    
    url = "http://localhost:8082/chat/stream"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": "Create a simple calculator with dark mode",
        "conversation_id": None,
        "project_id": None
    }
    
    print(f"📡 Sending request to {url}")
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        print("🌊 Streaming response:")
        print("=" * 80)
        
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                line_str = line.decode('utf-8')
                
                # Parse streaming data
                if line_str.startswith('data: '):
                    try:
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        data = json.loads(data_str)
                        
                        # Pretty print the streaming chunk
                        chunk_type = data.get('type', 'unknown')
                        content = data.get('data', {}).get('content', '')
                        timestamp = data.get('timestamp', '')
                        
                        print(f"[{chunk_count:03d}] {timestamp} | {chunk_type}: {content[:100]}{'...' if len(content) > 100 else ''}")
                        
                        # Show action metadata for actions
                        if chunk_type in ['action_start', 'action_result']:
                            action_type = data.get('data', {}).get('action_type', 'unknown')
                            file_path = data.get('data', {}).get('file_path', '')
                            print(f"      └─ Action: {action_type} {file_path}")
                        
                    except json.JSONDecodeError as e:
                        print(f"[{chunk_count:03d}] JSON Error: {e} | Raw: {line_str}")
                
                # Stop after reasonable number of chunks for testing
                if chunk_count >= 50:
                    print(f"⏹️ Stopping after {chunk_count} chunks for test purposes")
                    break
                    
        print("=" * 80)
        print(f"✅ Test completed! Received {chunk_count} streaming chunks")
        
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - is the server running?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_streaming_api()