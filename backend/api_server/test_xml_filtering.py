#!/usr/bin/env python3

import requests
import json
import time

def test_xml_filtering():
    """Test that XML action tags are filtered from assistant messages"""
    print("🧪 Testing XML filtering in streaming API...")
    
    url = "http://localhost:8084/chat/stream"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": "Create a todo with id 'xml-filter-test' that says 'Testing XML filtering'",
        "conversation_id": None,
        "project_id": None
    }
    
    print(f"📡 Sending request to {url}")
    
    try:
        # Send streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        print("🌊 Streaming response:")
        print("=" * 120)
        
        chunk_count = 0
        action_count = 0
        xml_found_in_assistant = False
        clean_assistant_messages = []
        
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                line_str = line.decode('utf-8')
                
                # Parse streaming data
                if line_str.startswith('data: '):
                    try:
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        data = json.loads(data_str)
                        
                        chunk_type = data.get('type', 'unknown')
                        content = data.get('data', {}).get('content', '')
                        
                        if chunk_type == "assistant_message":
                            # Check if XML tags leaked into assistant messages
                            if '<action' in content.lower() or '</action' in content.lower():
                                xml_found_in_assistant = True
                                print(f"🚨 XML LEAKED: [{chunk_count:03d}] AI: {repr(content)}")
                            else:
                                clean_assistant_messages.append(content)
                                print(f"✅ CLEAN: [{chunk_count:03d}] AI: {repr(content)}")
                        elif chunk_type in ['action_start', 'action_result']:
                            action_count += 1
                            action_data = data.get('data', {})
                            action_type = action_data.get('action_type', 'unknown')
                            status = action_data.get('status', '')
                            
                            print(f"🎬 ACTION: [{chunk_count:03d}] {action_type.upper()} ({chunk_type}): {content}")
                        elif chunk_type == "error":
                            print(f"❌ ERROR: [{chunk_count:03d}] {content}")
                        elif chunk_type == "text":
                            print(f"📡 STATUS: [{chunk_count:03d}] {content}")
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON Error: [{chunk_count:03d}] {e}")
                
                # Stop after reasonable number of chunks
                if chunk_count >= 80:
                    print(f"⏹️ Stopping after {chunk_count} chunks")
                    break
                    
        print("=" * 120)
        print(f"📊 RESULTS:")
        print(f"   Total chunks: {chunk_count}")
        print(f"   Actions detected: {action_count}")
        print(f"   Clean assistant messages: {len(clean_assistant_messages)}")
        print(f"   XML leaked into assistant: {xml_found_in_assistant}")
        
        if xml_found_in_assistant:
            print("❌ TEST FAILED: XML tags found in assistant messages!")
        else:
            print("✅ TEST PASSED: XML tags properly filtered from assistant messages!")
            
        # Show clean message content
        if clean_assistant_messages:
            print(f"\n📝 Clean assistant content: {''.join(clean_assistant_messages)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_xml_filtering()