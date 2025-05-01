"""
YAML loading utilities
"""

import os
import logging
import yaml
import uuid
from typing import Dict, Any, Optional, List

from ..models.process import Process, ProcessNode, ProcessTransition
from ..models.role import Role

logger = logging.getLogger(__name__)


def load_process_from_file(file_path: str) -> Optional[Process]:
    """
    Load a process from a YAML file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Process instance or None if loading failed
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        with open(file_path, "r") as f:
            yaml_content = f.read()
            
        data = yaml.safe_load(yaml_content)
        process_data = data.get("process", {})
        
        # Extract nodes. They don't have explicit IDs in the YAML,
        # so we'll use their names as IDs for now
        node_name_to_id = {}
        nodes = []
        
        for i, node_data in enumerate(process_data.get("nodes", [])):
            node_name = node_data["name"]
            node_id = str(i+1)  # Use 1-indexed IDs
            node_name_to_id[node_name] = node_id
            
            # Handle roles as a list instead of a single role
            roles = node_data.get("roles", [])
            # For backwards compatibility, check if "role" is present and add it
            if "role" in node_data and node_data["role"] not in roles:
                roles.append(node_data["role"])
            
            nodes.append(ProcessNode(
                id=node_id,
                name=node_name,
                roles=roles,  # Use the roles list
                description=node_data["description"],
                assigned_to=node_data.get("assigned_to")
            ))
            
        # Handle transitions, which use node names in the YAML
        transitions = []
        
        for transition_data in process_data.get("transitions", []):
            # Use the original node names for transitions - they will be resolved at database creation time
            transitions.append(ProcessTransition(
                from_node=transition_data["from"],
                to_node=transition_data["to"]
            ))
            
        # Prepare roles
        roles = []
        for role_data in process_data.get("roles", []):
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
            
        return Process(
            name=process_data.get("name", "Unnamed Process"),
            description=process_data.get("description"),
            learner_role=process_data.get("learner_role"),
            learner=process_data.get("learner", {}),
            nodes=nodes,
            transitions=transitions,
            roles=roles,
            evolution=process_data.get("evolution", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to load process from file: {str(e)}")
        return None 