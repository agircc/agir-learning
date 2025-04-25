import os
import logging
import json
import uuid
from uuid import UUID
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from agir_db.db.session import SessionLocal, get_db
from agir_db.models.user import User
from agir_db.models.process import Process as DBProcess, ProcessNode as DBProcessNode
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.custom_field import CustomField

from src.models.process import Process, ProcessNode
from src.models.agent import Agent
from src.llms import BaseLLMProvider, OpenAIProvider, AnthropicProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMProviderManager:
    """Manages multiple LLM providers based on model names"""
    
    def __init__(self, skip_llm=False):
        """Initialize the LLM provider manager
        
        Args:
            skip_llm: Whether to skip LLM initialization for testing purposes only
        """
        self.providers = {}  # Cache of initialized providers
        self.skip_llm = skip_llm
        
        # No default provider - will be determined by the database values
        self.default_provider = None
    
    def _create_provider(self, provider_type, model_name):
        """Create a new LLM provider
        
        Args:
            provider_type: Type of provider (openai, anthropic, ollama)
            model_name: Name of the model to use
            
        Returns:
            LLM provider instance
        
        Raises:
            ValueError: If provider cannot be initialized
        """
        # Skip LLM is only for testing
        if self.skip_llm:
            logger.info("Skip LLM flag is set, using dummy provider")
            return DummyProvider(model_name=model_name)
            
        if provider_type == 'openai':
            model = model_name or 'gpt-4'
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(f"OPENAI_API_KEY not found in environment. Required for model: {model}")
            
            logger.info(f"Initializing OpenAI provider with model: {model}")
            return OpenAIProvider(model_name=model)
            
        elif provider_type == 'anthropic':
            model = model_name or 'claude-3-opus-20240229'
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError(f"ANTHROPIC_API_KEY not found in environment. Required for model: {model}")
            
            logger.info(f"Initializing Anthropic provider with model: {model}")
            return AnthropicProvider(model_name=model)
            
        elif provider_type == 'ollama':
            model = model_name  # Must be specified
            if not model:
                raise ValueError("Model name must be specified for Ollama provider")
                
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
            
            # Set the OLLAMA_URL environment variable for the provider
            os.environ['OLLAMA_URL'] = ollama_url
            logger.info(f"Initializing Ollama provider with model {model} at {ollama_url}")
            
            # Verify Ollama is running and model is available
            self._verify_ollama_model(model)
            
            return OllamaProvider(model_name=model)
            
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    def _verify_ollama_model(self, model_name):
        """Verify that Ollama is running and the specified model is available
        
        Args:
            model_name: Name of the model to verify
            
        Raises:
            ValueError: If Ollama is not available or model is not found
        """
        try:
            import requests
            base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434').split('/api')[0]
            
            try:
                # Check if Ollama server is running
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    raise ValueError(f"Ollama server returned status code {response.status_code}")
                
                # Check if model is available
                models_data = response.json()
                models = models_data.get('models', [])
                model_names = [m.get('name') for m in models]
                
                if model_name not in model_names:
                    available_models = ", ".join(model_names) if model_names else "none"
                    raise ValueError(
                        f"Model '{model_name}' not found in Ollama. Available models: {available_models}. "
                        f"You may need to run: ollama pull {model_name}"
                    )
                
                logger.info(f"Verified Ollama model '{model_name}' is available")
                
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Failed to connect to Ollama server: {str(e)}")
                
        except ImportError:
            raise ValueError("Requests library not available, cannot verify Ollama model")
        
    def get_provider(self, model_name):
        """Get a provider for the specified model
        
        Args:
            model_name: Name of the model (e.g., "gpt-4", "claude-3", "phi")
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider cannot be initialized
        """
        if not model_name:
            raise ValueError("Model name must be specified")
            
        # If we already have a provider for this model, return it
        if model_name in self.providers:
            return self.providers[model_name]
            
        # Determine provider type from model name
        provider_type = self._detect_provider_type(model_name)
        
        # Create and cache the provider
        provider = self._create_provider(provider_type, model_name)
        self.providers[model_name] = provider
        return provider
    
    def _detect_provider_type(self, model_name):
        """Detect provider type from model name
        
        Args:
            model_name: Name of the model
            
        Returns:
            Provider type string
            
        Raises:
            ValueError: If provider type cannot be determined
        """
        if not model_name:
            raise ValueError("Model name must be specified")
            
        model_name = model_name.lower()
        if model_name in ["gpt-3", "gpt-3.5", "gpt-4", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"] or model_name.startswith("gpt-"):
            return "openai"
        elif model_name in ["claude", "claude-3", "claude-3-opus", "claude-3-sonnet"] or model_name.startswith("claude-"):
            return "anthropic"
        elif model_name in ["llama", "phi", "mixtral", "mistral"] or model_name.startswith("llama-") or model_name.startswith("phi-"):
            return "ollama"
        else:
            raise ValueError(f"Could not determine provider type for model: {model_name}")
