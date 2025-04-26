import logging
import json

from sqlalchemy.orm import Session
from src.db.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.process_role import ProcessRole
from agir_db.models.process_role_user import ProcessRoleUser
from src.db.data_store import get_learner, get_process, set_learner

logger = logging.getLogger(__name__)

def create_process_role_user(db: Session, role: str, process_id: Any, username: Optional[str] = None, model: Optional[str] = None) -> User:
    """
    Create a user for a specific role and process and associate them in process_role_users.
    
    Args:
        db: Database session
        role: Role name
        process_id: ID of the process
        username: Optional username for the user
        
    Returns:
        User instance
    """
    learner = get_learner()
    process = get_process()

    logger.info(f"Process learner role: {process.learner_role}")
    logger.info(f"Role: {role}")
    if process.learner_role == role:
        return learner
    # Generate username if not provided
    if not username:
        username = f"{role}_{process_id}"
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == username).first()
    
    if existing_user:
        logger.info(f"Found existing user with username {username}")
        return existing_user
    

    # Create new user
    logger.info(f"Creating new user for role {role}: {username}")
    
    # Create basic user
    new_user = User(
        username=username,
        first_name=f"Agent {role.capitalize()}",
        last_name=str(process_id)[:8],
        email=f"{username}@agir.ai",
        llm_model=model,
        is_active=True
    )
    
    db.add(new_user)
    db.flush()
    
    # Find the process role
    process_role = db.query(ProcessRole).filter(
        ProcessRole.process_id == process_id,
        ProcessRole.name == role
    ).first()
    
    if not process_role:
        logger.warning(f"Role '{role}' not found for process {process_id}. Creating a default role.")
        # Create a default role if it doesn't exist
        process_role = ProcessRole(
            process_id=process_id,
            name=role,
            description=f"Automatically created role for {role}"
        )
        db.add(process_role)
        db.flush()
    
    # Associate user with role
    role_user = ProcessRoleUser(
        role_id=process_role.id,
        user_id=new_user.id
    )
    db.add(role_user)
    
    db.commit()
    db.refresh(new_user)
    
    return new_user
