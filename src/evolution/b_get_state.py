import logging
import sys
from typing import Optional
from sqlalchemy.orm import Session
from agir_db.models.state import State
from agir_db.models.state_transition import StateTransition
from agir_db.schemas.state import StateInDBBase
from agir_db.models.episode import EpisodeStatus

from src.evolution.store import get_episode

logger = logging.getLogger(__name__)

def b_get_state(db: Session, scenario_id: int) -> Optional[State]:
    """
    Get the initial state of a scenario.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        
    Returns:
        Optional[State]: Initial state if found, None otherwise
    """
    try:
        episode = get_episode()
        if not episode:
            logger.error(f"No episode found")
            sys.exit(1)
        
        if episode.current_state_id and episode.status == EpisodeStatus.RUNNING:
          current_state = db.query(State).filter(State.id == episode.current_state_id).first()
          logger.info(f"Continuing with existing state: {current_state.name if current_state else None}")

          return current_state
        
        # Get all states in the scenario
        all_states = db.query(State).filter(State.scenario_id == scenario_id).all()
        if not all_states:
            logger.error(f"No states found for scenario: {scenario_id}")
            sys.exit(1)
        
        # Get all 'to' states in transitions
        to_states = db.query(StateTransition.to_state_id).filter(
            StateTransition.scenario_id == scenario_id
        ).all()
        to_state_ids = {t[0] for t in to_states}
        
        # Find states that are not 'to' states in any transition
        # These are potential starting states
        for state in all_states:
            if state.id not in to_state_ids:
                return StateInDBBase.model_validate(state)
        
        # If no clear starting state, return the first state
        logger.warning(f"No clear starting state found for scenario: {scenario_id}, using first state")
        return all_states[0]
        
    except Exception as e:
        logger.error(f"Failed to get state: {str(e)}")
        sys.exit(1)