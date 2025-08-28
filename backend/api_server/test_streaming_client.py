#!/usr/bin/env python3
"""
Test script for the streaming chat client
"""

import asyncio
from streaming_client import StreamingChatClient
import time

async def test_client():
    """Test the streaming client with sample messages"""
    
    print("🧪 Testing Streaming Chat Client")
    print("=" * 50)
    
    # Initialize client
    client = StreamingChatClient(
        base_url="http://localhost:8084",
        output_dir="test_chat_sessions"
    )
    
    # Test messages
    test_messages = [
        "Hello! Can you help me create a simple React component?",
        "Create a todo list component with add and delete functionality",
        "Now add some basic styling to make it look better"
    ]
    
    print(f"📋 Testing with {len(test_messages)} messages...")
    
    try:
        for i, message in enumerate(test_messages, 1):
            print(f"\n📤 Test Message {i}: {message}")
            print("-" * 30)
            
            result = await client.send_message(message)
            
            if result:
                print(f"✅ Message {i} processed successfully")
                print(f"   Response length: {len(result['response'])} chars")
                print(f"   Actions handled: {len(result['actions'])}")
            else:
                print(f"❌ Message {i} failed")
            
            # Small delay between messages
            await asyncio.sleep(2)
        
        # Print final summary
        print("\n" + "=" * 50)
        client.print_session_summary()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting streaming client test...")
    asyncio.run(test_client())