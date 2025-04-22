"""
OpenAI LLM Provider
"""

import os
import json
from typing import Dict, Any, List, Optional
import openai
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, model_name: str = "gpt-4", api_key: Optional[str] = None, **kwargs):
        """Initialize OpenAI provider.
        
        Args:
            model_name: Name of the model to use, defaults to gpt-4
            api_key: OpenAI API key, defaults to None (will use env var)
            **kwargs: Additional arguments for the OpenAI client
        """
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY env var or pass api_key.")
        
        # 直接初始化OpenAI客户端，不传递任何额外参数
        self.client = openai.OpenAI(api_key=self.api_key)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text from OpenAI model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text from the LLM
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, schema: Dict[str, Any], 
                     system_prompt: Optional[str] = None, 
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Generate JSON output from OpenAI model.
        
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