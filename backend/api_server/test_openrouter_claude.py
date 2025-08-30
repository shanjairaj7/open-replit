#!/usr/bin/env python3
"""
Test file to call OpenRouter OpenAI client with Claude model
Based on the setup from base_test_azure_hybrid.py
"""

import os
from openai import OpenAI
from datetime import datetime

def setup_openrouter_client():
    """Setup OpenRouter client using the same configuration as base_test_azure_hybrid.py"""
    
    # Use the same API key and base URL from the main codebase
    api_key = os.environ.get('OPENAI_KEY', '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')
    base_url = 'https://openrouter.ai/api/v1'
    
    # Create OpenAI client configured for OpenRouter
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers={"x-include-usage": 'true'}
    )
    
    # Use the same Claude model as in base_test_azure_hybrid.py
    model = 'anthropic/claude-3.5-sonnet'
    
    print(f"✅ OpenRouter client initialized")
    print(f"🔗 Base URL: {base_url}")
    print(f"🤖 Model: {model}")
    print(f"🔑 API Key: {api_key[:20]}...")
    
    return client, model

def test_claude_call(client, model, test_message="Hello! Can you tell me about yourself?"):
    """Test calling Claude through OpenRouter"""
    
    print(f"\n🚀 Testing Claude call...")
    print(f"📝 Message: {test_message}")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Make the API call to Claude via OpenRouter
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user", 
                    "content": test_message
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract the response
        claude_response = response.choices[0].message.content
        usage = response.usage
        
        print("✅ Response received!")
        print("=" * 60)
        print("🤖 Claude's Response:")
        print(claude_response)
        print("=" * 60)
        
        if usage:
            print("📊 Usage Statistics:")
            print(f"   📥 Prompt tokens: {usage.prompt_tokens}")
            print(f"   📤 Completion tokens: {usage.completion_tokens}")
            print(f"   📊 Total tokens: {usage.total_tokens}")
        
        print(f"⏰ Completed at: {datetime.now().isoformat()}")
        
        return claude_response
        
    except Exception as e:
        print(f"❌ Error calling Claude: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return None

def test_coding_request(client, model):
    """Test Claude with a coding request similar to what the main system does"""
    
    coding_message = """
    I want to create a simple Python function that calculates the factorial of a number.
    Please write the code with proper error handling and documentation.
    """
    
    print(f"\n🧪 Testing coding request...")
    return test_claude_call(client, model, coding_message)

def test_streaming_call(client, model, test_message="Explain how Python decorators work in simple terms"):
    """Test streaming response from Claude"""
    
    print(f"\n🌊 Testing streaming call...")
    print(f"📝 Message: {test_message}")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Make streaming API call
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": test_message
                }
            ],
            max_tokens=300,
            temperature=0.7,
            stream=True  # Enable streaming
        )
        
        print("🤖 Claude's Streaming Response:")
        print("-" * 40)
        
        full_response = ""
        chunk_count = 0
        
        for chunk in stream:
            chunk_count += 1
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)  # Print in real-time
                full_response += content
        
        print("\n" + "=" * 60)
        print(f"✅ Streaming completed!")
        print(f"📊 Total chunks: {chunk_count}")
        print(f"📝 Response length: {len(full_response)} characters")
        print(f"⏰ Completed at: {datetime.now().isoformat()}")
        
        return full_response
        
    except Exception as e:
        print(f"❌ Error in streaming call: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return None

def main():
    """Main test function"""
    print("🧪 OpenRouter Claude Test Client")
    print("=" * 60)
    
    # Setup client
    try:
        client, model = setup_openrouter_client()
    except Exception as e:
        print(f"❌ Failed to setup client: {e}")
        return
    
    # Test 1: Simple greeting
    print("\n🟢 Test 1: Simple Greeting")
    test_claude_call(client, model, "Hello! Please introduce yourself briefly.")
    
    # Test 2: Coding request
    print("\n🟡 Test 2: Coding Request")
    test_coding_request(client, model)
    
    # Test 3: Streaming response
    print("\n🔵 Test 3: Streaming Response")
    test_streaming_call(client, model, "Explain the benefits of using Python for web development in 3 bullet points.")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()