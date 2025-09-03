#!/usr/bin/env python3
"""
Comprehensive LLM Integration using OpenAI SDK
Supports OpenAI, Claude (Anthropic), and Gemini with streaming and tools
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for different LLM providers"""
    provider: str
    api_key: str
    base_url: str
    model: str
    
class LLMClient:
    """Unified client for multiple LLM providers using OpenAI SDK"""
    
    def __init__(self, provider: str = "openai"):
        """Initialize LLM client with specified provider"""
        self.config = self._get_provider_config(provider)
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self.async_client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        print(f"✅ Initialized {self.config.provider} client with model: {self.config.model}")
    
    def _get_provider_config(self, provider: str) -> LLMConfig:
        """Get configuration for different providers"""
        configs = {
            "openai": LLMConfig(
                provider="OpenAI",
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini"
            ),
            "claude": LLMConfig(
                provider="Claude",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                base_url="https://api.anthropic.com/v1",
                model="claude-3-5-sonnet-20241022"
            ),
            "gemini": LLMConfig(
                provider="Gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                model="gemini-2.0-flash-exp"
            )
        }
        
        if provider not in configs:
            raise ValueError(f"Unsupported provider: {provider}. Available: {list(configs.keys())}")
        
        config = configs[provider]
        if not config.api_key:
            env_var = "ANTHROPIC_API_KEY" if provider == "claude" else f"{provider.upper()}_API_KEY"
            raise ValueError(f"API key not found for {provider}. Set {env_var} in .env")
        
        return config
    
    def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Non-streaming chat completion"""
        print(f"🔄 Calling {self.config.provider} chat completion...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                **kwargs
            )
            
            result = {
                "provider": self.config.provider,
                "model": self.config.model,
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                "finish_reason": response.choices[0].finish_reason
            }
            
            print(f"✅ {self.config.provider} response received")
            return result
            
        except Exception as e:
            print(f"❌ Error with {self.config.provider}: {e}")
            return {"error": str(e), "provider": self.config.provider}
    
    def chat_completion_stream(self, messages: List[Dict], **kwargs):
        """Streaming chat completion"""
        print(f"🌊 Starting {self.config.provider} streaming...")
        
        try:
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            full_content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {
                        "provider": self.config.provider,
                        "content": content,
                        "full_content": full_content,
                        "chunk": chunk
                    }
            
            print(f"✅ {self.config.provider} streaming completed")
            
        except Exception as e:
            print(f"❌ Streaming error with {self.config.provider}: {e}")
            yield {"error": str(e), "provider": self.config.provider}
    
    async def async_chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Async non-streaming chat completion"""
        print(f"⚡ Async {self.config.provider} chat completion...")
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                **kwargs
            )
            
            result = {
                "provider": self.config.provider,
                "model": self.config.model,
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                "finish_reason": response.choices[0].finish_reason
            }
            
            print(f"✅ Async {self.config.provider} response received")
            return result
            
        except Exception as e:
            print(f"❌ Async error with {self.config.provider}: {e}")
            return {"error": str(e), "provider": self.config.provider}
    
    async def async_chat_completion_stream(self, messages: List[Dict], **kwargs):
        """Async streaming chat completion"""
        print(f"🌊⚡ Async streaming {self.config.provider}...")
        
        try:
            stream = await self.async_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            full_content = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {
                        "provider": self.config.provider,
                        "content": content,
                        "full_content": full_content,
                        "chunk": chunk
                    }
            
            print(f"✅ Async streaming {self.config.provider} completed")
            
        except Exception as e:
            print(f"❌ Async streaming error with {self.config.provider}: {e}")
            yield {"error": str(e), "provider": self.config.provider}
    
    def chat_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Dict[str, Any]:
        """Chat completion with tool/function calling"""
        print(f"🛠️  {self.config.provider} chat with tools...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                **kwargs
            )
            
            message = response.choices[0].message
            result = {
                "provider": self.config.provider,
                "model": self.config.model,
                "content": message.content,
                "tool_calls": []
            }
            
            # Handle tool calls
            if message.tool_calls:
                print(f"🔧 {len(message.tool_calls)} tool calls detected")
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "function": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })
            
            print(f"✅ {self.config.provider} tools response received")
            return result
            
        except Exception as e:
            print(f"❌ Tools error with {self.config.provider}: {e}")
            return {"error": str(e), "provider": self.config.provider}

# Example tool functions
def get_weather(location: str) -> str:
    """Get weather information for a location"""
    print(f"🌤️  Getting weather for {location}")
    # Mock weather response
    return f"The weather in {location} is sunny and 22°C"

def calculate(expression: str) -> str:
    """Calculate mathematical expressions"""
    print(f"🧮 Calculating: {expression}")
    try:
        # Safe evaluation for basic math
        result = eval(expression.replace("^", "**"))
        return f"The result of {expression} is {result}"
    except:
        return f"Could not calculate: {expression}"

# Tool definitions for OpenAI format
EXAMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state/country"
                    }
                },
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
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to calculate"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

# Tool handler mapping
TOOL_HANDLERS = {
    "get_weather": get_weather,
    "calculate": calculate
}

def handle_tool_calls(tool_calls: List[Dict]) -> List[Dict]:
    """Execute tool calls and return results"""
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call["function"]
        arguments = tool_call["arguments"]
        
        if function_name in TOOL_HANDLERS:
            try:
                result = TOOL_HANDLERS[function_name](**arguments)
                results.append({
                    "tool_call_id": tool_call["id"],
                    "function": function_name,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "tool_call_id": tool_call["id"],
                    "function": function_name,
                    "error": str(e)
                })
        else:
            results.append({
                "tool_call_id": tool_call["id"],
                "function": function_name,
                "error": f"Unknown function: {function_name}"
            })
    
    return results

