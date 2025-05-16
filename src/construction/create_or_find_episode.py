import logging

from sqlalchemy.orm import Session
from src.utils.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.episode import Episode, EpisodeStatus

logger = logging.getLogger(__name__)

def create_or_find_episode(db: Session, scenario_id: int, initiator_id: int) -> Optional[int]:
    """
    Create a new episode.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        initiator_id: ID of the initiator
        
    Returns:
        Optional[int]: ID of the episode if successful, None otherwise
    """
    try:
        episode = Episode(
            scenario_id=scenario_id,
            initiator_id=initiator_id,
            status=EpisodeStatus.RUNNING
        )
        
        db.add(episode)
        db.commit()
        db.refresh(episode)
        
        logger.info(f"Created episode with ID: {episode.id}")
        
        return episode.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create episode: {str(e)}")
        return None