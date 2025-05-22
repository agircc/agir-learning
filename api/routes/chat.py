from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_message import ChatMessage

router = APIRouter()

@router.get("/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    """Get all chat conversations"""
    conversations = db.query(ChatConversation).all()
    
    result = []
    for conv in conversations:
        messages_count = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv.id).count()
        
        result.append({
            "id": conv.id,
            "name": conv.name if conv.name else f"Conversation {conv.id}",
            "created_at": conv.created_at,
            "related_type": conv.related_type,
            "related_id": conv.related_id,
            "messages_count": messages_count
        })
    
    return result

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a conversation by ID with its messages"""
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    # Get messages for this conversation
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.created_at).all()
    
    formatted_messages = []
    for msg in messages:
        sender_name = "Unknown"
        if msg.sender:
            if msg.sender.first_name and msg.sender.last_name:
                sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"
            else:
                sender_name = msg.sender.username
        
        formatted_messages.append({
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "sender_name": sender_name,
            "created_at": msg.created_at
        })
    
    result = {
        "id": conversation.id,
        "name": conversation.name if conversation.name else f"Conversation {conversation.id}",
        "created_at": conversation.created_at,
        "related_type": conversation.related_type,
        "related_id": conversation.related_id,
        "messages": formatted_messages
    }
    
    return result

@router.post("/user/{user_id}/send")
async def send_message_to_user(
    user_id: uuid.UUID,
    content: str = Body(..., embed=True),
    conversation_id: Optional[uuid.UUID] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """Send a message to a user, creating a new conversation if needed"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get or create conversation
    conversation = None
    if conversation_id:
        conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = ChatConversation(
            name=f"Chat with {user.username}",
            related_type="user",
            related_id=user_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Create system message from admin to user
    # Note: In a real implementation, you'd use the authenticated user as sender
    admin_user = db.query(User).filter(User.role == "admin").first()
    if not admin_user:
        # Create a system user if no admin exists
        admin_user = User(
            username="system",
            first_name="System",
            last_name="Admin",
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    
    # Create the message
    message = ChatMessage(
        conversation_id=conversation.id,
        sender_id=admin_user.id,
        recipient_id=user_id,
        content=content,
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return {
        "id": message.id,
        "conversation_id": conversation.id,
        "sender_id": message.sender_id,
        "recipient_id": message.recipient_id,
        "content": message.content,
        "created_at": message.created_at
    } 