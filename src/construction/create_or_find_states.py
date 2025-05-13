import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.scenario import State, StateRole
from src.construction.data_store import set_states

logger = logging.getLogger(__name__)

def create_or_find_states(db: Session, scenario_id: int, states_data: List[Dict[str, Any]]) -> Optional[Dict[str, int]]:
    """
    Create or find states based on YAML states data.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        states_data: List of state data from YAML
        
    Returns:
        Optional[Dict[str, int]]: Mapping of YAML state names to database state IDs if successful, None otherwise
    """
    try:
        # Keep track of state IDs for lookup
        state_ids = {}
        
        # Create states
        for state_data in states_data:
            name = state_data.get("name")
            if not name:
                logger.error("State name is required")
                return None
            
            # Check if state exists
            state = db.query(State).filter(
                State.scenario_id == scenario_id,
                State.name == name
            ).first()
            
            if state:
                logger.info(f"State already exists: {name}")
                state_ids[name] = state.id
                continue
            
            # Create state
            state = State(
                scenario_id=scenario_id,
                name=name,
                description=state_data.get("description", ""),
                role=state_data.get("role", ""),
                is_required=state_data.get("is_required", True),
                external_id=str(uuid4())
            )
            
            db.add(state)
            db.flush()  # Get ID without committing
            
            logger.info(f"Created state: {name} with ID: {state.id}")
            state_ids[name] = state.id
            
            # Handle state roles if present
            roles_data = state_data.get("roles", [])
            if roles_data:
                for role_data in roles_data:
                    role_name = role_data.get("name")
                    if not role_name:
                        continue
                    
                    # Check if state role exists
                    state_role = db.query(StateRole).filter(
                        StateRole.state_id == state.id,
                        StateRole.name == role_name
                    ).first()
                    
                    if state_role:
                        logger.info(f"State role already exists: {role_name} for state: {name}")
                        continue
                    
                    # Create state role
                    state_role = StateRole(
                        state_id=state.id,
                        name=role_name,
                        description=role_data.get("description", "")
                    )
                    
                    db.add(state_role)
                    logger.info(f"Created state role: {role_name} for state: {name}")
        
        db.commit()
        logger.info(f"All states created successfully for scenario: {scenario_id}")
        
        # Store states data in data_store
        set_states(state_ids)
        
        return state_ids
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find states: {str(e)}")
        return None