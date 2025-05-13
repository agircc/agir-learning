"""
Utilities for querying chat messages
"""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_message import ChatMessage
from agir_db.models.process_instance_step import ProcessInstanceStep


def get_conversations_for_step(db: Session, step_id: uuid.UUID) -> List[ChatConversation]:
    """
    Get conversations related to a process instance step.
    
    Args:
        db: Database session
        step_id: ID of the process instance step
        
    Returns:
        List of chat conversations
    """
    # This implementation is a placeholder and would need to be updated 
    # based on how conversations are linked to process instance steps in your schema
    
    # Assuming there's a link between conversations and steps
    # This could be via a join table or a direct foreign key
    step = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == step_id).first()
    if not step:
        return []
    
    # For now, we'll return all conversations that might be related to this step
    # This is just a placeholder and should be replaced with proper query
    conversations = db.query(ChatConversation).all()
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