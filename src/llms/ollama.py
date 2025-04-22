"""
Ollama LLM Provider
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider."""
    
    def __init__(self, model_name: str, **kwargs):
        """Initialize Ollama provider.
        
        Args:
            model_name: Name of the model to use (e.g., 'phi')
            **kwargs: Additional arguments for the model
        """
        super().__init__(model_name, **kwargs)
        self.api_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/generate')
        logger.info(f"Initialized Ollama provider with model {model_name}")
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                 temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text from the Ollama model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text from the LLM
        """
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            logger.debug(f"Sending request to Ollama: {payload}")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Error generating text with Ollama: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_json(self, prompt: str, schema: Dict[str, Any], 
                     system_prompt: Optional[str] = None, 
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Generate JSON output from the Ollama model.
        
        Args:
            prompt: The user prompt
            schema: JSON schema for validation
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            
        Returns:
            Generated JSON from the LLM
        """
        try:
            # Format the prompt to instruct the model to return valid JSON
            json_prompt = f"""
            {prompt}
            
            Respond with a valid JSON object following this schema:
            {json.dumps(schema, indent=2)}
            
            Your response should be ONLY valid JSON with no additional text or explanation.
            """
            
            # Use the same generate method but tell the model to return JSON
            json_str = self.generate(
                json_prompt, 
                system_prompt=system_prompt or "You are a helpful assistant that only responds with valid JSON.",
                temperature=temperature,
                max_tokens=2000
            )
            
            # Try to parse the response as JSON
            try:
                # Extract JSON from the response if the model included other text
                json_start = json_str.find('{')
                json_end = json_str.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = json_str[json_start:json_end]
                
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Ollama response: {json_str}")
                return {"error": "Failed to parse JSON from model response"}
                
        except Exception as e:
            logger.error(f"Error generating JSON with Ollama: {str(e)}")
            return {"error": str(e)} 