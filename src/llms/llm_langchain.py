# 使用 langchain 调用 llm 模型
import os
import logging
from typing import Dict, Any, Optional, List, Union

from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.llms import Ollama
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.manager import CallbackManager
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain, LLMChain
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
    
    def get_chat_model(self):
        """Get the LangChain Chat model
        
        Returns:
            LangChain Chat model instance
        """
        if self._chat_model is None:
            self._initialize_chat_model()
        return self._chat_model
    
    def _initialize_llm(self):
        """Initialize the LangChain LLM model"""
        raise NotImplementedError("Subclasses must implement _initialize_llm")
    
    def _initialize_chat_model(self):
        """Initialize the LangChain Chat model"""
        raise NotImplementedError("Subclasses must implement _initialize_chat_model")
    
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text completion
        
        Args:
            prompt: Text prompt
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        chat = self.get_chat_model()
        result = chat.predict(prompt)
        return result
    
    def generate_with_history(self, messages: List[Dict[str, str]]) -> str:
        """Generate response with conversation history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Generated response
        """
        chat = self.get_chat_model()
        
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
        response = chat.predict_messages(lc_messages)
        return response.content
    
    def create_chain(self, system_prompt: str = None, memory: bool = True) -> ConversationChain:
        """Create a conversation chain
        
        Args:
            system_prompt: Optional system prompt
            memory: Whether to use conversation memory
            
        Returns:
            ConversationChain instance
        """
        chat = self.get_chat_model()
        
        if memory:
            mem = ConversationBufferMemory(return_messages=True)
            
            # Create the prompt template
            if system_prompt:
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=system_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    HumanMessage(content="{input}")
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    MessagesPlaceholder(variable_name="history"),
                    HumanMessage(content="{input}")
                ])
            
            # Create the chain
            chain = ConversationChain(
                llm=chat,
                prompt=prompt,
                memory=mem,
                verbose=False
            )
        else:
            # No memory version
            if system_prompt:
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content="{input}")
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    HumanMessage(content="{input}")
                ])
            
            chain = LLMChain(llm=chat, prompt=prompt)
        
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
            openai_api_key=api_key
        )
    
    def _initialize_chat_model(self):
        """Initialize the OpenAI Chat model"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self._chat_model = ChatOpenAI(
            model_name=self.model_name,
            temperature=0.7,
            openai_api_key=api_key
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
            anthropic_api_key=api_key
        )
    
    def _initialize_chat_model(self):
        """Initialize the Anthropic Chat model"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self._chat_model = ChatAnthropic(
            model_name=self.model_name,
            temperature=0.7,
            anthropic_api_key=api_key
        )


class OllamaLangChainProvider(BaseLangChainProvider):
    """LangChain provider for Ollama"""
    
    def _initialize_llm(self):
        """Initialize the Ollama LLM"""
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        base_url = ollama_url.split('/api')[0]
        
        self._llm = Ollama(
            model=self.model_name,
            base_url=base_url
        )
    
    def _initialize_chat_model(self):
        """Initialize the Ollama Chat model"""
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        base_url = ollama_url.split('/api')[0]
        
        # Ollama doesn't have a dedicated chat model in LangChain
        # so we'll use the regular LLM interface
        self._chat_model = Ollama(
            model=self.model_name,
            base_url=base_url
        )


def get_langchain_provider(model_name: str) -> BaseLangChainProvider:
    """Get a LangChain provider for the specified model
    
    Args:
        model_name: Name of the model
        
    Returns:
        LangChain provider instance
    """
    model_name = model_name.lower()
    
    if model_name.startswith('gpt-'):
        return OpenAILangChainProvider(model_name=model_name)
    elif model_name.startswith('claude-'):
        return AnthropicLangChainProvider(model_name=model_name)
    else:
        # Default to Ollama for other models
        return OllamaLangChainProvider(model_name=model_name)