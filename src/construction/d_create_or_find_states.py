import logging
import sys
from uuid import uuid4
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.state import State
from agir_db.models.agent_role import AgentRole
from agir_db.models.state_role import StateRole
from src.common.data_store import set_states, get_agent_roles
import json

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
                sys.exit(1)
            
            # Check if state exists
            state = db.query(State).filter(
                State.scenario_id == scenario_id,
                State.name == name
            ).first()
            
            if state:
                logger.info(f"State already exists: {name}")
                state_ids[name] = state.id
                continue
            
            # Debug print
            print("State data: ")
            print(state_data)
            
            # Handle prompts if they exist
            prompts = None
            if hasattr(state_data, 'prompts') and state_data.prompts:
                # Store the prompts list directly - SQLAlchemy will handle the PostgreSQL ARRAY type
                if isinstance(state_data.prompts, list):
                    prompts = state_data.prompts
                else:
                    # If not a list but has value, wrap as a single-element list
                    prompts = [state_data.prompts]
                
                # Debug output for prompts
                logger.info(f"Added prompts for state: {name}")
                logger.info(f"Prompts type: {type(prompts)}")
                logger.info(f"Prompts count: {len(prompts)}")
                logger.info(f"First prompt (first 100 chars): {prompts[0][:100]}...")
            
            # Create state without role (we'll handle roles separately)
            state = State(
                scenario_id=scenario_id,
                name=name,
                description=state_data.description,
                prompts=prompts,  # Direct list - SQLAlchemy handles PostgreSQL ARRAY type
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
                        agent_role_id=agent_role_id
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
                            agent_role_id=agent_role.id
                        )
                        db.add(state_role)
                        logger.info(f"Created state_role for state: {name} and role: {role_name}")
                    else:
                        logger.error(f"Role {role_name} not found in database for state: {name}")
                        sys.exit(1)
            
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
                            agent_role_id=agent_role_id
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
                                agent_role_id=agent_role.id
                            )
                            db.add(state_role)
                            logger.info(f"Created state_role for state: {name} and role: {role_name}")
                        else:
                            logger.error(f"Role {role_name} not found in database for state: {name}")
                            sys.exit(1)
        
        db.commit()
        logger.info(f"All states created successfully for scenario: {scenario_id}")
        
        # Store states data in data_store
        set_states(state_ids)
        
        return state_ids
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find states: {str(e)}")
        sys.exit(1)