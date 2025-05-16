import logging
from typing import Optional

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.episode import Episode, EpisodeStatus

from src.common.data_store import get_learner
from src.evolution.store import set_episode

logger = logging.getLogger(__name__)

def a_create_or_find_episode(scenario_id: int) -> Optional[Episode]:
    """
    Find an existing running episode for the scenario or create a new one if none exists.

    Returns:
        Optional[Episode]: Found or created episode if successful, None otherwise
    """
    db = None
    try:
        db = next(get_db())
        
        logger.info(f"Looking for existing running episode for scenario: {scenario_id}")
        
        # Check for existing running episodes
        existing_episode = db.query(Episode).filter(
            Episode.scenario_id == scenario_id, 
            Episode.status == EpisodeStatus.RUNNING
        ).first()
        
        if existing_episode:
            logger.info(f"Found existing running episode {existing_episode.id} for scenario {scenario_id}")
            set_episode(existing_episode)
            return existing_episode

        logger.info(f"Creating new episode for scenario: {scenario_id}")

        # Get scenario
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            logger.error(f"Scenario not found: {scenario_id}")
            return None
        
        learner = get_learner()            
        # Create episode
        episode = Episode(
            scenario_id=scenario_id,
            status=EpisodeStatus.RUNNING,
            initiator_id=learner.id
        )
        
        db.add(episode)
        db.commit()
        
        logger.info(f"Created episode {episode.id} for scenario {scenario_id}")
        set_episode(episode)
        return episode
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Failed to create or find episode: {str(e)}")
        return None
    finally:
        if db:
            db.close()