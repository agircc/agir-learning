"""
Fast completion functionality without conversation history.
Uses FAISS-based memory retrieval for optimal performance.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.user import User
from src.llm.llm_provider import get_llm_model
from src.completions.fast_memory_retriever import get_fast_memory_retriever
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Simple user cache for fast lookups
_user_cache: Dict[str, User] = {}
_user_cache_limit = 100

def _get_cached_user(user_id: str) -> Optional[User]:
    """Get user from cache or database"""
    if user_id in _user_cache:
        return _user_cache[user_id]
    
    try:
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        
        # Cache the result (with size limit)
        if user and len(_user_cache) < _user_cache_limit:
            _user_cache[user_id] = user
        
        return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return None
    finally:
        if 'db' in locals():
            db.close()

class FastCompletion:
    """
    Fast completion class without conversation history.
    Optimized for speed with FAISS-based memory retrieval.
    """
    
    def __init__(self, user_id: str, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """
        Initialize fast completion
        
        Args:
            user_id: User ID for context
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
        """
        self.user_id = user_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Get user info
        self.user = _get_cached_user(user_id)
        if not self.user:
            raise ValueError(f"User {user_id} not found")
        
        if not self.user.llm_model:
            raise ValueError(f"User {self.user.username} has no LLM model specified")
        
        # Initialize LLM
        self.llm = get_llm_model(
            self.user.llm_model, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        # Initialize memory retriever
        self.memory_retriever = get_fast_memory_retriever(user_id)
        
        logger.info(f"Initialized fast completion for user {self.user.username} with {self.memory_retriever.get_memory_count()} memories")
    
    def _format_memories_for_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for LLM context"""
        if not memories:
            return "No specific memories available."
        
        formatted = "Relevant knowledge and memories:\n\n"
        for i, memory in enumerate(memories[:3]):  # Limit to top 3 for performance
            formatted += f"{i+1}. {memory['content']}\n\n"
        
        return formatted
    
    def complete(self, prompt: str) -> str:
        """
        Generate completion for the given prompt
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated completion
        """
        try:
            # Search for relevant memories
            relevant_memories = self.memory_retriever.search_memories(prompt, k=3)
            
            # Format memories for context
            memory_context = self._format_memories_for_context(relevant_memories)
            
            # Create system prompt with user context and memories
            system_prompt = f"""You are {self.user.first_name} {self.user.last_name}.
Respond based on your knowledge and the provided context.

{memory_context}

Provide a helpful, accurate response based on the above context."""
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            
            # Generate response
            response = self.llm.invoke(messages)
            
            # Extract content
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "user_id": self.user_id,
            "username": self.user.username,
            "memory_count": self.memory_retriever.get_memory_count(),
            "model": self.user.llm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

def create_fast_completion(user_id: str, temperature: float = 0.7, max_tokens: Optional[int] = None) -> Optional[FastCompletion]:
    """
    Create a fast completion instance
    
    Args:
        user_id: User ID
        temperature: LLM temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        FastCompletion instance or None if failed
    """
    try:
        return FastCompletion(user_id, temperature, max_tokens)
    except Exception as e:
        logger.error(f"Failed to create fast completion: {str(e)}")
        return None 