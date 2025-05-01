import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.process import ProcessTransition
from src.construction.data_store import set_process_transitions

logger = logging.getLogger(__name__)

def create_or_find_process_transitions(
    db: Session, 
    process_id: int, 
    transitions: List[Any],
    node_id_mapping: Dict[str, int]
) -> bool:
    """
    Create process transitions from YAML process.
    
    Args:
        db: Database session
        process_id: ID of the process
        transitions: List of transitions
        node_id_mapping: Mapping of YAML node names to database node IDs
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # If no transitions, return early
        if not transitions:
            logger.info("No transitions defined in YAML")
            set_process_transitions({})
            return True
        
        # Log node mappings for debugging
        logger.debug(f"Node name to ID mapping: {node_id_mapping}")
        
        # Fetch existing transitions for this process
        existing_transitions = db.query(ProcessTransition).filter(
            ProcessTransition.process_id == process_id
        ).all()
        
        # Create set of existing transition tuples (from_node_id, to_node_id)
        existing_transition_set = {
            (t.from_node_id, t.to_node_id) for t in existing_transitions
        }
        
        # Store transition mapping for data_store
        transition_mapping = {}
        
        # Process each transition
        for transition in transitions:
            from_node_name = transition.from_node
            to_node_name = transition.to_node
            
            # Find nodes by name if not found in the mapping
            from_node_id = node_id_mapping.get(from_node_name)
            to_node_id = node_id_mapping.get(to_node_name)
            
            # Skip if either node is not found
            if not from_node_id:
                logger.warning(f"From node not found for transition: {from_node_name}")
                continue
                
            if not to_node_id:
                logger.warning(f"To node not found for transition: {to_node_name}")
                continue
            
            # Check if transition already exists
            if (from_node_id, to_node_id) in existing_transition_set:
                logger.info(f"Transition already exists: {from_node_name} -> {to_node_name}")
                transition_key = f"{from_node_name}_{to_node_name}"
                transition_mapping[transition_key] = {
                    'from_node_id': from_node_id,
                    'to_node_id': to_node_id
                }
                continue
            
            # Create transition
            db_transition = ProcessTransition(
                process_id=process_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                condition=transition.condition
            )
            
            db.add(db_transition)
            logger.debug(f"Created transition: {from_node_name} ({from_node_id}) -> {to_node_name} ({to_node_id})")
            
            # Store in transition mapping
            transition_key = f"{from_node_name}_{to_node_name}"
            transition_mapping[transition_key] = {
                'from_node_id': from_node_id,
                'to_node_id': to_node_id
            }
        
        db.commit()
        logger.info(f"Created or found process transitions")
        
        # Store transitions data in data_store
        set_process_transitions(transition_mapping)
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process transitions: {str(e)}")
        return False