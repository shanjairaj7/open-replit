from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, AsyncGenerator
import json
import logging
import asyncio
from datetime import datetime

from app.models.llm_models import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/chat")
async def chat_endpoint(
    chat_request: ChatRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    openai_api_key: Optional[str] = Header(None, alias="x-openai-api-key"),
    anthropic_api_key: Optional[str] = Header(None, alias="x-anthropic-api-key"),
    google_api_key: Optional[str] = Header(None, alias="x-google-api-key"),
    groq_api_key: Optional[str] = Header(None, alias="x-groq-api-key")
) -> StreamingResponse:
    """
    Main chat endpoint - replaces api.chat.ts
    Handles AI chat interactions with streaming responses
    """
    try:
        logger.info("Chat request received", extra={
            "message_count": len(chat_request.messages),
            "chat_mode": chat_request.chatMode,
            "model": chat_request.model,
            "provider": chat_request.provider
        })
        
        # Extract API keys from headers first, then fallback to body
        api_keys = {}
        
        # Priority 1: Headers (for security)
        if openai_api_key:
            api_keys["openai"] = openai_api_key
        if anthropic_api_key:
            api_keys["anthropic"] = anthropic_api_key
        if google_api_key:
            api_keys["google"] = google_api_key
        if groq_api_key:
            api_keys["groq"] = groq_api_key
            
        # Priority 2: Request body (for compatibility with frontend)
        if chat_request.apiKeys:
            # Normalize API key names to lowercase for case-insensitive matching
            normalized_request_keys = {k.lower(): v for k, v in chat_request.apiKeys.items() if v}
            
            if "openai" in normalized_request_keys and "openai" not in api_keys:
                api_keys["openai"] = normalized_request_keys["openai"]
            if "anthropic" in normalized_request_keys and "anthropic" not in api_keys:
                api_keys["anthropic"] = normalized_request_keys["anthropic"]
            if "google" in normalized_request_keys and "google" not in api_keys:
                api_keys["google"] = normalized_request_keys["google"]
            if "groq" in normalized_request_keys and "groq" not in api_keys:
                api_keys["groq"] = normalized_request_keys["groq"]
            # Handle AmazonBedrock -> amazon mapping
            if "amazonbedrock" in normalized_request_keys and "amazon" not in api_keys:
                api_keys["amazon"] = normalized_request_keys["amazonbedrock"]
        
        # Initialize chat service
        chat_service = ChatService(api_keys=api_keys)
        
        # Process the chat request and return streaming response
        async def generate_chat_response() -> AsyncGenerator[str, None]:
            try:
                async for chunk in chat_service.process_chat_stream(chat_request):
                    # Stream chunks directly in AI SDK format
                    yield chunk
                    
            except Exception as e:
                logger.error(f"Error in chat stream: {str(e)}")
                # Send error as text chunk
                yield f'0:"Error: {str(e)}"\n'
        
        return StreamingResponse(
            generate_chat_response(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.post("/chat/simple")
async def simple_chat_endpoint(
    chat_request: ChatRequest,
    request: Request,
    openai_api_key: Optional[str] = Header(None, alias="x-openai-api-key"),
    anthropic_api_key: Optional[str] = Header(None, alias="x-anthropic-api-key"),
    google_api_key: Optional[str] = Header(None, alias="x-google-api-key"),
    groq_api_key: Optional[str] = Header(None, alias="x-groq-api-key")
) -> ChatResponse:
    """
    Simple non-streaming chat endpoint for testing
    """
    try:
        logger.info("Simple chat request received")
        
        # Extract API keys from headers first, then fallback to body
        api_keys = {}
        if openai_api_key:
            api_keys["openai"] = openai_api_key
        if anthropic_api_key:
            api_keys["anthropic"] = anthropic_api_key
        if google_api_key:
            api_keys["google"] = google_api_key
        if groq_api_key:
            api_keys["groq"] = groq_api_key
            
        # Fallback to request body
        if chat_request.apiKeys:
            # Normalize API key names to lowercase for case-insensitive matching
            normalized_request_keys = {k.lower(): v for k, v in chat_request.apiKeys.items() if v}
            
            if "openai" in normalized_request_keys and "openai" not in api_keys:
                api_keys["openai"] = normalized_request_keys["openai"]
            if "anthropic" in normalized_request_keys and "anthropic" not in api_keys:
                api_keys["anthropic"] = normalized_request_keys["anthropic"]
            if "google" in normalized_request_keys and "google" not in api_keys:
                api_keys["google"] = normalized_request_keys["google"]
            if "groq" in normalized_request_keys and "groq" not in api_keys:
                api_keys["groq"] = normalized_request_keys["groq"]
            # Handle AmazonBedrock -> amazon mapping
            if "amazonbedrock" in normalized_request_keys and "amazon" not in api_keys:
                api_keys["amazon"] = normalized_request_keys["amazonbedrock"]
        
        chat_service = ChatService(api_keys=api_keys)
        response = await chat_service.process_chat_simple(chat_request)
        
        return ChatResponse(
            success=True,
            message=response
        )
        
    except Exception as e:
        logger.error(f"Error in simple chat: {str(e)}")
        return ChatResponse(
            success=False,
            error=str(e)
        )