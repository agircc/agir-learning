import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.scenario import StateTransition
from src.construction.data_store import set_state_transitions

logger = logging.getLogger(__name__)

def create_or_find_state_transitions(
    db: Session, 
    scenario_id: int, 
    transitions: List[Dict[str, str]],
    state_id_mapping: Dict[str, int]
) -> bool:
    """
    Create or find state transitions based on YAML transitions data.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        transitions: List of transition data from YAML
        state_id_mapping: Mapping of YAML state names to database state IDs
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        success = True
        
        for transition in transitions:
            from_state_name = transition.get("from")
            to_state_name = transition.get("to")
            
            if not from_state_name or not to_state_name:
                logger.error("Transition from/to state names are required")
                success = False
                continue
            
            from_state_id = state_id_mapping.get(from_state_name)
            to_state_id = state_id_mapping.get(to_state_name)
            
            if not from_state_id:
                logger.error(f"From state not found: {from_state_name}")
                success = False
                continue
                
            if not to_state_id:
                logger.error(f"To state not found: {to_state_name}")
                success = False
                continue
            
            # Check if transition exists
            existing = db.query(StateTransition).filter(
                StateTransition.scenario_id == scenario_id,
                StateTransition.from_state_id == from_state_id,
                StateTransition.to_state_id == to_state_id
            ).first()
            
            if existing:
                logger.info(f"Transition already exists: {from_state_name} -> {to_state_name}")
                continue
            
            # Create transition
            transition_obj = StateTransition(
                scenario_id=scenario_id,
                from_state_id=from_state_id,
                to_state_id=to_state_id,
                condition=transition.get("condition", "")
            )
            
            db.add(transition_obj)
            logger.info(f"Created transition: {from_state_name} -> {to_state_name}")
        
        db.commit()
        
        # Store transitions in data store
        transitions_map = {
            f"{from_name}_{to_name}": {
                "from_state_id": state_id_mapping[from_name],
                "to_state_id": state_id_mapping[to_name]
            }
            for transition in transitions
            for from_name, to_name in [(transition.get("from"), transition.get("to"))]
            if from_name in state_id_mapping and to_name in state_id_mapping
        }
        set_state_transitions(transitions_map)
        
        return success
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find state transitions: {str(e)}")
        return False