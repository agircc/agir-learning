"""
YAML loading utilities
"""

import os
import logging
import yaml
import uuid
from typing import Dict, Any, Optional, List

from ..models.scenario import Scenario, State, StateTransition
from ..models.role import Role

logger = logging.getLogger(__name__)


def load_scenario_from_file(file_path: str) -> Optional[Scenario]:
    """
    Load a scenario from a YAML file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Scenario instance or None if loading failed
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        with open(file_path, "r") as f:
            yaml_content = f.read()
            
        data = yaml.safe_load(yaml_content)
        scenario_data = data.get("scenario", {}) or data.get("process", {})  # Support both new and old format
        
        # Extract states. They don't have explicit IDs in the YAML,
        # so we'll use their names as IDs for now
        state_name_to_id = {}
        states = []
        
        for i, state_data in enumerate(scenario_data.get("states", []) or scenario_data.get("nodes", [])):  # Support both new and old format
            state_name = state_data["name"]
            state_id = str(i+1)  # Use 1-indexed IDs
            state_name_to_id[state_name] = state_id
            
            # Handle roles as a list instead of a single role
            roles = state_data.get("roles", [])
            # For backwards compatibility, check if "role" is present and add it
            if "role" in state_data and state_data["role"] not in roles:
                roles.append(state_data["role"])
            
            states.append(State(
                id=state_id,
                name=state_name,
                roles=roles,  # Use the roles list
                description=state_data["description"],
                assigned_to=state_data.get("assigned_to")
            ))
            
        # Handle transitions, which use state names in the YAML
        transitions = []
        
        for transition_data in scenario_data.get("transitions", []):
            # Use the original state names for transitions - they will be resolved at database creation time
            transitions.append(StateTransition(
                from_state=transition_data["from"],
                to_state=transition_data["to"],
                condition=transition_data.get("condition", "")
            ))
            
        # Prepare roles
        roles = []
        for role_data in scenario_data.get("roles", []):
            # Add model field if present
            role_args = {}
            
            # If id is not provided, use name as id
            if "id" in role_data:
                role_args["id"] = role_data["id"]
            elif "name" in role_data:
                # Use name as id if id is not provided
                role_args["id"] = role_data["name"]
            else:
                # Skip if neither id nor name is provided
                logger.warning("Role without id or name found, skipping")
                continue
                
            # Add required fields
            if "name" in role_data:
                role_args["name"] = role_data["name"]
            else:
                # Use id as name if name is not provided
                role_args["name"] = role_args["id"]
                
            if "description" in role_data:
                role_args["description"] = role_data["description"]
            else:
                role_args["description"] = f"Role {role_args['name']}"
                
            # Add optional fields
            role_args["system_prompt_template"] = role_data.get("system_prompt_template", "")
            
            # Add model if present
            if "model" in role_data:
                role_args["model"] = role_data["model"]
                
            roles.append(Role(**role_args))
            
        return Scenario(
            name=scenario_data.get("name", "Unnamed Scenario"),
            description=scenario_data.get("description"),
            learner_role=scenario_data.get("learner_role"),
            learner=scenario_data.get("learner", {}),
            states=states,
            transitions=transitions,
            roles=roles,
            evolution=scenario_data.get("evolution", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to load scenario from file: {str(e)}")
        return None 