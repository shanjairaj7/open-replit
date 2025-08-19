#!/usr/bin/env python3
"""
Test the streaming API with a normal message that shouldn't contain action tags.
"""

import asyncio
import aiohttp
import json

async def test_normal_message():
    """Test that normal assistant messages without action tags are streamed"""
    
    print("🧪 Testing normal assistant message streaming")
    
    # Test message that should not trigger any actions
    test_message = "what's 2 + 2?"
    
    url = "http://localhost:8084/chat/stream"
    headers = {"Content-Type": "application/json"}
    data = {"message": test_message}
    
    print(f"📤 Sending request: {test_message}")
    
    assistant_messages = []
    action_messages = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                print(f"📊 Response status: {response.status}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_content = line[6:]  # Remove 'data: ' prefix
                        if data_content == '[DONE]':
                            print("✅ Stream completed")
                            break
                        
                        try:
                            event_data = json.loads(data_content)
                            event_type = event_data.get('event')
                            content = event_data.get('content', '')
                            
                            if event_type == 'assistant_message':
                                assistant_messages.append(content)
                                print(f"🤖 ASSISTANT: {content}")
                            elif event_type == 'action_start':
                                action_messages.append(content)
                                print(f"⚡ ACTION: {content}")
                            elif event_type == 'action_result':
                                print(f"✅ RESULT: {content}")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️  Invalid JSON: {data_content}")
                            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print(f"\n📊 TEST RESULTS:")
    print(f"   Assistant messages received: {len(assistant_messages)}")
    print(f"   Action messages received: {len(action_messages)}")
    
    # Check if any assistant messages contain action tags
    has_action_tags = any('<action' in msg for msg in assistant_messages)
    
    if has_action_tags:
        print("❌ FAILED: Assistant messages contain action tags!")
        for i, msg in enumerate(assistant_messages):
            if '<action' in msg:
                print(f"   Message {i+1}: {msg}")
    else:
        print("✅ PASSED: No assistant messages contain action tags")
        
    if len(assistant_messages) > 0:
        print("✅ PASSED: Assistant messages were streamed (as expected for normal message)")
    else:
        print("⚠️  WARNING: No assistant messages received (unexpected for normal message)")
        
    if assistant_messages:
        print("📝 Assistant messages received:")
        for i, msg in enumerate(assistant_messages):
            print(f"   {i+1}: '{msg}'")

if __name__ == "__main__":
    asyncio.run(test_normal_message())