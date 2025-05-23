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
from src.common.utils.memory_utils import get_user_memories, search_user_memories, add_user_memory, search_user_memories_vector
from src.llm.llm_provider import get_llm_model

from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class LearnerChatSession:
    """
    Class to manage a chat session with a learner.
    """
    
    def __init__(self, username: str = None, user_id: str = None):
        """
        Initialize a chat session with a learner.
        
        Args:
            username: Username of the learner to chat with
            user_id: User ID of the learner to chat with (alternative to username)
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
        self.llm = get_llm_model(self.model_name)
        self.chat_history = []
        self.memories = self._load_initial_memories()
        
        logger.info(f"Initialized chat session with learner {self.user.username} using model {self.model_name}")
    
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
    
    def _load_initial_memories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Load initial memories for the learner.
        
        Args:
            limit: Maximum number of memories to load
            
        Returns:
            List[Dict[str, Any]]: List of memories
        """
        return get_user_memories(str(self.user.id), limit=limit)
    
    def _format_memories_for_context(self) -> str:
        """
        Format memories for inclusion in the LLM context.
        
        Returns:
            str: Formatted memories
        """
        if not self.memories:
            return "You have no specific memories to draw from."
        
        formatted = "Your relevant memories and learned knowledge:\n\n"
        for i, memory in enumerate(self.memories):
            formatted += f"{i+1}. {memory['content']}\n\n"
        
        return formatted
    
    def _search_memories(self, query: str, limit: int = 3) -> None:
        """
        Search memories related to a query and update the current memories.
        Uses vector similarity search for better semantic matching.
        
        Args:
            query: Search query
            limit: Maximum number of memories to retrieve
        """
        try:
            # Use vector search directly
            relevant_memories = search_user_memories_vector(str(self.user.id), query, limit=limit)
            
            if relevant_memories:
                self.memories = relevant_memories
                logger.info(f"Found {len(relevant_memories)} relevant memories using vector search for query: {query}")
            else:
                # Fall back to keyword search if vector search returns no results
                relevant_memories = search_user_memories(str(self.user.id), query, limit=limit)
                if relevant_memories:
                    self.memories = relevant_memories
                    logger.info(f"Found {len(relevant_memories)} relevant memories using text search for query: {query}")
                else:
                    logger.info(f"No relevant memories found for query: {query}")
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            # Keep current memories if search fails
    
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
        
        # Create system prompt with memories
        system_prompt = f"""You are {self.user.first_name} {self.user.last_name}.
You should respond based on your memories and learned knowledge.

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


def create_chat_session(username: str = None, user_id: str = None) -> Optional[LearnerChatSession]:
    """
    Create a chat session with a learner.
    
    Args:
        username: Username of the learner to chat with
        user_id: User ID of the learner to chat with (alternative to username)
        
    Returns:
        Optional[LearnerChatSession]: Chat session if created successfully, None otherwise
    """
    try:
        return LearnerChatSession(username=username, user_id=user_id)
    except Exception as e:
        logger.error(f"Failed to create chat session: {str(e)}")
        return None