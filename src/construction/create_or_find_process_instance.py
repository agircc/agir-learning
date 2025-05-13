import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.episode import Episode, EpisodeStatus

logger = logging.getLogger(__name__)

def create_or_find_process_instance(db: Session, process_id: int, initiator_id: int) -> Optional[int]:
    """
    Create a process instance.
    
    Args:
        db: Database session
        process_id: ID of the process
        initiator_id: ID of the initiator
        
    Returns:
        Optional[int]: ID of the process instance if successful, None otherwise
    """
    try:
        instance = Episode(
            scenario_id=process_id,
            initiator_id=initiator_id,
            status=EpisodeStatus.RUNNING
        )
        
        db.add(instance)
        db.commit()
        db.refresh(instance)
        
        logger.info(f"Created process instance with ID: {instance.id}")
        
        return instance.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process instance: {str(e)}")
        return None