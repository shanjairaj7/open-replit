#!/usr/bin/env python3

import requests
import json
import time

def test_simple_streaming():
    """Test the streaming API with a very simple request"""
    print("🧪 Testing streaming API with a simple todo request...")
    
    url = "http://localhost:8082/chat/stream"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": "Create a todo with id 'test-todo' that says 'Test streaming API'",
        "conversation_id": None,
        "project_id": None
    }
    
    print(f"📡 Sending request to {url}")
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=10)
        
        print(f"📊 Response status: {response.status_code}")
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
                        
                        print(f"[{chunk_count:03d}] {chunk_type}: {content[:150]}{'...' if len(content) > 150 else ''}")
                        
                        # Show action metadata for actions
                        if chunk_type in ['action_start', 'action_result']:
                            action_data = data.get('data', {})
                            action_type = action_data.get('action_type', 'unknown')
                            
                            if 'file_path' in action_data:
                                print(f"      └─ Action: {action_type} -> {action_data['file_path']}")
                            elif 'todo_id' in action_data:
                                print(f"      └─ Todo: {action_type} -> {action_data['todo_id']} ({action_data.get('status', '')})")
                            else:
                                print(f"      └─ Action: {action_type}")
                        
                    except json.JSONDecodeError as e:
                        print(f"[{chunk_count:03d}] JSON Error: {e} | Raw: {line_str[:100]}")
                
                # Stop after reasonable number of chunks
                if chunk_count >= 30:
                    print(f"⏹️ Stopping after {chunk_count} chunks")
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
    test_simple_streaming()