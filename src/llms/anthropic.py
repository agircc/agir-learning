"""
Anthropic LLM Provider
"""

import os
import json
from typing import Dict, Any, List, Optional
import anthropic
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider."""
    
    def __init__(self, model_name: str = "claude-3-opus-20240229", api_key: Optional[str] = None, **kwargs):
        """Initialize Anthropic provider.
        
        Args:
            model_name: Name of the model to use, defaults to claude-3-opus
            api_key: Anthropic API key, defaults to None (will use env var)
            **kwargs: Additional arguments for the Anthropic client
        """
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY env var or pass api_key.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text from Anthropic model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text from the LLM
        """
        message_params = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system_prompt:
            message_params["system"] = system_prompt
            
        response = self.client.messages.create(**message_params)
        return response.content[0].text
    
    def generate_json(self, prompt: str, schema: Dict[str, Any], 
                     system_prompt: Optional[str] = None, 
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Generate JSON output from Anthropic model.
        
        Args:
            prompt: The user prompt
            schema: JSON schema for validation
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            
        Returns:
            Generated JSON from the LLM
        """
        if not system_prompt:
            system_prompt = "You are a helpful assistant. Always respond with valid JSON."
        
        # Add schema to the system prompt
        system_prompt += f"\nOutput must conform to this JSON schema: {json.dumps(schema)}"
        
        # Format prompt to emphasize JSON output
        modified_prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        response_json_str = self.generate(
            prompt=modified_prompt, 
            system_prompt=system_prompt,
            temperature=temperature
        )
        
        # Try to parse the response as JSON
        try:
            # Handle common formatting issues
            response_json_str = response_json_str.strip()
            if response_json_str.startswith("```json"):
                response_json_str = response_json_str.split("```json")[1]
            if response_json_str.endswith("```"):
                response_json_str = response_json_str.split("```")[0]
                
            return json.loads(response_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response_json_str}") 