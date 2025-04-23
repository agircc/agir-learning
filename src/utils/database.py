"""
Database utility functions for AGIR Learning
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from agir_db.models.user import User
from agir_db.models.process import Process as DBProcess
from agir_db.models.custom_field import CustomField  # 导入agir_db包中的CustomField

logger = logging.getLogger(__name__)

# 不再需要导入这些类，因为我们直接使用agir_db的CustomField
# from sqlalchemy import Column, Integer, String, Text, ForeignKey
# from agir_db.db.base_class import Base

def get_or_create_user(db: Session, username: str, user_data: Dict[str, Any]) -> Tuple[User, bool]:
    """
    Get an existing user by username or create a new one.
    
    Args:
        db: Database session
        username: Username to look up
        user_data: User data for creation if needed
        
    Returns:
        Tuple of (user, created) where created is True if a new user was created
    """
    # Look for existing user
    existing_user = db.query(User).filter(User.username == username).first()
    
    if existing_user:
        logger.info(f"Found existing user: {username}")
        return existing_user, False
    
    # Create new user
    logger.info(f"Creating new user: {username}")
    
    # Extract standard User fields
    first_name = user_data.pop("first_name", None)
    last_name = user_data.pop("last_name", None)
    gender = user_data.pop("gender", None)
    birth_date = user_data.pop("birth_date", None)
    email = user_data.pop("email", f"{username}@agir.ai")  # Generate default email
    logger.info(f"gender: {gender}")
    # Create the user
    new_user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        birth_date=birth_date,
        email=email,
        is_active=True,
    )
    
    db.add(new_user)
    db.flush()  # Flush to get the ID without committing
    
    # Save remaining fields as custom fields
    if user_data:
        for key, value in user_data.items():
            if value is not None:
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                custom_field = CustomField(
                    user_id=new_user.id,
                    field_name=key,
                    field_value=str(value)
                )
                db.add(custom_field)
    
    db.commit()
    db.refresh(new_user)
    
    return new_user, True


def create_or_update_agent(db: Session, agent_data: Dict[str, Any], created_by_id: int) -> User:
    """
    Create or update an agent user.
    
    Args:
        db: Database session
        agent_data: Agent data
        created_by_id: ID of the user who created this agent
        
    Returns:
        Agent user
    """
    username = agent_data.get("username", f"{agent_data.get('role', 'agent')}_{agent_data.get('id', 'unknown')}")
    
    # Check if agent already exists
    existing_agent = db.query(User).filter(User.username == username).first()
    
    if existing_agent:
        logger.info(f"Updating existing agent: {username}")
        
        # Update basic fields if provided
        if "first_name" in agent_data:
            existing_agent.first_name = agent_data["first_name"]
        if "last_name" in agent_data:
            existing_agent.last_name = agent_data["last_name"]
        if "email" in agent_data:
            existing_agent.email = agent_data["email"]
            
        # Update custom fields
        for key, value in agent_data.items():
            if key in ["username", "first_name", "last_name", "email", "id"]:
                continue
                
            if value is not None:
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                    
                # Check if field exists
                existing_field = db.query(CustomField).filter(
                    CustomField.user_id == existing_agent.id,
                    CustomField.field_name == key
                ).first()
                
                if existing_field:
                    existing_field.field_value = str(value)
                else:
                    new_field = CustomField(
                        user_id=existing_agent.id,
                        field_name=key,
                        field_value=str(value)
                    )
                    db.add(new_field)
        
        db.commit()
        db.refresh(existing_agent)
        return existing_agent
    
    # Create new agent
    logger.info(f"Creating new agent: {username}")
    
    first_name = agent_data.get("first_name", f"Agent {agent_data.get('name', username)}")
    last_name = agent_data.get("last_name", agent_data.get("role", ""))
    email = agent_data.get("email", f"{username}@agir.ai")
    
    # Create agent user
    new_agent = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_active=True,
        created_by=created_by_id
    )
    
    db.add(new_agent)
    db.flush()
    
    # Add custom fields
    for key, value in agent_data.items():
        if key in ["username", "first_name", "last_name", "email", "id"]:
            continue
            
        if value is not None:
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
                
            custom_field = CustomField(
                user_id=new_agent.id,
                field_name=key,
                field_value=str(value)
            )
            db.add(custom_field)
    
    db.commit()
    db.refresh(new_agent)
    
    return new_agent


def find_agent_by_role(db: Session, role: str, created_by_id: Optional[int] = None) -> Optional[User]:
    """
    Find an agent by role.
    
    Args:
        db: Database session
        role: Role to look for
        created_by_id: Optional filter by creator
        
    Returns:
        Agent user or None if not found
    """
    query = db.query(CustomField, User) \
        .filter(CustomField.field_name == "role") \
        .filter(CustomField.field_value == role) \
        .filter(CustomField.user_id == User.id)
    
    if created_by_id is not None:
        query = query.filter(User.created_by_id == created_by_id)
    
    result = query.first()
    
    if result:
        return result[1]  # Return the User object
    
    return None


def create_process_record(db: Session, process_data: Dict[str, Any]) -> DBProcess:
    """
    Create a process record in the database
    
    Args:
        db: Database session
        process_data: Process data, should include 'name', 'description', and optionally 'created_by'
        
    Returns:
        DBProcess instance
    """
    logger.info(f"Creating process record: {process_data.get('name', 'Unnamed')}")
    
    # Make sure we have a created_by value (required by the database)
    created_by = process_data.get("created_by")
    if not created_by:
        # Find an active user to use as creator
        active_user = db.query(User).filter(User.is_active == True).first()
        if active_user:
            created_by = str(active_user.id)
            logger.info(f"Using active user ID {active_user.id} as process creator")
        else:
            logger.error("No active users found to use as process creator")
            raise ValueError("No active users found to use as process creator. Please create a user first.")
    
    # Create process record
    process_record = DBProcess(
        name=process_data.get("name", "Unnamed Process"),
        description=process_data.get("description", ""),
        created_by=created_by
    )
    
    db.add(process_record)
    db.commit()
    db.refresh(process_record)
    
    logger.info(f"Created process record with ID: {process_record.id}")
    return process_record 