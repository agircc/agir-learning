from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from agir_db.db.session import get_db
from agir_db.models.user import User

router = APIRouter()

@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).all()
    
    # Format response to include full name
    result = []
    for user in users:
        full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else ""
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": full_name,
            "role": user.role if hasattr(user, "role") else None,
            "created_at": user.created_at
        })
    
    return result

@router.get("/{user_id}")
async def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Format response with additional information
    full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else ""
    result = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": full_name,
        "role": user.role if hasattr(user, "role") else None,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    # Add any additional profile data if available
    if hasattr(user, "profile") and user.profile:
        result["profile"] = user.profile
    
    return result

@router.get("/{user_id}/profile")
async def get_user_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get detailed user profile information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Compile comprehensive profile information
    profile = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else "",
        "role": user.role if hasattr(user, "role") else None,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    # Add additional profile attributes if they exist
    for attr in ["bio", "avatar", "preferences", "metadata"]:
        if hasattr(user, attr):
            profile[attr] = getattr(user, attr)
    
    return profile 