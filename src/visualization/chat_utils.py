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
        db: Database session
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
        db: Database session
        conversation_id: ID of the chat conversation
        
    Returns:
        List of chat messages
    """
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.created_at).all()
    
    return messages


def format_messages(messages: List[ChatMessage]) -> str:
    """
    Format chat messages into a readable string.
    
    Args:
        messages: List of chat messages
        
    Returns:
        Formatted string of messages
    """
    formatted = ""
    
    for message in messages:
        sender = message.sender.name if message.sender else "Unknown"
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S") if message.created_at else "Unknown time"
        
        formatted += f"[{timestamp}] {sender}:\n"
        formatted += f"{message.content}\n\n"
    
    return formatted 