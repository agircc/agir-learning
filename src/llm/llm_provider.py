import os
import logging
from typing import Dict, Any, Optional, List, Union

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from src.llm.llm_memory import enhance_messages_with_memories

logger = logging.getLogger(__name__)

class BaseLangChainProvider:
    """Base class for LangChain LLM providers"""
    
    def __init__(self, model_name: str, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """Initialize the LangChain provider
        
        Args:
            model_name: Name of the model
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm = None
    
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
    
    def generate(self, prompt: str, temperature: float = 0.7, user_id: Optional[str] = None) -> str:
        """Generate text completion
        
        Args:
            prompt: Text prompt
            temperature: Sampling temperature
            user_id: Optional user ID for memory integration
            
        Returns:
            Generated text
        """
        chat = self.get_llm()
        
        # Handle memory integration if user_id is provided
        if user_id:
            # Create a SystemMessage with the prompt
            messages = [SystemMessage(content=prompt)]
            result = call_llm_with_memory(chat, messages, user_id, query=prompt)
        else:
            try:
                result = chat.invoke(prompt)
            except (AttributeError, TypeError):
                try:
                    result = chat(prompt)
                except:
                    result = chat.generate(prompt)
        
        # Extract result content
        if hasattr(result, 'content'):
            return result.content
        return str(result)
    
    def generate_with_history(self, messages: List[Dict[str, str]], user_id: Optional[str] = None) -> str:
        """Generate response with conversation history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            user_id: Optional user ID for memory integration
            
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
        
        # Generate response with or without memory
        if user_id:
            # Determine query from the last user message
            query = None
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    query = msg.get('content', '')
                    break
                    
            response = call_llm_with_memory(chat, lc_messages, user_id, query)
        else:
            try:
                response = chat.invoke(lc_messages)
            except (AttributeError, TypeError):
                try:
                    response = chat(lc_messages)
                except:
                    response = chat.generate(lc_messages)
            
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
        
        # Log model information for debugging
        logger.info(f"Creating chain with model: {type(chat).__name__}")
        
        # Create a runnable sequence using the pipe operator
        chain = prompt | chat
        
        # Log the resulting chain type
        logger.info(f"Created chain type: {type(chain).__name__}")
        
        return chain

class OpenAILangChainProvider(BaseLangChainProvider):
    """LangChain provider for OpenAI models"""
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Build ChatOpenAI kwargs
        kwargs = {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'api_key': api_key
        }
        
        # Add max_tokens if specified
        if self.max_tokens is not None:
            kwargs['max_tokens'] = self.max_tokens
        
        self._llm = ChatOpenAI(**kwargs)

class AnthropicLangChainProvider(BaseLangChainProvider):
    """LangChain provider for Anthropic models"""
    
    def _initialize_llm(self):
        """Initialize Anthropic LLM"""
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Build ChatAnthropic kwargs
        kwargs = {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'anthropic_api_key': api_key
        }
        
        # Add max_tokens if specified
        if self.max_tokens is not None:
            kwargs['max_tokens'] = self.max_tokens
        
        self._llm = ChatAnthropic(**kwargs)

def detect_provider_type(model_name: str) -> str:
    """Detect the provider type based on model name
    
    Args:
        model_name: Name of the model
        
    Returns:
        Provider type string ('openai', 'anthropic', etc.)
    """
    model_name = model_name.lower()
    
    # OpenAI models
    if (model_name.startswith("gpt-") or 
        model_name.startswith("text-davinci-") or
        model_name.startswith("o1-") or
        model_name.startswith("o3-")):
        return "openai"
    elif model_name.startswith("claude-"):
        return "anthropic"
    else:
        # Default to OpenAI for unknown models
        logger.warning(f"Unknown model type: {model_name}, defaulting to OpenAI")
        return "openai"

def get_llm_model(model_name: str, temperature: float = 0.7, max_tokens: Optional[int] = None) -> BaseChatModel:
    """Get a LangChain provider for the specified model
    
    Args:
        model_name: Name of the model
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        LangChain provider instance
    """
    if not model_name:
        raise ValueError("Model name must be specified")
    
    provider_type = detect_provider_type(model_name)
    
    if provider_type == 'openai':
        provider = OpenAILangChainProvider(
            model_name=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
    elif provider_type == 'anthropic':
        provider = AnthropicLangChainProvider(
            model_name=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
    
    return provider.get_llm()

def call_llm_with_memory(llm: BaseChatModel, messages: List[BaseMessage], user_id: str, query: str = None) -> Any:
    """Call LLM with memory enhancement
    
    A simplified approach to calling an LLM with memory enhancement.
    
    Args:
        llm: The LLM model to use
        messages: List of messages to send to the LLM
        user_id: User ID for memory lookups
        query: Optional query string for memory retrieval
        
    Returns:
        LLM response
    """
    # Enhance messages with memories if query is provided
    if query:
        messages = enhance_messages_with_memories(messages, user_id, query)
    
    # Try different invocation methods since LangChain versions have different interfaces
    try:
        logger.info(f"Attempting to call LLM using invoke() method")
        return llm.invoke(messages)
    except (AttributeError, TypeError) as e:
        logger.info(f"invoke() failed: {str(e)}, trying direct call")
        try:
            return llm(messages)
        except Exception as e2:
            logger.info(f"Direct call failed: {str(e2)}, trying generate()")
            try:
                return llm.generate(messages)
            except Exception as e3:
                logger.error(f"All LLM call methods failed: {str(e3)}")
                # Return a simple error message as the last resort
                return AIMessage(content="I apologize, but I'm having trouble processing your request.")