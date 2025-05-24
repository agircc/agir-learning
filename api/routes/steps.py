from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any
import uuid

from agir_db.db.session import get_db
from agir_db.models.step import Step
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_message import ChatMessage

router = APIRouter()

@router.get("/")
async def get_steps(db: Session = Depends(get_db)):
    """Get all steps"""
    steps = db.query(Step).all()
    return steps

@router.get("/{step_id}")
async def get_step(step_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a step by ID"""
    step = db.query(Step).options(
        joinedload(Step.state)
    ).filter(Step.id == step_id).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    return step

@router.get("/{step_id}/details")
async def get_step_details(step_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get detailed information for a step"""
    step = db.query(Step).options(
        joinedload(Step.state)
    ).filter(Step.id == step_id).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    
    # Get state data
    state_data = {}
    if step.state:
        state_data = {
            "id": step.state.id,
            "name": step.state.name,
            "description": step.state.description or ""
        }
    
    response = {
        "id": step.id,
        "action": step.action,
        "generated_text": step.generated_text,
        "created_at": step.created_at,
        "episode_id": step.episode_id,
        "state_id": step.state_id,
        "state": state_data
    }
    
    return response

@router.get("/{step_id}/conversations")
async def get_step_conversations(step_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get conversations related to a step"""
    step = db.query(Step).filter(Step.id == step_id).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    
    # Get conversations related to this step
    conversations = db.query(ChatConversation).options(
        joinedload(ChatConversation.messages).joinedload(ChatMessage.sender)
    ).filter(
        ChatConversation.related_id == step_id,
        ChatConversation.related_type == 'step'
    ).all()
    
    result = []
    for conv in conversations:
        # Format messages for this conversation
        formatted_messages = []
        for msg in conv.messages:
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
        
        result.append({
            "id": conv.id,
            "name": conv.name if conv.name else f"Conversation {conv.id}",
            "created_at": conv.created_at,
            "messages": formatted_messages
        })
    
    return result 