"""
Base LLM Provider
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, model_name: str, **kwargs):
        """Initialize LLM provider.
        
        Args:
            model_name: Name of the model to use
            **kwargs: Additional arguments for the model
        """
        self.model_name = model_name
        self.kwargs = kwargs
        
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                 temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text from the model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text from the LLM
        """
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Dict[str, Any], 
                     system_prompt: Optional[str] = None, 
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Generate JSON output from the model.
        
        Args:
            prompt: The user prompt
            schema: JSON schema for validation
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            
        Returns:
            Generated JSON from the LLM
        """
        pass 