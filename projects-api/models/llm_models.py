from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ModelInfo(BaseModel):
    name: str
    label: str
    provider: str
    maxTokenAllowed: int
    inputTokenPricing: Optional[float] = None
    outputTokenPricing: Optional[float] = None
    description: Optional[str] = None

class ProviderInfo(BaseModel):
    name: str
    staticModels: List[ModelInfo]
    getApiKeyLink: Optional[str] = None
    labelForGetApiKey: Optional[str] = None
    icon: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    files: Optional[Dict[str, Any]] = None
    promptId: Optional[str] = None
    contextOptimization: bool = True
    chatMode: str = "build"  # 'discuss' or 'build' 
    designScheme: Optional[Dict[str, Any]] = None
    maxLLMSteps: int = 5
    supabase: Optional[Dict[str, Any]] = None
    # API keys can be passed in body or headers
    apiKeys: Optional[Dict[str, str]] = None
    model: Optional[str] = None
    provider: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None