#!/usr/bin/env python3
"""
Test script for FastAPI backend with real API keys
Usage: python test_with_real_keys.py
"""

import json
import requests
from urllib.parse import unquote

def test_chat_api():
    """Test the chat API with your actual API keys"""
    
    print("=== FastAPI Backend Test with Real API Keys ===\n")
    
    # Paste your API keys here (from browser console)
    # Format: {"openai": "sk-...", "anthropic": "sk-ant-...", etc}
    api_keys_json = input("Paste your API keys JSON from browser console: ")
    
    try:
        api_keys = json.loads(api_keys_json)
        print(f"\nFound API keys for providers: {list(api_keys.keys())}")
    except:
        print("Invalid JSON. Please copy the exact output from the browser console.")
        return
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    response = requests.get("http://localhost:8000/api/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test 2: Models endpoint
    print("\n2. Testing models endpoint...")
    response = requests.get("http://localhost:8000/api/models")
    print(f"   Status: {response.status_code}")
    print(f"   Found {len(response.json()['modelList'])} models")
    
    # Test 3: Simple chat (non-streaming)
    print("\n3. Testing simple chat endpoint...")
    
    # Choose a model based on available API keys
    model = "gpt-3.5-turbo" if "openai" in api_keys else "claude-3-haiku-20240307"
    
    response = requests.post(
        "http://localhost:8000/api/chat/simple",
        json={
            "messages": [
                {"role": "user", "content": "Say 'Hello from FastAPI backend!' in exactly 5 words."}
            ],
            "apiKeys": api_keys,
            "model": model
        }
    )
    
    print(f"   Status: {response.status_code}")
    result = response.json()
    if result.get("success"):
        print(f"   AI Response: {result.get('message')}")
    else:
        print(f"   Error: {result.get('error')}")
    
    # Test 4: Streaming chat
    print("\n4. Testing streaming chat endpoint...")
    
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "Count from 1 to 5 slowly."}
            ],
            "apiKeys": api_keys,
            "model": model
        },
        stream=True
    )
    
    print(f"   Status: {response.status_code}")
    print("   Streaming response:")
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # Remove 'data: ' prefix
                try:
                    data = json.loads(data_str)
                    if data.get('type') == 'text':
                        print(f"   > {data.get('content')}", end='', flush=True)
                    elif data.get('type') == 'error':
                        print(f"\n   Error: {data.get('error')}")
                    elif data.get('type') == 'done':
                        print("\n   [Stream completed]")
                except json.JSONDecodeError:
                    pass
    
    print("\n\n=== All tests completed ===")
    
    # Test how frontend would send it
    print("\n5. Testing with headers (like frontend with backend switcher)...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add API keys as headers
    if "openai" in api_keys:
        headers["x-openai-api-key"] = api_keys["openai"]
    if "anthropic" in api_keys:
        headers["x-anthropic-api-key"] = api_keys["anthropic"]
    if "google" in api_keys:
        headers["x-google-api-key"] = api_keys["google"]
    
    response = requests.post(
        "http://localhost:8000/api/chat/simple",
        headers=headers,
        json={
            "messages": [
                {"role": "user", "content": "Say 'Headers test successful!' in 3 words."}
            ],
            "model": model
        }
    )
    
    print(f"   Status: {response.status_code}")
    result = response.json()
    if result.get("success"):
        print(f"   AI Response: {result.get('message')}")
    else:
        print(f"   Error: {result.get('error')}")

if __name__ == "__main__":
    test_chat_api()