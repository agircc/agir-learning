"""
Utilities for querying chat messages
"""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_message import ChatMessage
from agir_db.models.step import Step


def get_conversations_for_step(db: Session, step_id: uuid.UUID) -> List[ChatConversation]:
    """
    Get conversations related to a step.
    
    Args:
        db: Database session (will be closed by caller)
        step_id: ID of the step
        
    Returns:
        List of chat conversations
    """
    # Query conversations directly using the related_id and related_type fields
    conversations = db.query(ChatConversation).filter(
        ChatConversation.related_id == step_id,
        ChatConversation.related_type == 'step'
    ).all()
    
    return conversations


def get_messages_for_conversation(db: Session, conversation_id: uuid.UUID) -> List[ChatMessage]:
    """
    Get messages for a conversation.
    
    Args:
        db: Database session (will be closed by caller)
        conversation_id: ID of the chat conversation
        
    Returns:
        List of chat messages
    """
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.created_at).all()
    
    return messages


def format_messages(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    """
    Format chat messages into a list of structured message dictionaries.
    
    Args:
        messages: List of chat messages
        
    Returns:
        List of dictionaries containing message information
    """
    formatted_messages = []
    
    for message in messages:
        # Use first_name and last_name instead of username for a more realistic display
        if message.sender and message.sender.first_name and message.sender.last_name:
            sender_name = f"{message.sender.first_name} {message.sender.last_name}"
        elif message.sender:
            sender_name = message.sender.username
        else:
            sender_name = "Unknown"
            
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S") if message.created_at else "Unknown time"
        
        # Extract sender role if available
        sender_role = getattr(message.sender, 'role', None)
        if not sender_role and hasattr(message.sender, 'agent_role'):
            sender_role = message.sender.agent_role
            
        formatted_message = {
            "sender_name": sender_name,
            "sender_id": str(message.sender_id) if message.sender_id else None,
            "sender_role": sender_role,
            "content": message.content,
            "timestamp": timestamp,
            "raw_timestamp": message.created_at
        }
        
        formatted_messages.append(formatted_message)
    
    return formatted_messages


def format_messages_legacy(messages: List[ChatMessage]) -> str:
    """
    Format chat messages into a readable string (legacy format).
    
    Args:
        messages: List of chat messages
        
    Returns:
        Formatted string of messages
    """
    formatted = ""
    
    for message in messages:
        # Use first_name and last_name instead of username for a more realistic display
        if message.sender and message.sender.first_name and message.sender.last_name:
            sender_name = f"{message.sender.first_name} {message.sender.last_name}"
        elif message.sender:
            sender_name = message.sender.username
        else:
            sender_name = "Unknown"
            
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S") if message.created_at else "Unknown time"
        
        formatted += f"[{timestamp}] {sender_name}:\n"
        formatted += f"{message.content}\n\n"
    
    return formatted 