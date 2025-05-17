# 使用 langchain 调用 llm 模型
import os
import logging
from typing import Dict, Any, Optional, List, Union

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)

class BaseLangChainProvider:
    """Base class for LangChain LLM providers"""
    
    def __init__(self, model_name: str):
        """Initialize the LangChain provider
        
        Args:
            model_name: Name of the model
        """
        self.model_name = model_name
        self._llm = None
        self._chat_model = None
    
    def get_llm(self):
        """Get the LangChain LLM model
        
        Returns:
            LangChain LLM instance
        """
        if self._llm is None:
            self._initialize_llm()
        return self._llm
    
    def _initialize_llm(self):
        """Initialize the LangChain LLM model"""
        raise NotImplementedError("Subclasses must implement _initialize_llm")
    
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text completion
        
        Args:
            prompt: Text prompt
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        chat = self.get_llm()
        result = chat.invoke(prompt)
        
        # Extract result content
        if hasattr(result, 'content'):
            return result.content
        return str(result)
    
    def generate_with_history(self, messages: List[Dict[str, str]]) -> str:
        """Generate response with conversation history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Generated response
        """
        chat = self.get_llm()
        
        # Convert messages to LangChain format
        lc_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                lc_messages.append(SystemMessage(content=content))
            elif role == 'user':
                lc_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                lc_messages.append(AIMessage(content=content))
        
        # Generate response
        response = chat.invoke(lc_messages)
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    def create_chain(self, system_prompt: str = None, memory: bool = True):
        """Create a conversation chain using updated LangChain practices
        
        Args:
            system_prompt: Optional system prompt
            memory: Whether to include memory placeholders in the prompt
            
        Returns:
            Runnable instance (RunnableSequence)
        """
        chat = self.get_llm()
        
        # Create the prompt template
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # Add history placeholder if memory is enabled
        if memory:
            messages.append(MessagesPlaceholder(variable_name="chat_history"))
        
        # Add user input placeholder
        messages.append(HumanMessage(content="{input}"))
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # Create a runnable sequence using the pipe operator
        chain = prompt | chat
        
        return chain

class OpenAILangChainProvider(BaseLangChainProvider):
    """LangChain provider for OpenAI"""
    
    def _initialize_llm(self):
        """Initialize the OpenAI LLM"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self._llm = ChatOpenAI(
            model_name=self.model_name,
            temperature=0.7,
            api_key=api_key
        )

class AnthropicLangChainProvider(BaseLangChainProvider):
    """LangChain provider for Anthropic"""
    
    def _initialize_llm(self):
        """Initialize the Anthropic LLM"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self._llm = ChatAnthropic(
            model_name=self.model_name,
            temperature=0.7,
            api_key=api_key
        )

def detect_provider_type(model_name: str) -> str:
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
    else:
        raise ValueError(f"Could not determine provider type for model: {model_name}")


def get_langchain_provider(model_name: str) -> BaseLangChainProvider:
    """Get a LangChain provider for the specified model
    
    Args:
        model_name: Name of the model
        
    Returns:
        LangChain provider instance
    """
    if not model_name:
        raise ValueError("Model name must be specified")
    
    provider_type = detect_provider_type(model_name)
    
    if provider_type == 'openai':
        provider = OpenAILangChainProvider(model_name=model_name)
        
    elif provider_type == 'anthropic':
        provider = AnthropicLangChainProvider(model_name=model_name)
    
    return provider

class LLMProviderManager:
    """Manages LLM providers based on model names (always using LangChain)"""
    
    def __init__(self, skip_llm=False):
        """Initialize the LLM provider manager
        
        Args:
            skip_llm: Whether to skip LLM initialization for testing purposes only
        """
        self.providers = {}  # Cache of initialized providers
        
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
        
        # Create and cache the provider
        provider = get_langchain_provider(model_name)
        self.providers[model_name] = provider
        return provider