#!/usr/bin/env python3

import requests
import json
import time

def test_full_streaming():
    """Test the complete streaming API to see action detection"""
    print("🧪 Testing FULL streaming API to see actions...")
    
    url = "http://localhost:8082/chat/stream"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": "Create a todo with id 'streaming-test' that says 'Test real-time streaming'",
        "conversation_id": None,
        "project_id": None
    }
    
    print(f"📡 Sending request to {url}")
    
    try:
        # Send streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
        
        print(f"📊 Response status: {response.status_code}")
        print("🌊 Streaming response:")
        print("=" * 100)
        
        chunk_count = 0
        action_count = 0
        
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
                        
                        # Different handling for different types
                        if chunk_type == "assistant_message":
                            print(f"[{chunk_count:03d}] 💬 AI: {content}", end='', flush=True)
                        elif chunk_type in ['action_start', 'action_result']:
                            action_count += 1
                            action_data = data.get('data', {})
                            action_type = action_data.get('action_type', 'unknown')
                            status = action_data.get('status', '')
                            
                            print(f"\n[{chunk_count:03d}] 🎬 ACTION {action_type.upper()} ({chunk_type}): {content}")
                            
                            # Show detailed metadata
                            if 'file_path' in action_data:
                                print(f"           📁 File: {action_data['file_path']}")
                            if 'todo_id' in action_data:
                                print(f"           📝 Todo: {action_data['todo_id']} | Status: {action_data.get('status', 'N/A')}")
                            if 'priority' in action_data:
                                print(f"           🔥 Priority: {action_data['priority']}")
                            if status:
                                print(f"           ⚡ Result: {status}")
                        elif chunk_type == "error":
                            print(f"\n[{chunk_count:03d}] ❌ ERROR: {content}")
                        elif chunk_type == "text":
                            print(f"[{chunk_count:03d}] 📡 STATUS: {content}")
                        
                    except json.JSONDecodeError as e:
                        print(f"\n[{chunk_count:03d}] ⚠️ JSON Error: {e}")
                
                # Stop after reasonable number of chunks or when we see actions
                if chunk_count >= 100:  # Give more time to see actions
                    print(f"\n⏹️ Stopping after {chunk_count} chunks")
                    break
                    
        print("\n" + "=" * 100)
        print(f"✅ Test completed!")
        print(f"📊 Total chunks received: {chunk_count}")
        print(f"🎬 Actions detected: {action_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_full_streaming()