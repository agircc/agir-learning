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
                assigned_to=state_data.get("assigned_to"),
                prompts=state_data.get("prompts")
            ))
        
        # Extract transitions between states
        transitions = []
        
        # Handle different transition formats
        transition_list = scenario_data.get("transitions", []) or scenario_data.get("edges", [])
        
        for transition_data in transition_list:
            # Handle different field naming conventions
            from_state_name = transition_data.get("from_state_name") or transition_data.get("from")
            to_state_name = transition_data.get("to_state_name") or transition_data.get("to")
            
            if not from_state_name or not to_state_name:
                logger.warning(f"Incomplete transition data: {transition_data}")
                continue
                
            # Get state IDs
            from_id = state_name_to_id.get(from_state_name)
            to_id = state_name_to_id.get(to_state_name)
            
            if not from_id or not to_id:
                logger.warning(f"Invalid state reference in transition: {from_state_name} -> {to_state_name}")
                continue
                
            transitions.append(StateTransition(
                from_state_name=from_state_name,
                to_state_name=to_state_name,
                condition=transition_data.get("condition", "")
            ))
        
        # Extract role information
        roles = []
        for i, role_data in enumerate(scenario_data.get("roles", [])):
            if isinstance(role_data, dict):
                # Use name as ID or generate a unique ID if name is not suitable
                role_id = role_data.get("id", role_data["name"])
                capabilities = role_data.get("capabilities", [])
                
                roles.append(Role(
                    id=role_id,
                    name=role_data["name"],
                    description=role_data.get("description", ""),
                    system_prompt_template=role_data.get("system_prompt_template"),
                    model=role_data.get("model"),
                    required_skills=role_data.get("required_skills", []),
                    knowledge_sources=role_data.get("knowledge_sources", [])
                ))
            else:
                # Simple string format - use the string as both ID and name
                role_name = str(role_data)
                roles.append(Role(
                    id=role_name,
                    name=role_name,
                    description="",
                    system_prompt_template=None,
                    required_skills=[],
                    knowledge_sources=[]
                ))
                
        # Extract learner information
        learner = scenario_data.get("learner", {})
        learner_role = scenario_data.get("learner_role")
        
        # Create scenario
        scenario = Scenario(
            name=scenario_data.get("name", "Unnamed Scenario"),
            description=scenario_data.get("description", ""),
            states=states,
            transitions=transitions,
            roles=roles,
            learner=learner,
            learner_role=learner_role,
            evolution=scenario_data.get("evolution", {})
        )
        
        return scenario
        
    except Exception as e:
        logger.error(f"Failed to load scenario from {file_path}: {str(e)}")
        return None 