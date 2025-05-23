from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
import time

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_message import ChatMessage
from api.middleware.auth import get_current_user
from src.chat.chat_with_learner import LearnerChatSession

router = APIRouter()

# Pydantic models for OpenAI-like API
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "agir-learner"
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    user_id: Optional[str] = None  # Optional user ID for personalized responses

class CompletionRequest(BaseModel):
    prompt: str
    model: Optional[str] = "agir-learner"
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    user_id: Optional[str] = None

@router.get("/conversations")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat conversations"""
    conversations = db.query(ChatConversation).all()
    
    result = []
    for conv in conversations:
        messages_count = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv.id).count()
        
        result.append({
            "id": conv.id,
            "name": conv.title if conv.title else f"Conversation {conv.id}",
            "created_at": conv.created_at,
            "related_type": conv.related_type,
            "related_id": conv.related_id,
            "messages_count": messages_count
        })
    
    return result

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        "name": conversation.title if conversation.title else f"Conversation {conversation.id}",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        # Create new conversation using the authenticated user
        conversation = ChatConversation(
            title=f"Chat with {user.username}",
            created_by=current_user.id,
            related_type="user",
            related_id=user_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Create the message from the authenticated user
    message = ChatMessage(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=content,
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Generate AI response using LearnerChatSession
    try:
        # Initialize chat session with the target user
        chat_session = LearnerChatSession(user_id=str(user_id))
        
        # Get response from the AI user
        ai_response = chat_session.chat(content)
        
        # Create message for AI response
        ai_message = ChatMessage(
            conversation_id=conversation.id,
            sender_id=user_id,
            content=ai_response,
            created_at=datetime.utcnow()
        )
        
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        
        # Include AI response in the result
        return {
            "id": message.id,
            "conversation_id": conversation.id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at,
            "ai_response": {
                "id": ai_message.id,
                "sender_id": str(user_id),
                "content": ai_response,
                "created_at": ai_message.created_at
            }
        }
    except Exception as e:
        # Log the error but continue without AI response
        print(f"Error generating AI response: {str(e)}")
        
        # Return the original message without AI response
        return {
            "id": message.id,
            "conversation_id": conversation.id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at
        }

@router.post("/completions")
async def create_completion(request: CompletionRequest):
    """Create a text completion (similar to OpenAI's completions API)"""
    try:
        # Use a default user ID if none provided, or create a session without user context
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Initialize chat session
        chat_session = LearnerChatSession(user_id=user_id)
        
        # Get AI response
        ai_response = chat_session.chat(request.prompt)
        
        # Generate a unique completion ID
        completion_id = f"cmpl-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format
        return {
            "id": completion_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "text": ai_response,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": len(request.prompt.split()) + len(ai_response.split())
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating completion: {str(e)}"
        )

@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (similar to OpenAI's chat completions API)"""
    try:
        # Use a default user ID if none provided
        user_id = request.user_id or "00000000-0000-0000-0000-000000000000"
        
        # Initialize chat session
        chat_session = LearnerChatSession(user_id=user_id)
        
        # Get the last user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in the conversation"
            )
        
        last_user_message = user_messages[-1].content
        
        # Get AI response
        ai_response = chat_session.chat(last_user_message)
        
        # Generate a unique completion ID
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:20]}"
        
        # Return OpenAI-like response format
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ai_response
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(ai_response.split())
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating chat completion: {str(e)}"
        ) 