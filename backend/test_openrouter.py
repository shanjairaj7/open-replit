#!/usr/bin/env python3
"""
Test script to verify OpenRouter integration works with the provided API key
Tests both simple chat and tool calling functionality
"""

import json
import os
from openai import OpenAI

# Use provided OpenRouter API key
API_KEY = "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"

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Tool functions
def get_weather(location: str) -> str:
    """Get weather for a location"""
    return f"Weather in {location}: 22°C, sunny"

def calculate(expression: str) -> str:
    """Calculate math expressions"""
    try:
        result = eval(expression.replace("^", "**"))
        return str(result)
    except:
        return "Calculation error"

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "calculate",
            "description": "Calculate mathematical expressions",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    }
]

tool_handlers = {"get_weather": get_weather, "calculate": calculate}

def execute_tool_call(tool_call):
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    if function_name in tool_handlers:
        result = tool_handlers[function_name](**arguments)
        return {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": result
        }

def agent_chat(user_message: str, model: str = "meta-llama/llama-3.2-3b-instruct"):
    """Universal agent function from documentation"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed for weather or calculations."},
        {"role": "user", "content": user_message}
    ]
    
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        if message.content:
            messages.append({"role": "assistant", "content": message.content})
        
        if message.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                } for tc in message.tool_calls]
            })
            
            for tool_call in message.tool_calls:
                tool_result = execute_tool_call(tool_call)
                messages.append(tool_result)
            continue
        else:
            return message.content

def test_simple_chat():
    """Test 1: Simple question without tools"""
    print("🧪 TEST 1: Simple Chat")
    print("-" * 40)
    
    try:
        result = agent_chat("What is the capital of France?")
        print(f"✅ SUCCESS: {result}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_tool_calling():
    """Test 2: Question requiring tool calls"""
    print("\n🧪 TEST 2: Tool Calling")
    print("-" * 40)
    
    try:
        result = agent_chat("What's the weather in Tokyo and what's 15 * 8?")
        print(f"✅ SUCCESS: {result}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_streaming():
    """Test 3: Streaming response"""
    print("\n🧪 TEST 3: Streaming")
    print("-" * 40)
    
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about Python in 2 sentences."}
        ]
        
        stream = client.chat.completions.create(
            model="meta-llama/llama-3.2-3b-instruct",
            messages=messages,
            stream=True
        )
        
        print("Streaming response: ", end="")
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        
        print("\n✅ Streaming SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Streaming FAILED: {e}")
        return False

def test_different_models():
    """Test 4: Try different cheap models"""
    print("\n🧪 TEST 4: Different Models")
    print("-" * 40)
    
    cheap_models = [
        "meta-llama/llama-3.2-3b-instruct",
        "meta-llama/llama-3.2-1b-instruct", 
        "google/gemini-2.5-flash-image-preview:free"
    ]
    
    success_count = 0
    
    for model in cheap_models:
        try:
            print(f"Testing {model}...")
            result = agent_chat("What is 2+2?", model=model)
            print(f"  ✅ {model}: SUCCESS")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {model}: FAILED - {e}")
    
    print(f"\n{success_count}/{len(cheap_models)} models working")
    return success_count > 0

if __name__ == "__main__":
    print("🚀 OpenRouter Integration Test")
    print("=" * 50)
    print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
    print(f"Base URL: https://openrouter.ai/api/v1")
    print("=" * 50)
    
    tests = [
        test_simple_chat,
        test_tool_calling, 
        test_streaming,
        test_different_models
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"FINAL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Documentation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    print("=" * 50)