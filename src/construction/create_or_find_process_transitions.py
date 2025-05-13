import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.scenario import StateTransition
from src.construction.data_store import set_process_transitions

logger = logging.getLogger(__name__)

def create_or_find_process_transitions(
    db: Session, 
    process_id: int, 
    transitions: List[Dict[str, str]],
    node_id_mapping: Dict[str, int]
) -> bool:
    """
    Create or find process transitions based on YAML process transitions.
    
    Args:
        db: Database session
        process_id: ID of the process
        transitions: List of transition data from YAML
        node_id_mapping: Mapping of YAML node names to database node IDs
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        success = True
        
        for transition in transitions:
            from_node_name = transition.get("from")
            to_node_name = transition.get("to")
            
            if not from_node_name or not to_node_name:
                logger.error("Transition from/to node names are required")
                success = False
                continue
            
            from_node_id = node_id_mapping.get(from_node_name)
            to_node_id = node_id_mapping.get(to_node_name)
            
            if not from_node_id:
                logger.error(f"From node not found: {from_node_name}")
                success = False
                continue
                
            if not to_node_id:
                logger.error(f"To node not found: {to_node_name}")
                success = False
                continue
            
            # Check if transition exists
            existing = db.query(StateTransition).filter(
                StateTransition.scenario_id == process_id,
                StateTransition.from_state_id == from_node_id,
                StateTransition.to_state_id == to_node_id
            ).first()
            
            if existing:
                logger.info(f"Transition already exists: {from_node_name} -> {to_node_name}")
                continue
            
            # Create transition
            transition_obj = StateTransition(
                scenario_id=process_id,
                from_state_id=from_node_id,
                to_state_id=to_node_id,
                condition=transition.get("condition", "")
            )
            
            db.add(transition_obj)
            logger.info(f"Created transition: {from_node_name} -> {to_node_name}")
        
        db.commit()
        return success
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find process transitions: {str(e)}")
        return False