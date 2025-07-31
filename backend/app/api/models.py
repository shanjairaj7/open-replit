from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.services.llm_service import LLMService
from app.models.llm_models import ModelInfo, ProviderInfo

router = APIRouter()
logger = logging.getLogger(__name__)

class ModelsResponse(BaseModel):
    modelList: List[ModelInfo]
    providers: List[ProviderInfo]
    defaultProvider: ProviderInfo

@router.get("/models", response_model=ModelsResponse)
async def get_models(request: Request) -> ModelsResponse:
    """Get available AI models and providers - replaces api.models.ts"""
    try:
        # Get API keys from request headers or cookies
        # For now, we'll return static models, but this can be enhanced
        # to check API keys and return dynamic models
        
        llm_service = LLMService()
        
        # Get all providers
        providers = llm_service.get_all_providers()
        default_provider = llm_service.get_default_provider()
        
        # Get models for all providers
        all_models = []
        for provider in providers:
            models = llm_service.get_models_for_provider(provider.name)
            all_models.extend(models)
        
        return ModelsResponse(
            modelList=all_models,
            providers=providers,
            defaultProvider=default_provider
        )
        
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting models: {str(e)}")

@router.get("/models/{provider}")
async def get_models_for_provider(provider: str, request: Request) -> Dict[str, Any]:
    """Get models for specific provider"""
    try:
        llm_service = LLMService()
        models = llm_service.get_models_for_provider(provider)
        
        return {
            "provider": provider,
            "models": models
        }
        
    except Exception as e:
        logger.error(f"Error getting models for provider {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting models for provider: {str(e)}")