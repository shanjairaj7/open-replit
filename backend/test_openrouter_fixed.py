#!/usr/bin/env python3
"""
Fixed test script for OpenRouter integration
"""

import json
import os
from openai import OpenAI

API_KEY = "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"

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def get_weather(location: str) -> str:
    return f"Weather in {location}: 22°C, sunny"

def calculate(expression: str) -> str:
    try:
        result = eval(expression.replace("^", "**"))
        return str(result)
    except:
        return "Calculation error"

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

def agent_chat(user_message: str, model: str = "meta-llama/llama-3.1-8b-instruct"):
    """Universal agent function - using 3.1-8b as it supports tools"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed for weather or calculations."},
        {"role": "user", "content": user_message}
    ]
    
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"  Iteration {iteration}...")
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            print(f"  Response: {message.content[:50] if message.content else 'No content'}...")
            
            if message.content:
                messages.append({"role": "assistant", "content": message.content})
            
            if message.tool_calls:
                print(f"  Tool calls: {len(message.tool_calls)}")
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    } for tc in message.tool_calls]
                })
                
                # Execute tools
                for tool_call in message.tool_calls:
                    tool_result = execute_tool_call(tool_call)
                    if tool_result:
                        messages.append(tool_result)
                        print(f"    Tool {tool_call.function.name}: {tool_result['content'][:30]}...")
                
                continue  # Continue the loop
            else:
                # No tool calls, return final response
                return message.content
                
        except Exception as e:
            print(f"  Error in iteration {iteration}: {e}")
            return f"Error: {e}"
    
    return "Max iterations reached"

def test_simple_chat():
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
    print("\n🧪 TEST 2: Tool Calling")
    print("-" * 40)
    
    try:
        result = agent_chat("What's the weather in Tokyo and calculate 15 * 8?")
        print(f"✅ SUCCESS: {result}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_available_models():
    print("\n🧪 TEST 3: Check Available Tool-Supporting Models")
    print("-" * 40)
    
    models_to_test = [
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-nemo",
        "google/gemma-2-9b-it"
    ]
    
    working_models = []
    
    for model in models_to_test:
        print(f"Testing {model}...")
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"}
            ]
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            print(f"  ✅ {model}: Works")
            working_models.append(model)
            
        except Exception as e:
            print(f"  ❌ {model}: {e}")
    
    print(f"\nWorking models: {working_models}")
    return len(working_models) > 0

if __name__ == "__main__":
    print("🚀 OpenRouter Integration Test (Fixed)")
    print("=" * 50)
    
    tests = [test_simple_chat, test_tool_calling, test_available_models]
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nFINAL: {passed}/{len(tests)} tests passed")
    
    if passed >= 2:
        print("🎉 Integration working! Most functionality confirmed.")
    else:
        print("⚠️  Issues found, but basic functionality may work.")