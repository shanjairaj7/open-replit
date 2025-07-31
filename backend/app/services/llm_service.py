from typing import List, Dict, Any, Optional
import logging

from app.models.llm_models import ModelInfo, ProviderInfo

logger = logging.getLogger(__name__)

class LLMService:
    """Service for managing LLM providers and models"""
    
    def __init__(self):
        self._providers: List[ProviderInfo] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize static provider and model information"""
        
        # OpenAI Models
        openai_models = [
            ModelInfo(
                name="gpt-4-turbo-preview",
                label="GPT-4 Turbo",
                provider="OpenAI",
                maxTokenAllowed=128000,
                inputTokenPricing=0.01,
                outputTokenPricing=0.03,
                description="Most capable GPT-4 model"
            ),
            ModelInfo(
                name="gpt-4",
                label="GPT-4",
                provider="OpenAI", 
                maxTokenAllowed=8192,
                inputTokenPricing=0.03,
                outputTokenPricing=0.06
            ),
            ModelInfo(
                name="gpt-3.5-turbo",
                label="GPT-3.5 Turbo",
                provider="OpenAI",
                maxTokenAllowed=16385,
                inputTokenPricing=0.001,
                outputTokenPricing=0.002
            )
        ]
        
        # Anthropic Models
        anthropic_models = [
            ModelInfo(
                name="claude-3-opus-20240229",
                label="Claude 3 Opus",
                provider="Anthropic",
                maxTokenAllowed=200000,
                inputTokenPricing=0.015,
                outputTokenPricing=0.075
            ),
            ModelInfo(
                name="claude-3-sonnet-20240229",
                label="Claude 3 Sonnet", 
                provider="Anthropic",
                maxTokenAllowed=200000,
                inputTokenPricing=0.003,
                outputTokenPricing=0.015
            ),
            ModelInfo(
                name="claude-3-haiku-20240307",
                label="Claude 3 Haiku",
                provider="Anthropic",
                maxTokenAllowed=200000,
                inputTokenPricing=0.00025,
                outputTokenPricing=0.00125
            )
        ]
        
        # Google Models
        google_models = [
            ModelInfo(
                name="gemini-pro",
                label="Gemini Pro",
                provider="Google",
                maxTokenAllowed=32768,
                inputTokenPricing=0.0005,
                outputTokenPricing=0.0015
            )
        ]
        
        # Groq Models
        groq_models = [
            ModelInfo(
                name="llama3-8b-8192",
                label="Llama 3 8B",
                provider="Groq",
                maxTokenAllowed=8192,
                inputTokenPricing=0.00005,
                outputTokenPricing=0.00008
            ),
            ModelInfo(
                name="llama3-70b-8192", 
                label="Llama 3 70B",
                provider="Groq",
                maxTokenAllowed=8192,
                inputTokenPricing=0.00059,
                outputTokenPricing=0.00079
            ),
            ModelInfo(
                name="mixtral-8x7b-32768",
                label="Mixtral 8x7B",
                provider="Groq",
                maxTokenAllowed=32768,
                inputTokenPricing=0.00024,
                outputTokenPricing=0.00024
            ),
            ModelInfo(
                name="moonshotai/kimi-k2-instruct",
                label="Kimi K2 Instruct",
                provider="Groq",
                maxTokenAllowed=128000,
                inputTokenPricing=0.0001,
                outputTokenPricing=0.0002
            )
        ]
        
        self._providers = [
            ProviderInfo(
                name="OpenAI",
                staticModels=openai_models,
                getApiKeyLink="https://platform.openai.com/account/api-keys",
                labelForGetApiKey="OpenAI API Key",
                icon="openai"
            ),
            ProviderInfo(
                name="Anthropic", 
                staticModels=anthropic_models,
                getApiKeyLink="https://console.anthropic.com/",
                labelForGetApiKey="Anthropic API Key",
                icon="anthropic"
            ),
            ProviderInfo(
                name="Google",
                staticModels=google_models,
                getApiKeyLink="https://makersuite.google.com/app/apikey",
                labelForGetApiKey="Google AI API Key", 
                icon="google"
            ),
            ProviderInfo(
                name="Groq",
                staticModels=groq_models,
                getApiKeyLink="https://console.groq.com/keys",
                labelForGetApiKey="Groq API Key",
                icon="groq"
            )
        ]
    
    def get_all_providers(self) -> List[ProviderInfo]:
        """Get all available providers"""
        return self._providers
    
    def get_default_provider(self) -> ProviderInfo:
        """Get the default provider (OpenAI)"""
        return self._providers[0]  # OpenAI as default
    
    def get_models_for_provider(self, provider_name: str) -> List[ModelInfo]:
        """Get models for a specific provider"""
        for provider in self._providers:
            if provider.name.lower() == provider_name.lower():
                return provider.staticModels
        return []
    
    def get_model_by_name(self, model_name: str) -> Optional[ModelInfo]:
        """Get a specific model by name"""
        for provider in self._providers:
            for model in provider.staticModels:
                if model.name == model_name:
                    return model
        return None
    
    def get_provider_by_name(self, provider_name: str) -> Optional[ProviderInfo]:
        """Get a provider by name"""
        for provider in self._providers:
            if provider.name.lower() == provider_name.lower():
                return provider
        return None