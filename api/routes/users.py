from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from agir_db.db.session import get_db
from agir_db.models.user import User
from api.middleware.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users"""
    users = db.query(User).all()
    
    # Format response to include full name
    result = []
    for user in users:
        full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else ""
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": full_name,
            "created_at": user.created_at
        }
        result.append(user_data)
    
    return result

@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        "created_at": user.created_at,
        "updated_at": user.last_login_at  # Using last_login_at as updated_at
    }
    
    # Add any additional profile data if available
    for attr in ["avatar", "description", "interests", "skills"]:
        if hasattr(user, attr) and getattr(user, attr):
            result[attr] = getattr(user, attr)
    
    return result

@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: uuid.UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }
    
    # Add additional profile attributes if they exist
    for attr in ["avatar", "description", "birth_date", "gender", "profession", 
                "personality_traits", "background", "interests", "skills"]:
        if hasattr(user, attr) and getattr(user, attr):
            profile[attr] = getattr(user, attr)
    
    return profile 