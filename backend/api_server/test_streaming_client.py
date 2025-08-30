#!/usr/bin/env python3
"""
Test client for the streaming chat API
Calls the /chat/stream endpoint on port 8084 with a user message
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_streaming_chat():
    """Test the streaming chat API endpoint"""
    
    # API endpoint
    base_url = "http://localhost:8084"
    endpoint = f"{base_url}/chat/stream"
    
    # Test message
    test_message = "Build a simple todo app where I can add tasks and mark them complete"
    
    # Request payload matching ConversationRequest model
    payload = {
        "message": test_message,
        "conversation_id": None,  # Will be auto-generated
        "project_id": None,       # Create mode
        "action_result": False
    }
    
    print(f"🚀 Testing streaming chat API at {endpoint}")
    print(f"📝 Message: {test_message}")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Create HTTP session with proper headers
        timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Send POST request to streaming endpoint
            async with session.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/plain",
                }
            ) as response:
                
                print(f"📡 Response status: {response.status}")
                print(f"📋 Response headers:")
                for key, value in response.headers.items():
                    print(f"  {key}: {value}")
                print("=" * 60)
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error response: {error_text}")
                    return
                
                # Process streaming response
                chunk_count = 0
                conversation_id = None
                project_id = None
                
                async for line in response.content:
                    if not line:
                        continue
                        
                    try:
                        # Decode line
                        line_text = line.decode('utf-8').strip()
                        
                        # Skip empty lines
                        if not line_text:
                            continue
                            
                        # Parse SSE format (data: {...})
                        if line_text.startswith('data: '):
                            json_data = line_text[6:]  # Remove 'data: ' prefix
                            
                            try:
                                chunk_data = json.loads(json_data)
                                chunk_count += 1
                                
                                # Extract key information
                                chunk_type = chunk_data.get('type', 'unknown')
                                data = chunk_data.get('data', {})
                                timestamp = chunk_data.get('timestamp', '')
                                action_id = chunk_data.get('action_id')
                                
                                # Track conversation and project IDs
                                if chunk_type == 'conversation_info':
                                    conversation_id = data.get('conversation_id')
                                    project_id = data.get('project_id')
                                    
                                # Display chunk information
                                print(f"📦 Chunk #{chunk_count} [{chunk_type}]")
                                if action_id:
                                    print(f"   🔧 Action ID: {action_id}")
                                    
                                # Display relevant content based on type
                                if chunk_type == 'conversation_info':
                                    print(f"   💬 Conversation ID: {conversation_id}")
                                    print(f"   📁 Project ID: {project_id}")
                                    if 'time_to_first_chunk_ms' in data:
                                        print(f"   ⚡ Time to first chunk: {data['time_to_first_chunk_ms']}ms")
                                        
                                elif chunk_type == 'assistant_message' or chunk_type == 'text':
                                    content = data.get('content', '')
                                    if content:
                                        # Truncate long content for readability
                                        display_content = content[:100] + "..." if len(content) > 100 else content
                                        print(f"   💭 Content: {display_content}")
                                        
                                elif chunk_type == 'action_start':
                                    action_type = data.get('action_type', 'unknown')
                                    print(f"   🏃 Action: {action_type}")
                                    
                                elif chunk_type == 'action_result':
                                    result = data.get('result', '')
                                    status = data.get('status', 'unknown')
                                    action_type = data.get('action_type', '')
                                    print(f"   ✅ Result: {status}")
                                    if action_type:
                                        print(f"   🔧 Action: {action_type}")
                                    if 'file_path' in data:
                                        print(f"   📄 File: {data['file_path']}")
                                        
                                elif chunk_type == 'error':
                                    error = data.get('error', '')
                                    print(f"   ❌ Error: {error}")
                                    
                                print(f"   🕐 Time: {timestamp}")
                                print("-" * 40)
                                
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Failed to parse JSON: {e}")
                                print(f"   Raw data: {json_data[:200]}...")
                                
                        else:
                            # Non-SSE line, might be important
                            if line_text:
                                print(f"📄 Raw line: {line_text[:200]}...")
                                
                    except UnicodeDecodeError as e:
                        print(f"⚠️ Failed to decode line: {e}")
                        continue
                        
                print("=" * 60)
                print(f"✅ Streaming completed!")
                print(f"📊 Total chunks received: {chunk_count}")
                print(f"💬 Final conversation ID: {conversation_id}")
                print(f"📁 Final project ID: {project_id}")
                print(f"⏰ Completed at: {datetime.now().isoformat()}")
                
    except asyncio.TimeoutError:
        print("⏰ Request timed out after 10 minutes")
    except aiohttp.ClientError as e:
        print(f"🌐 HTTP client error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

async def test_api_health():
    """Test if the API server is running"""
    try:
        base_url = "http://localhost:8084"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API server is healthy: {data}")
                    return True
                else:
                    print(f"❌ API server returned status {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Streaming Chat API Test Client")
    print("=" * 60)
    
    # First check if server is running
    print("🏥 Checking API health...")
    healthy = await test_api_health()
    
    if not healthy:
        print("❌ API server is not responding. Please start the server first:")
        print("   python streaming_api.py")
        return
    
    print("\n🎯 Starting streaming chat test...")
    await test_streaming_chat()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main())