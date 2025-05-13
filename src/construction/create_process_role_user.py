import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.agent_assignment import AgentAssignment
from src.construction.data_store import get_learner, get_process, set_learner

logger = logging.getLogger(__name__)

def create_process_role_user(db: Session, role: str, process_id: Any, username: Optional[str] = None, model: Optional[str] = None) -> User:
    """
    Create a user for a specific role and process and associate them in agent_assignments.
    
    Args:
        db: Database session
        role: Role name
        process_id: ID of the process
        username: Username (optional, will be generated if None)
        model: LLM model to use (optional)
        
    Returns:
        User: Created or found user
    """
    try:
        process = get_process()
        
        # Check if this is the learner role
        logger.info(f"Process learner role: {process.learner_role}")
        
        if process.learner_role == role:
            # Use existing learner
            learner = get_learner()
            if learner:
                logger.info(f"Using existing learner: {learner.username}")
                user = db.query(User).filter(User.id == learner.id).first()
                if user:
                    return user
        
        # Generate username if not provided
        if not username:
            username = f"{role}_{process_id}"
        
        # Find or create user
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            # Create new user
            user = User(
                username=username,
                first_name=role,
                last_name=str(process_id)[:8],
                email=f"{username}@agir.ai",
                is_active=True
            )
            
            # Set model if provided
            if model and hasattr(user, 'llm_model'):
                user.llm_model = model
                
            db.add(user)
            db.flush()  # Get ID without committing
            
            logger.info(f"Created new user: {username} with ID: {user.id}")
        
        # Find the process role
        process_role = db.query(AgentRole).filter(
            AgentRole.scenario_id == process_id,
            AgentRole.name == role
        ).first()
        
        if not process_role:
            logger.warning(f"Role '{role}' not found for process {process_id}. Creating a default role.")
            
            process_role = AgentRole(
                scenario_id=process_id,
                name=role,
                description=f"Auto-created role for {role}"
            )
            
            db.add(process_role)
            db.flush()
        
        # Create role-user association if it doesn't exist
        role_user = AgentAssignment(
            role_id=process_role.id,
            user_id=user.id
        )
        
        db.add(role_user)
        db.commit()
        
        if process.learner_role == role:
            # Store as learner
            set_learner(user)
        
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process role user: {str(e)}")
        raise
