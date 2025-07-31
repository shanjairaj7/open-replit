from typing import Dict, Any, List, Optional, AsyncGenerator
import logging
import json
import asyncio
from datetime import datetime
import openai
import anthropic
from groq import AsyncGroq

from app.models.llm_models import ChatRequest, ChatMessage
from app.services.llm_service import LLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class ChatService:
    """Service for handling AI chat interactions"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.llm_service = LLMService()
        
        # Initialize AI clients
        self.openai_client = None
        self.anthropic_client = None
        self.groq_client = None
        
        if "openai" in api_keys:
            self.openai_client = openai.AsyncOpenAI(api_key=api_keys["openai"])
        
        if "anthropic" in api_keys:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=api_keys["anthropic"])
            
        if "groq" in api_keys:
            self.groq_client = AsyncGroq(api_key=api_keys["groq"])
    
    async def process_chat_stream(self, chat_request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Process chat request with streaming response in AI SDK format
        This replaces the complex streaming logic from api.chat.ts
        """
        try:
            # Determine model and provider
            if chat_request.model:
                model_name = chat_request.model
            else:
                # Smart default based on available API keys - always use Kimi for Groq
                if "groq" in self.api_keys:
                    model_name = "moonshotai/kimi-k2-instruct"
                elif "openai" in self.api_keys:
                    model_name = "gpt-4-turbo-preview"
                elif "anthropic" in self.api_keys:
                    model_name = "claude-3-sonnet-20240229"
                elif "google" in self.api_keys:
                    model_name = "gemini-pro"
                else:
                    model_name = "moonshotai/kimi-k2-instruct"  # fallback to Kimi
                    
            model_info = self.llm_service.get_model_by_name(model_name)
            
            if not model_info:
                raise ValueError(f"Model {model_name} not found")
            
            provider = model_info.provider.lower()
            
            # Send initial progress annotation in AI SDK format (data stream)
            progress_data = {
                "type": "progress",
                "label": "response", 
                "status": "in-progress",
                "order": 1,
                "message": f"Processing with {model_info.label}..."
            }
            # AI SDK data format: 2:[data]\n (writeData equivalent)
            yield f'2:{json.dumps([progress_data])}\n'
            
            # Add system prompt based on chat mode (like Remix API does)
            system_prompt = self._get_system_prompt(chat_request.chatMode)
            
            # Convert messages to the format expected by AI APIs  
            formatted_messages = self._format_messages(chat_request.messages, system_prompt)
            
            # Debug: Log message count and total length
            total_chars = sum(len(msg["content"]) for msg in formatted_messages)
            logger.info(f"Sending {len(formatted_messages)} messages, total chars: {total_chars}")
            logger.info(f"Chat mode: {chat_request.chatMode}, System prompt length: {len(system_prompt)} chars")
            logger.info(f"Model requested: {chat_request.model}, Model selected: {model_name}, Provider: {provider}")
            logger.info(f"Model info label: {model_info.label}")
            
            # Process based on provider
            if provider == "openai" and self.openai_client:
                async for chunk in self._process_openai_stream(model_name, formatted_messages):
                    yield chunk
                    
            elif provider == "anthropic" and self.anthropic_client:
                async for chunk in self._process_anthropic_stream(model_name, formatted_messages):
                    yield chunk
                    
            elif provider == "groq" and self.groq_client:
                async for chunk in self._process_groq_stream(model_name, formatted_messages):
                    yield chunk
                    
            else:
                raise ValueError(f"Provider {provider} not available or API key not provided")
            
            # Send completion progress
            completion_data = {
                "type": "progress",
                "label": "response", 
                "status": "complete",
                "order": 2,
                "message": "Response generated"
            }
            yield f'2:{json.dumps([completion_data])}\n'
            
            # Send usage annotation (placeholder - would need real token counting)
            usage_data = {
                "type": "usage",
                "value": {
                    "completionTokens": 100,  # Would calculate actual tokens
                    "promptTokens": 50,
                    "totalTokens": 150
                }
            }
            # Usage is a message annotation, use code 8:
            yield f'8:{json.dumps([usage_data])}\n'
                
        except Exception as e:
            logger.error(f"Error in process_chat_stream: {str(e)}")
            # Send error as text chunk with proper escaping
            error_msg = f"Error: {str(e)}"
            escaped_error = json.dumps(error_msg)[1:-1]
            yield f'0:"{escaped_error}"\n'
    
    async def _process_openai_stream(self, model: str, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Process OpenAI streaming response in AI SDK format"""
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=4000,
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # Properly escape content for JSON
                    escaped_content = json.dumps(content)[1:-1]  # Use json.dumps then remove outer quotes
                    yield f'0:"{escaped_content}"\n'
            
        except Exception as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            # Send error as text chunk with proper escaping
            error_msg = f"Error: {str(e)}"
            escaped_error = json.dumps(error_msg)[1:-1]
            yield f'0:"{escaped_error}"\n'
    
    async def _process_anthropic_stream(self, model: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process Anthropic streaming response"""
        try:
            # Convert OpenAI format to Anthropic format
            system_message = ""
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            stream = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_message,
                messages=anthropic_messages,
                stream=True
            )
            
            content_buffer = ""
            
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    content = chunk.delta.text
                    content_buffer += content
                    
                    yield {
                        "type": "text", 
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            yield {
                "type": "message_complete",
                "full_content": content_buffer,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Anthropic streaming error: {str(e)}")
            yield {
                "type": "error",
                "error": f"Anthropic error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _process_groq_stream(self, model: str, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Process Groq streaming response in AI SDK format - stream raw text like Remix does"""
        try:
            stream = await self.groq_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=8000,  # Increased to handle larger responses
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    
                    # Stream raw text content exactly like Remix does (no parsing)
                    escaped_content = json.dumps(content)[1:-1]
                    yield f'0:"{escaped_content}"\n'
            
        except Exception as e:
            logger.error(f"Groq streaming error: {str(e)}")
            # Send error as text chunk with proper escaping
            error_msg = f"Error: {str(e)}"
            escaped_error = json.dumps(error_msg)[1:-1]
            yield f'0:"{escaped_error}"\n'
    
    async def process_chat_simple(self, chat_request: ChatRequest) -> str:
        """Simple non-streaming chat processing for testing"""
        try:
            if chat_request.model:
                model_name = chat_request.model
            else:
                # Smart default based on available API keys - always use Kimi for Groq
                if "groq" in self.api_keys:
                    model_name = "moonshotai/kimi-k2-instruct"
                elif "openai" in self.api_keys:
                    model_name = "gpt-4-turbo-preview"
                elif "anthropic" in self.api_keys:
                    model_name = "claude-3-sonnet-20240229"
                elif "google" in self.api_keys:
                    model_name = "gemini-pro"
                else:
                    model_name = "moonshotai/kimi-k2-instruct"  # fallback to Kimi
                    
            model_info = self.llm_service.get_model_by_name(model_name)
            
            if not model_info:
                raise ValueError(f"Model {model_name} not found")
            
            provider = model_info.provider.lower()
            system_prompt = self._get_system_prompt(chat_request.chatMode)
            formatted_messages = self._format_messages(chat_request.messages, system_prompt)
            
            if provider == "openai" and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=formatted_messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
            elif provider == "anthropic" and self.anthropic_client:
                system_message = ""
                anthropic_messages = []
                
                for msg in formatted_messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        anthropic_messages.append(msg)
                
                response = await self.anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=1000,
                    system=system_message,
                    messages=anthropic_messages
                )
                return response.content[0].text
                
            elif provider == "groq" and self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model=model_name,
                    messages=formatted_messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
            else:
                raise ValueError(f"Provider {provider} not available")
                
        except Exception as e:
            logger.error(f"Error in simple chat: {str(e)}")
            raise e
    
    def _get_system_prompt(self, chat_mode: str) -> str:
        """Get system prompt based on chat mode (like Remix API)"""
        if chat_mode == "discuss":
            return """You are Claude, an AI assistant created by Anthropic. You are helpful, harmless, and honest.
You are a technical consultant specializing in web development, software architecture, and modern development practices.

When responding to technical questions:
- Provide clear, actionable advice
- Include relevant code examples when helpful
- Consider best practices and modern approaches
- Be concise but thorough

You can help with debugging, architecture decisions, technology choices, and implementation strategies."""
        
        else:  # build mode (default)
            return """You are bolt, an expert AI assistant and exceptional senior software developer with vast knowledge across multiple programming languages, frameworks, and best practices.

<artifact_instructions>
CRITICAL: You MUST always follow the <boltArtifact> format for creating code and files.

1. THINK HOLISTICALLY and COMPREHENSIVELY before creating an artifact.
2. ALWAYS use the latest file modifications and make edits to the latest content.
3. Wrap content in <boltArtifact> tags with title and unique id attributes.
4. Use <boltAction> tags to define specific actions:

   - file: For writing/updating files. Add filePath attribute.
   - shell: For running shell commands. Use && for multiple commands.
   - start: For starting development servers.

5. Action order is CRITICAL. Create files before running commands that use them.
6. Update package.json FIRST, then run npm install.
7. Provide FULL, complete file contents. NEVER use placeholders.
8. Split functionality into smaller modules for best practices.

Example:
<boltArtifact id="react-app" title="React Counter App">
<boltAction type="file" filePath="package.json">
{
  "name": "counter-app",
  "scripts": {"dev": "vite"},
  "dependencies": {"react": "^18.0.0"}
}
</boltAction>
<boltAction type="shell">npm install</boltAction>
<boltAction type="file" filePath="src/App.jsx">
import React, { useState } from 'react';
export default function App() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>Count: {count}</button>;
}
</boltAction>
<boltAction type="start">npm run dev</boltAction>
</boltArtifact>
</artifact_instructions>

Always provide complete, working solutions with proper artifact structure."""
    
    def _format_messages(self, messages: List[ChatMessage], system_prompt: str) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to API format with system prompt"""
        formatted = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
        
        # Add system prompt as first message if not already present
        if not formatted or formatted[0]["role"] != "system":
            formatted.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        # Very aggressive context management to prevent token overflow
        MAX_MESSAGES = 5  # Keep only system + 4 recent messages
        if len(formatted) > MAX_MESSAGES:
            # Keep system message + recent messages
            formatted = [formatted[0]] + formatted[-(MAX_MESSAGES-1):]
            logger.info(f"Truncated conversation to {len(formatted)} messages to fit context")
        
        # Truncate very long individual messages more aggressively
        for msg in formatted:
            if msg["role"] == "system":
                # Keep system prompt shorter
                if len(msg["content"]) > 2000:
                    msg["content"] = msg["content"][:2000] + "...[truncated]"
            else:
                # User/assistant messages even shorter
                if len(msg["content"]) > 1500:
                    msg["content"] = msg["content"][:1500] + "...[truncated]"
                    logger.info(f"Truncated long {msg['role']} message")
        
        return formatted