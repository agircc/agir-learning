import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.scenario import State, StateRole
from agir_db.models.agent_role import AgentRole
from src.construction.data_store import set_states, get_agent_roles

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
        
        # Get agent_roles mapping for creating state_roles
        agent_roles_mapping = get_agent_roles()
        if not agent_roles_mapping:
            logger.warning("No agent roles found in data store. State roles may not be created properly.")
        
        # Create states
        for state_data in states_data:
            name = state_data.name
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
            
            print("State data: ")
            print(state_data)
            
            # Create state without role (we'll handle roles separately)
            state = State(
                scenario_id=scenario_id,
                name=name,
                description=state_data.description,
            )
            
            db.add(state)
            db.flush()  # Get ID without committing
            
            logger.info(f"Created state: {name} with ID: {state.id}")
            state_ids[name] = state.id
            
            # Handle state roles
            # Check if we have a single role or multiple roles
            if hasattr(state_data, 'role') and state_data.role:
                # Single role case (doctor.yml format)
                role_name = state_data.role
                # Get the agent_role_id from our mapping
                if agent_roles_mapping and role_name in agent_roles_mapping:
                    agent_role_id = agent_roles_mapping[role_name]
                    # Create state_role entry
                    state_role = StateRole(
                        state_id=state.id,
                        agent_role_id=agent_role_id,
                        created_at=None  # Let it be set automatically
                    )
                    db.add(state_role)
                    logger.info(f"Created state_role for state: {name} and role: {role_name}")
                else:
                    logger.warning(f"Role {role_name} not found in agent_roles mapping. Looking up in database.")
                    # Try to find the role in the database
                    agent_role = db.query(AgentRole).filter(
                        AgentRole.scenario_id == scenario_id,
                        AgentRole.name == role_name
                    ).first()
                    
                    if agent_role:
                        state_role = StateRole(
                            state_id=state.id,
                            agent_role_id=agent_role.id,
                            created_at=None  # Let it be set automatically
                        )
                        db.add(state_role)
                        logger.info(f"Created state_role for state: {name} and role: {role_name}")
                    else:
                        logger.error(f"Role {role_name} not found in database for state: {name}")
            
            # Handle multiple roles (therapist.yml format)
            if hasattr(state_data, 'roles') and state_data.roles:
                roles = state_data.roles
                for role_name in roles:
                    # Get the agent_role_id from our mapping
                    if agent_roles_mapping and role_name in agent_roles_mapping:
                        agent_role_id = agent_roles_mapping[role_name]
                        # Create state_role entry
                        state_role = StateRole(
                            state_id=state.id,
                            agent_role_id=agent_role_id,
                            created_at=None  # Let it be set automatically
                        )
                        db.add(state_role)
                        logger.info(f"Created state_role for state: {name} and role: {role_name}")
                    else:
                        logger.warning(f"Role {role_name} not found in agent_roles mapping. Looking up in database.")
                        # Try to find the role in the database
                        agent_role = db.query(AgentRole).filter(
                            AgentRole.scenario_id == scenario_id,
                            AgentRole.name == role_name
                        ).first()
                        
                        if agent_role:
                            state_role = StateRole(
                                state_id=state.id,
                                agent_role_id=agent_role.id,
                                created_at=None  # Let it be set automatically
                            )
                            db.add(state_role)
                            logger.info(f"Created state_role for state: {name} and role: {role_name}")
                        else:
                            logger.error(f"Role {role_name} not found in database for state: {name}")
        
        db.commit()
        logger.info(f"All states created successfully for scenario: {scenario_id}")
        
        # Store states data in data_store
        set_states(state_ids)
        
        return state_ids
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find states: {str(e)}")
        return None