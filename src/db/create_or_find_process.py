import logging

from sqlalchemy.orm import Session
from src.db.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union 
from agir_db.db.session import get_db
from agir_db.models.process import Process
from agir_db.schemas.process import ProcessDTO
from agir_db.models.user import User
from src.db.data_store import set_process

logger = logging.getLogger(__name__)

def create_or_find_process(db: Session, process_name: str, description: str, learner_role: str, created_by: Optional[str] = None, default_user_id: Optional[int] = None) -> Optional[int]:
    """
    Create or find process based on YAML process.
    
    Args:
        db: Database session
        process_name: Name of the process
        description: Description of the process
        learner_role: Role of the learner
        created_by: Username of creator (optional)
        default_user_id: User ID to use as default creator if created_by is None
        
    Returns:
        Optional[int]: ID of the process if successful, None otherwise
    """
    try:
        # Check if process exists
        query = db.query(Process).filter(Process.name == process_name)
        if created_by:
            query = query.filter(Process.created_by == created_by)
            
        process = query.first()
        
        if process:
            logger.info(f"Found existing process: {process_name}")
            
            # Store process data in data_store
            process_info = ProcessDTO.model_validate(process)
            set_process(process_info)
            
            return process.id
        
        # If created_by is None, use default_user_id or find the first admin user
        creator_id = None
        if created_by:
            # Find user by username
            creator = db.query(User).filter(User.username == created_by).first()
            if creator:
                creator_id = str(creator.id)
            else:
                logger.warning(f"User with username {created_by} not found")
        
        # If still no creator_id, use default_user_id
        if not creator_id and default_user_id:
            creator_id = str(default_user_id)
            logger.info(f"Using target user as process creator since created_by was not provided")
        
        # If still no creator_id, find an admin user
        if not creator_id:
            admin_user = db.query(User).filter(User.is_active == True).first()
            if admin_user:
                creator_id = str(admin_user.id)
                logger.info(f"Using first active user as process creator: {admin_user.username}")
            else:
                logger.error("No active users found in database to use as process creator")
                return None
        
        # Create new process with the determined creator_id
        process = Process(
            name=process_name,
            description=description,
            created_by=creator_id,
            learner_role=learner_role
        )
        
        db.add(process)
        db.commit()
        logger.info(f"Created new process: {process_name} with ID: {process.id}, creator ID: {creator_id}")
        
        # Store process data in data_store
        process_info = ProcessDTO.model_validate(process)
        set_process(process_info)
        
        return process.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find process: {str(e)}")
        return None
