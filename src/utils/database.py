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
    
    # Handle LLM model if present
    llm_model = user_data.pop("model", None)
    
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
    
    # Set LLM model if present and the field exists
    if llm_model and hasattr(new_user, 'llm_model'):
        new_user.llm_model = llm_model
    
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


def find_or_create_learner(db: Session, learner_data: Dict[str, Any]) -> User:
    """
    Find an existing learner or create a new one based on the provided data.
    This is a specialized function for handling the main learner user.
    
    Args:
        db: Database session
        learner_data: Learner data from the YAML file
        
    Returns:
        User instance representing the learner
    """
    username = learner_data.get("username")
    if not username:
        raise ValueError("Learner must have a username specified")
    
    # Try to find existing learner
    user, created = get_or_create_user(db, username, learner_data.copy())
    
    # Mark as learner role in custom fields if created
    if created:
        learner_role = CustomField(
            user_id=user.id,
            field_name="role",
            field_value="learner"
        )
        db.add(learner_role)
        db.commit()
        logger.info(f"Marked user {username} as a learner")
    
    return user


def create_or_update_agent(db: Session, role: str, process_id: Any, username: Optional[str] = None) -> User:
    """
    Create or update an agent user for a specific role and process.
    
    Args:
        db: Database session
        role: Role name
        process_id: ID of the process
        username: Optional username for the agent
        
    Returns:
        Agent user
    """
    # Generate username if not provided
    if not username:
        username = f"{role}_{process_id}"
    
    # Check if agent already exists
    existing_agent = db.query(User).filter(User.username == username).first()
    
    if existing_agent:
        logger.info(f"Found existing agent for role {role}: {username}")
        
        # Update role if needed
        existing_role = db.query(CustomField).filter(
            CustomField.user_id == existing_agent.id,
            CustomField.field_name == "role"
        ).first()
        
        if existing_role:
            if existing_role.field_value != role:
                existing_role.field_value = role
                db.commit()
                logger.info(f"Updated agent role to {role}")
        else:
            # Add role field
            role_field = CustomField(
                user_id=existing_agent.id,
                field_name="role",
                field_value=role
            )
            db.add(role_field)
            db.commit()
            logger.info(f"Added role {role} to existing agent")
        
        return existing_agent
    
    # Create new agent
    logger.info(f"Creating new agent for role {role}: {username}")
    
    # Create basic user
    new_agent = User(
        username=username,
        first_name=f"Agent {role.capitalize()}",
        last_name=str(process_id)[:8],
        email=f"{username}@agir.ai",
        is_active=True
    )
    
    db.add(new_agent)
    db.flush()
    
    # Add role custom field
    role_field = CustomField(
        user_id=new_agent.id,
        field_name="role",
        field_value=role
    )
    db.add(role_field)
    
    # Add process ID custom field
    process_field = CustomField(
        user_id=new_agent.id,
        field_name="process_id",
        field_value=str(process_id)
    )
    db.add(process_field)
    
    db.commit()
    db.refresh(new_agent)
    
    return new_agent


def find_agent_by_role(db: Session, role: str, process_id: Optional[Any] = None) -> Optional[User]:
    """
    Find an agent by role and optionally process ID.
    
    Args:
        db: Database session
        role: Role to look for (e.g., "learner", "patient", "nurse")
        process_id: Optional process ID to filter by
        
    Returns:
        Agent user or None if not found
    """
    # Start with basic query for the role
    query = db.query(User).join(
        CustomField, 
        User.id == CustomField.user_id
    ).filter(
        CustomField.field_name == "role",
        CustomField.field_value == role
    )
    
    # If process_id provided, add that filter
    if process_id is not None:
        query = query.join(
            CustomField, 
            User.id == CustomField.user_id,
            isouter=True
        ).filter(
            CustomField.field_name == "process_id",
            CustomField.field_value == str(process_id)
        )
    
    agent = query.first()
    
    if agent:
        logger.info(f"Found agent for role {role}" + (f" in process {process_id}" if process_id else ""))
        return agent
    
    logger.info(f"No agent found for role {role}" + (f" in process {process_id}" if process_id else ""))
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