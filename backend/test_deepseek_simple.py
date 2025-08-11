#!/usr/bin/env python3
"""
Simple test for DeepSeek-R1 streaming on Azure OpenAI
Using the exact configuration from the Azure mode
"""

from openai import AzureOpenAI

# Your Azure configuration
endpoint = "https://rajsu-m9qoo96e-eastus2.openai.azure.com/"
model_name = "DeepSeek-R1-0528"
deployment = "DeepSeek-R1-0528"
api_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
api_version = "2024-12-01-preview"

def test_streaming():
    """Test streaming with DeepSeek model"""
    print("🚀 Testing DeepSeek-R1 Streaming on Azure OpenAI")
    print("=" * 60)
    
    # Create client
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    print(f"📍 Endpoint: {endpoint}")
    print(f"🤖 Model: {deployment}")
    print(f"📝 Sending request...\n")
    
    try:
        # Create streaming completion
        response = client.chat.completions.create(
            model=deployment,  # Use deployment name
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "What are 3 key features of Python? List them briefly."}
            ],
            max_tokens=200,
            temperature=0.7,
            stream=True,
            stream_options={"include_usage": True}  # Get usage info
        )
        
        print("📨 Response (streaming):")
        print("-" * 40)
        
        # Process stream
        full_response = ""
        chunk_count = 0
        usage_info = None
        
        for chunk in response:
            chunk_count += 1
            
            # Extract content from chunk
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    print(content, end='', flush=True)
                    full_response += content
            
            # Check for usage info (usually in last chunk)
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
        
        print("\n" + "-" * 40)
        
        # Print statistics
        print(f"\n✅ Streaming completed successfully!")
        print(f"\n📊 Statistics:")
        print(f"  • Chunks received: {chunk_count}")
        print(f"  • Response length: {len(full_response)} characters")
        
        if usage_info:
            print(f"\n💰 Token Usage:")
            print(f"  • Prompt tokens: {usage_info.prompt_tokens}")
            print(f"  • Completion tokens: {usage_info.completion_tokens}")
            print(f"  • Total tokens: {usage_info.total_tokens}")
        else:
            print("\n💰 Token Usage: Not available (may need stream_options)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Print more details if available
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
        
        return False

def test_non_streaming():
    """Test non-streaming completion for comparison"""
    print("\n" + "=" * 60)
    print("🚀 Testing Non-Streaming Completion")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "What is 2 + 2?"}
            ],
            max_tokens=50,
            temperature=0,
        )
        
        print(f"Response: {response.choices[0].message.content}")
        
        if response.usage:
            print(f"\n💰 Token Usage:")
            print(f"  • Prompt tokens: {response.usage.prompt_tokens}")
            print(f"  • Completion tokens: {response.usage.completion_tokens}")
            print(f"  • Total tokens: {response.usage.total_tokens}")
        
        print("\n✅ Non-streaming test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Run both tests
    print("🧪 DeepSeek-R1 Azure OpenAI Test Suite\n")
    
    # Test non-streaming first (simpler)
    non_streaming_passed = test_non_streaming()
    
    # Test streaming
    streaming_passed = test_streaming()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Non-streaming: {'✅ PASSED' if non_streaming_passed else '❌ FAILED'}")
    print(f"Streaming: {'✅ PASSED' if streaming_passed else '❌ FAILED'}")
    
    if non_streaming_passed and streaming_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")