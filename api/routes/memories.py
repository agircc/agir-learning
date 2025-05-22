from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
import uuid
from math import ceil

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.memory import UserMemory

router = APIRouter()

@router.get("/{user_id}")
async def get_user_memories(
    user_id: uuid.UUID, 
    page: int = Query(1, ge=1), 
    page_size: int = Query(10, ge=1, le=100),
    memory_type: Optional[str] = None,
    min_importance: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get memories for a user with pagination and filtering"""
    # First check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Build query for memories
    query = db.query(UserMemory).filter(UserMemory.user_id == user_id)
    
    # Apply filters if provided
    if memory_type:
        query = query.filter(UserMemory.memory_type == memory_type)
    if min_importance is not None:
        query = query.filter(UserMemory.importance >= min_importance)
    
    # Get total count for pagination
    total = query.count()
    
    # Add pagination
    query = query.order_by(desc(UserMemory.importance), desc(UserMemory.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    memories = query.all()
    
    # Format response
    result = {
        "items": memories,
        "total": total,
        "page": page,
        "size": page_size,
        "pages": ceil(total / page_size) if total > 0 else 1
    }
    
    return result

@router.get("/memory/{memory_id}")
async def get_memory(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a memory by ID"""
    memory = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory

@router.get("/types")
async def get_memory_types(db: Session = Depends(get_db)):
    """Get all unique memory types"""
    # Query distinct memory types
    memory_types = db.query(UserMemory.memory_type).distinct().filter(UserMemory.memory_type != None).all()
    return [t[0] for t in memory_types if t[0]] 