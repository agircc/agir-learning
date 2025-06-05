"""
Chat with learner module - allows direct conversation with a learner user.
This module uses the learner's memories to provide context-aware responses.
"""

import logging
import uuid
import sys
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
import json
import argparse

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.memory import UserMemory
from src.common.utils.memory_utils import get_user_memories, search_user_memories, add_user_memory
from src.completions.fast_memory_retriever import get_fast_memory_retriever
from src.llm.llm_provider import get_llm_model

from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class LearnerChatSession:
    """
    Class to manage a chat session with a learner.
    """
    
    def __init__(self, username: str = None, user_id: str = None, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """
        Initialize a chat session with a learner.
        
        Args:
            username: Username of the learner to chat with
            user_id: User ID of the learner to chat with (alternative to username)
            temperature: Sampling temperature for the LLM (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
        """
        if not username and not user_id:
            raise ValueError("Either username or user_id must be provided")
        
        self.db = next(get_db())
        self.user = self._find_user(username, user_id)
        
        if not self.user:
            raise ValueError(f"User with {'username ' + username if username else 'ID ' + user_id} not found")
        
        if not self.user.llm_model:
            raise ValueError(f"User {self.user.username} has no LLM model specified")
        
        self.model_name = self.user.llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = get_llm_model(self.model_name, temperature=temperature, max_tokens=max_tokens)
        self.chat_history = []
        
        # Use cached FastMemoryRetriever instead of loading memories directly
        self.memory_retriever = get_fast_memory_retriever(str(self.user.id))
        
        logger.info(f"Initialized chat session with learner {self.user.username} using model {self.model_name}, temperature={temperature}, max_tokens={max_tokens}")
        logger.info(f"Loaded {self.memory_retriever.get_memory_count()} memories using cached retriever")
    
    def _find_user(self, username: str = None, user_id: str = None) -> Optional[User]:
        """
        Find a user by username or ID.
        
        Args:
            username: Username to search for
            user_id: User ID to search for
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        try:
            if username:
                return self.db.query(User).filter(User.username == username).first()
            elif user_id:
                return self.db.query(User).filter(User.id == user_id).first()
            return None
        except Exception as e:
            logger.error(f"Error finding user: {str(e)}")
            return None
    
    def _format_memories_for_context(self) -> str:
        """
        Format memories for inclusion in the LLM context.
        
        Returns:
            str: Formatted memories
        """
        if not hasattr(self, 'memories') or not self.memories:
            return "You have no specific memories to draw from."
        
        formatted = "Your relevant memories and learned knowledge:\n\n"
        for i, memory in enumerate(self.memories):
            formatted += f"{i+1}. {memory['content']}\n\n"
        
        return formatted
    
    def _search_memories(self, query: str, limit: int = 3) -> None:
        """
        Search memories related to a query and update the current memories.
        Uses cached FastMemoryRetriever for better performance.
        
        Args:
            query: Search query
            limit: Maximum number of memories to retrieve
        """
        try:
            # Use cached memory retriever instead of rebuilding FAISS index
            relevant_memories = self.memory_retriever.search_memories(query, k=limit)
            
            if relevant_memories:
                # Convert FastMemoryRetriever format to expected format
                self.memories = []
                for memory in relevant_memories:
                    self.memories.append({
                        'id': memory.get('id'),
                        'content': memory.get('content'),
                        'importance': memory.get('importance', 1.0),
                        'created_at': memory.get('created_at'),
                        'source': memory.get('source', 'unknown')
                    })
                logger.info(f"Found {len(relevant_memories)} relevant memories using cached retriever for query: {query}")
            else:
                # Fall back to keyword search if vector search returns no results
                relevant_memories = search_user_memories(str(self.user.id), query, limit=limit)
                if relevant_memories:
                    self.memories = relevant_memories
                    logger.info(f"Found {len(relevant_memories)} relevant memories using text search for query: {query}")
                else:
                    logger.info(f"No relevant memories found for query: {query}")
                    self.memories = []
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            # Keep current memories if search fails
            if not hasattr(self, 'memories'):
                self.memories = []
    
    def chat(self, message: str) -> str:
        """
        Send a message to the learner and get a response.
        
        Args:
            message: Message to send
            
        Returns:
            str: Response from the learner
        """
        # Search for relevant memories based on the message
        self._search_memories(message)
        
        # Format memories for context
        memory_context = self._format_memories_for_context()
        
        # Build user profile information
        profile_info = []
        
        # Basic identity
        name_parts = []
        if self.user.first_name:
            name_parts.append(self.user.first_name)
        if self.user.last_name:
            name_parts.append(self.user.last_name)
        full_name = " ".join(name_parts) if name_parts else self.user.username or "Unknown"
        
        # Add profession and description
        if self.user.profession:
            profile_info.append(f"You work as a {self.user.profession}.")
        
        if self.user.description:
            profile_info.append(f"About yourself: {self.user.description}")
        
        # Add demographic info
        if self.user.gender:
            profile_info.append(f"You identify as {self.user.gender}.")
        
        # Add background
        if self.user.background:
            profile_info.append(f"Your background: {self.user.background}")
        
        # Add personality traits
        if self.user.personality_traits:
            traits = ", ".join(self.user.personality_traits)
            profile_info.append(f"Your personality traits include: {traits}.")
        
        # Add interests
        if self.user.interests:
            interests = ", ".join(self.user.interests)
            profile_info.append(f"Your interests include: {interests}.")
        
        # Add skills
        if self.user.skills:
            skills = ", ".join(self.user.skills)
            profile_info.append(f"Your skills include: {skills}.")
        
        # Build profile section
        profile_section = ""
        if profile_info:
            profile_section = f"\nYour profile:\n" + "\n".join(profile_info) + "\n"
        
        # Create system prompt with enhanced profile information
        system_prompt = f"""You are {full_name}.
You should respond based on your profile, memories and learned knowledge.
{profile_section}
{memory_context}

"""
        
        # Create messages for LLM
        messages = [SystemMessage(content=system_prompt)]
        
        # Add chat history
        for msg in self.chat_history[-5:]:  # Include last 5 messages for context
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=message))
        
        # Save to history
        self.chat_history.append({"role": "user", "content": message})
        
        # Generate response
        try:
            response = self.llm.invoke(messages)
            
            # Extract content
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Save to history
            self.chat_history.append({"role": "assistant", "content": response_text})
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"
    
    def add_memory(self, content: str, importance: float = 1.0) -> Optional[str]:
        """
        Add a new memory for the learner.
        
        Args:
            content: Memory content
            importance: Importance of the memory
            
        Returns:
            Optional[str]: ID of the created memory if successful, None otherwise
        """
        try:
            memory_id = add_user_memory(
                str(self.user.id),
                content,
                meta_data={"source": "chat", "added_by": "user"},
                importance=importance,
                source="manual_chat"
            )
            
            if memory_id:
                # Refresh memories
                self.memories = self._load_initial_memories()
                logger.info(f"Added new memory with ID {memory_id}")
                return memory_id
            else:
                logger.error("Failed to add memory")
                return None
                
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            return None
    
    def close(self) -> None:
        """
        Close the chat session.
        """
        if self.db:
            self.db.close()
            logger.info(f"Closed chat session with learner {self.user.username}")


def create_chat_session(username: str = None, user_id: str = None, temperature: float = 0.7, max_tokens: Optional[int] = None) -> Optional[LearnerChatSession]:
    """
    Create a chat session with a learner.
    
    Args:
        username: Username of the learner to chat with
        user_id: User ID of the learner to chat with (alternative to username)
        temperature: Sampling temperature for the LLM (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Optional[LearnerChatSession]: Chat session if created successfully, None otherwise
    """
    try:
        return LearnerChatSession(username=username, user_id=user_id, temperature=temperature, max_tokens=max_tokens)
    except Exception as e:
        logger.error(f"Failed to create chat session: {str(e)}")
        return None