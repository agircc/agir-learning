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
                "num_predict": max_tokens,  # Ollama uses num_predict instead of max_tokens
                "stream": False  # Get the complete response, not a stream
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            logger.debug(f"Sending request to Ollama: {payload}")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Parse the JSON response
            result = response.json()
            logger.debug(f"Received response from Ollama: {result}")
            
            # Extract the response text from the result
            return result.get("response", "")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error with Ollama: {str(e)}")
            return f"Error: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from Ollama: {str(e)}")
            return f"Error parsing response: {str(e)}"
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
            
            # Configure the request to use either "format": "json" or provide the schema
            # depending on the Ollama model's capabilities
            payload = {
                "model": self.model_name,
                "prompt": json_prompt,
                "temperature": temperature,
                "num_predict": 2000,  # Ollama uses num_predict instead of max_tokens
                "stream": False,
                "format": schema  # Provide the full schema for structured output
            }
            
            if system_prompt:
                payload["system"] = system_prompt or "You are a helpful assistant that only responds with valid JSON."
                
            logger.debug(f"Sending JSON request to Ollama: {payload}")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Parse the JSON response from Ollama
            result = response.json()
            logger.debug(f"Received JSON response from Ollama: {result}")
            
            # Extract the response text which contains the JSON string
            json_str = result.get("response", "{}")
            
            try:
                # Parse the JSON string into a Python dictionary
                # The response field contains the JSON as a string that needs to be parsed
                parsed_json = json.loads(json_str)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Ollama response: {json_str} - Error: {str(e)}")
                # Add additional debug info in case of error
                logger.error(f"Full Ollama response: {result}")
                return {"error": "Failed to parse JSON from model response"}
                
        except Exception as e:
            logger.error(f"Error generating JSON with Ollama: {str(e)}")
            return {"error": str(e)} 