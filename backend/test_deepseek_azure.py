#!/usr/bin/env python3
"""
Test file for DeepSeek-R1 model on Azure OpenAI
Tests streaming functionality with the OpenAI package
"""

import os
import time
from openai import AzureOpenAI
from typing import Optional

# Azure endpoint configuration
ENDPOINT = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com/"
MODEL_NAME = "DeepSeek-R1-0528"
API_VERSION = "2024-05-01-preview"

# Get API key from environment or use a test key
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "YOUR_API_KEY_HERE")

def test_basic_completion():
    """Test basic non-streaming completion"""
    print("=" * 60)
    print("TEST 1: Basic Completion (Non-Streaming)")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the capital of France? Answer in one sentence."}
            ],
            max_tokens=100,
            temperature=0.7,
        )
        
        print(f"✅ Response received successfully!")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_streaming_completion():
    """Test streaming completion with token counting"""
    print("\n" + "=" * 60)
    print("TEST 2: Streaming Completion")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
    )
    
    try:
        print("Streaming response:")
        print("-" * 40)
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "List 3 things to see in Paris. Be brief."}
            ],
            max_tokens=200,
            temperature=0.7,
            stream=True,
            stream_options={"include_usage": True}  # Request usage info in stream
        )
        
        full_response = ""
        chunk_count = 0
        start_time = time.time()
        
        for chunk in response:
            chunk_count += 1
            
            # Check for content in the chunk
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    full_response += content
            
            # Check for usage information (usually in the last chunk)
            if hasattr(chunk, 'usage') and chunk.usage:
                print(f"\n\n📊 Usage Statistics:")
                print(f"  - Prompt tokens: {chunk.usage.prompt_tokens}")
                print(f"  - Completion tokens: {chunk.usage.completion_tokens}")
                print(f"  - Total tokens: {chunk.usage.total_tokens}")
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "-" * 40)
        print(f"✅ Streaming completed successfully!")
        print(f"📈 Stats:")
        print(f"  - Chunks received: {chunk_count}")
        print(f"  - Total characters: {len(full_response)}")
        print(f"  - Time elapsed: {elapsed_time:.2f} seconds")
        print(f"  - Avg time per chunk: {(elapsed_time/chunk_count*1000):.2f} ms")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Streaming Error: {e}")
        return False

def test_multi_turn_conversation():
    """Test multi-turn conversation with context"""
    print("\n" + "=" * 60)
    print("TEST 3: Multi-Turn Conversation (Streaming)")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
    )
    
    # Build conversation history
    messages = [
        {"role": "system", "content": "You are a helpful travel assistant."},
        {"role": "user", "content": "I'm planning a trip to Tokyo."},
        {"role": "assistant", "content": "Tokyo is an amazing destination! It offers a unique blend of traditional culture and modern technology. You can explore ancient temples, enjoy world-class cuisine, and experience cutting-edge technology all in one city."},
        {"role": "user", "content": "What's the best time to visit?"}
    ]
    
    try:
        print("User: What's the best time to visit?")
        print("\nAssistant: ", end='')
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
            stream=True,
        )
        
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    full_response += content
        
        print("\n" + "-" * 40)
        print("✅ Multi-turn conversation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Multi-turn Error: {e}")
        return False

def test_reasoning_task():
    """Test DeepSeek's reasoning capabilities with a complex task"""
    print("\n" + "=" * 60)
    print("TEST 4: Reasoning Task (Streaming)")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
    )
    
    reasoning_prompt = """Solve this step by step:
    If a train travels at 60 mph for 2 hours, then at 80 mph for 3 hours, 
    what is the total distance traveled and average speed?"""
    
    try:
        print(f"Problem: {reasoning_prompt}")
        print("\nSolution: ")
        print("-" * 40)
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful math tutor. Show your reasoning step by step."},
                {"role": "user", "content": reasoning_prompt}
            ],
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent reasoning
            stream=True,
        )
        
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    full_response += content
        
        print("\n" + "-" * 40)
        print("✅ Reasoning task completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Reasoning Task Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n🚀 Starting DeepSeek-R1 Azure OpenAI Tests")
    print(f"📍 Endpoint: {ENDPOINT}")
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"🔑 API Key: {'Set' if API_KEY != 'YOUR_API_KEY_HERE' else 'Not Set'}")
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️  Warning: Please set your API key!")
        print("   export AZURE_OPENAI_API_KEY='your-api-key'")
        print("   or update the API_KEY variable in this script")
        return
    
    # Run all tests
    tests = [
        ("Basic Completion", test_basic_completion),
        ("Streaming Completion", test_streaming_completion),
        ("Multi-Turn Conversation", test_multi_turn_conversation),
        ("Reasoning Task", test_reasoning_task),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed successfully!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()