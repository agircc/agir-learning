"""
YAML loading utilities
"""

import os
import logging
import yaml
import uuid
from typing import Dict, Any, Optional

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
            
            nodes.append(ProcessNode(
                id=node_id,
                name=node_name,
                role=node_data["role"],
                description=node_data["description"],
                assigned_to=node_data.get("assigned_to")
            ))
            
        # Handle transitions, which use node names in the YAML
        transitions = []
        
        for transition_data in process_data.get("transitions", []):
            # Handle transitions that use names rather than IDs
            from_node = transition_data["from"]
            to_node = transition_data["to"]
            
            # If from/to are names, convert to IDs using the mapping
            from_node_id = node_name_to_id.get(from_node, from_node)
            to_node_id = node_name_to_id.get(to_node, to_node)
            
            transitions.append(ProcessTransition(
                from_node=from_node_id,
                to_node=to_node_id
            ))
            
        # Prepare roles
        roles = []
        for role_data in process_data.get("roles", []):
            # Add model field if present
            role_args = {
                "id": role_data["id"],
                "name": role_data["name"],
                "description": role_data["description"],
                "system_prompt_template": role_data.get("system_prompt_template", "")
            }
            
            # Add model if present
            if "model" in role_data:
                role_args["model"] = role_data["model"]
                
            roles.append(Role(**role_args))
            
        return Process(
            name=process_data.get("name", "Unnamed Process"),
            description=process_data.get("description"),
            target_user=process_data.get("target_user", {}),
            nodes=nodes,
            transitions=transitions,
            roles=roles,
            evolution=process_data.get("evolution", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to load process from file: {str(e)}")
        return None 