# Example usage functions
def basic_chat_example(provider: str = "openai"):
    """Example of basic chat completion"""
    print(f"\n{'='*50}")
    print(f"BASIC CHAT EXAMPLE - {provider.upper()}")
    print(f"{'='*50}")
    
    client = LLMClient(provider)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
    
    response = client.chat_completion(messages)
    if "error" not in response:
        print(f"\n🤖 {response['provider']} Response:")
        print(response["content"])
        print(f"\n📊 Usage: {response['usage']}")
    else:
        print(f"\n❌ Error: {response['error']}")

def streaming_chat_example(provider: str = "openai"):
    """Example of streaming chat completion"""
    print(f"\n{'='*50}")
    print(f"STREAMING CHAT EXAMPLE - {provider.upper()}")
    print(f"{'='*50}")
    
    client = LLMClient(provider)
    
    messages = [
        {"role": "system", "content": "You are a creative writer."},
        {"role": "user", "content": "Write a short story about a robot learning to paint."}
    ]
    
    print(f"\n🤖 {provider.upper()} Streaming Response:")
    print("-" * 40)
    
    for chunk in client.chat_completion_stream(messages):
        if "error" not in chunk:
            print(chunk["content"], end="", flush=True)
        else:
            print(f"\n❌ Error: {chunk['error']}")
            break
    
    print("\n" + "-" * 40)

def tools_example(provider: str = "openai"):
    """Example of tool/function calling"""
    print(f"\n{'='*50}")
    print(f"TOOLS EXAMPLE - {provider.upper()}")
    print(f"{'='*50}")
    
    client = LLMClient(provider)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that can use tools to help users."},
        {"role": "user", "content": "What's the weather like in Tokyo and can you calculate 15 * 23?"}
    ]
    
    response = client.chat_with_tools(messages, EXAMPLE_TOOLS)
    
    if "error" not in response:
        print(f"\n🤖 {response['provider']} Response:")
        if response["content"]:
            print(response["content"])
        
        if response["tool_calls"]:
            print(f"\n🔧 Tool Calls:")
            tool_results = handle_tool_calls(response["tool_calls"])
            
            for result in tool_results:
                print(f"  {result['function']}: {result.get('result', result.get('error'))}")
    else:
        print(f"\n❌ Error: {response['error']}")

async def async_example(provider: str = "openai"):
    """Example of async operations"""
    print(f"\n{'='*50}")
    print(f"ASYNC EXAMPLE - {provider.upper()}")
    print(f"{'='*50}")
    
    client = LLMClient(provider)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What are the benefits of renewable energy?"}
    ]
    
    # Async non-streaming
    response = await client.async_chat_completion(messages)
    if "error" not in response:
        print(f"\n🤖 Async {response['provider']} Response:")
        print(response["content"])
    else:
        print(f"\n❌ Error: {response['error']}")
    
    # Async streaming
    print(f"\n🌊 Async Streaming Response:")
    print("-" * 40)
    async for chunk in client.async_chat_completion_stream(messages):
        if "error" not in chunk:
            print(chunk["content"], end="", flush=True)
        else:
            print(f"\n❌ Error: {chunk['error']}")
            break
    print("\n" + "-" * 40)

def compare_providers():
    """Compare responses from different providers"""
    print(f"\n{'='*50}")
    print("PROVIDER COMPARISON")
    print(f"{'='*50}")
    
    prompt = "Explain the concept of artificial intelligence in 2 sentences."
    messages = [
        {"role": "system", "content": "You are a concise and accurate educator."},
        {"role": "user", "content": prompt}
    ]
    
    providers = ["openai", "claude", "gemini"]
    
    for provider in providers:
        try:
            print(f"\n🤖 {provider.upper()}:")
            print("-" * 20)
            
            client = LLMClient(provider)
            response = client.chat_completion(messages)
            
            if "error" not in response:
                print(response["content"])
                if response["usage"]:
                    print(f"Tokens: {response['usage']['total_tokens']}")
            else:
                print(f"❌ Error: {response['error']}")
                
        except Exception as e:
            print(f"❌ Failed to initialize {provider}: {e}")

if __name__ == "__main__":
    print("🚀 LLM Integration Examples")
    print("=" * 50)
    
    # Test which providers are available
    available_providers = []
    for provider in ["openai", "claude", "gemini"]:
        try:
            LLMClient(provider)
            available_providers.append(provider)
            print(f"✅ {provider.upper()} available")
        except Exception as e:
            print(f"❌ {provider.upper()} not available: {e}")
    
    if not available_providers:
        print("\n❌ No providers available. Please check your API keys in .env file.")
        exit(1)
    
    # Run examples with first available provider
    test_provider = available_providers[0]
    print(f"\n🧪 Running examples with {test_provider.upper()}")
    
    # Basic examples
    basic_chat_example(test_provider)
    streaming_chat_example(test_provider)
    tools_example(test_provider)
    
    # Async examples
    print("\n⚡ Running async examples...")
    asyncio.run(async_example(test_provider))
    
    # Provider comparison (if multiple available)
    if len(available_providers) > 1:
        compare_providers()
    
    print(f"\n✅ Examples completed!")