from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
import uuid
from math import ceil

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_assignment import AgentAssignment
from agir_db.models.agent_role import AgentRole
from agir_db.models.episode import Episode
from agir_db.models.scenario import Scenario
from api.middleware.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all users with pagination and optional search"""
    # Build query
    query = db.query(User)
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            User.username.ilike(search_term) |
            User.email.ilike(search_term) |
            User.first_name.ilike(search_term) |
            User.last_name.ilike(search_term)
        )
    
    # Get total count for pagination
    total = query.count()
    
    # Add pagination
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    users = query.all()
    
    # Format response to include full name
    result_items = []
    for user in users:
        full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else ""
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": full_name,
            "created_at": user.created_at,
            "avatar": getattr(user, "avatar", None),
            "profession": getattr(user, "profession", None),
            "description": getattr(user, "description", None)
        }
        result_items.append(user_data)
    
    # Return paginated response
    return {
        "items": result_items,
        "total": total,
        "page": page,
        "size": page_size,
        "pages": ceil(total / page_size) if total > 0 else 1
    }

@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID, 
    db: Session = Depends(get_db)
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

@router.get("/{user_id}/episodes")
async def get_user_episodes(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get episodes that this user has participated in via agent assignments"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get agent assignments for this user with pagination
    assignments_query = db.query(AgentAssignment).filter(
        AgentAssignment.user_id == user_id
    )
    
    # Get total count for pagination
    total = assignments_query.count()
    
    # Apply pagination
    assignments = assignments_query.order_by(desc(AgentAssignment.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    if not assignments:
        return {
            "items": [],
            "total": total,
            "page": page,
            "size": page_size,
            "pages": ceil(total / page_size) if total > 0 else 1
        }
    
    # Get episodes and related info
    result = []
    for assignment in assignments:
        # Get episode
        episode = db.query(Episode).filter(Episode.id == assignment.episode_id).first()
        if not episode:
            continue
            
        # Get role
        role = db.query(AgentRole).filter(AgentRole.id == assignment.role_id).first()
        
        # Get scenario
        scenario = db.query(Scenario).filter(Scenario.id == episode.scenario_id).first()
        
        episode_data = {
            "id": episode.id,
            "scenario_id": episode.scenario_id,
            "status": episode.status.value if hasattr(episode.status, 'value') else str(episode.status),
            "created_at": episode.created_at,
            "updated_at": episode.updated_at,
            "scenario_name": scenario.name if scenario else None,
            "role_description": assignment.description if assignment.description else (role.description if role else None)
        }
        
        result.append(episode_data)
    
    # Sort by creation date, newest first
    result.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "size": page_size,
        "pages": ceil(total / page_size) if total > 0 else 1
    }

@router.get("/{user_id}/learning")
async def get_user_learning_episodes(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get episodes that this user initiated (learning episodes)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get episodes initiated by this user with pagination
    episodes_query = db.query(Episode).filter(
        Episode.initiator_id == user_id
    )
    
    # Get total count for pagination
    total = episodes_query.count()
    
    # Apply pagination
    episodes = episodes_query.order_by(desc(Episode.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    if not episodes:
        return {
            "items": [],
            "total": total,
            "page": page,
            "size": page_size,
            "pages": ceil(total / page_size) if total > 0 else 1
        }
    
    # Get related info for each episode
    result = []
    for episode in episodes:
        # Get scenario
        scenario = db.query(Scenario).filter(Scenario.id == episode.scenario_id).first()
        
        # Get user's role in this episode (if any)
        assignment = db.query(AgentAssignment).filter(
            AgentAssignment.episode_id == episode.id,
            AgentAssignment.user_id == user_id
        ).first()
        
        role_description = None
        if assignment:
            role = db.query(AgentRole).filter(AgentRole.id == assignment.role_id).first()
            role_description = assignment.description if assignment.description else (role.description if role else None)
        
        episode_data = {
            "id": episode.id,
            "scenario_id": episode.scenario_id,
            "status": episode.status.value if hasattr(episode.status, 'value') else str(episode.status),
            "created_at": episode.created_at,
            "updated_at": episode.updated_at,
            "scenario_name": scenario.name if scenario else None,
            "role_description": role_description
        }
        
        result.append(episode_data)
    
    # Sort by creation date, newest first
    result.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "size": page_size,
        "pages": ceil(total / page_size) if total > 0 else 1
    } 