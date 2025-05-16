import logging
from typing import Optional
from sqlalchemy.orm import Session
from agir_db.models.state import State
from agir_db.models.state_transition import StateTransition
from agir_db.schemas.state import StateInDBBase

logger = logging.getLogger(__name__)

def b_get_initial_state(db: Session, scenario_id: int) -> Optional[State]:
    """
    Get the initial state of a scenario.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        
    Returns:
        Optional[State]: Initial state if found, None otherwise
    """
    try:
        # Get all states in the scenario
        all_states = db.query(State).filter(State.scenario_id == scenario_id).all()
        if not all_states:
            logger.error(f"No states found for scenario: {scenario_id}")
            return None
        
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
        logger.error(f"Failed to get initial state: {str(e)}")
        return None