import logging

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.agent_role import AgentRole
from src.construction.data_store import set_agent_roles

logger = logging.getLogger(__name__)

def create_or_find_agent_roles(
    db: Session, 
    scenario_id: int, 
    roles_data: List[Dict[str, str]]
) -> Optional[Dict[str, int]]:
    """
    Create or find agent roles based on YAML roles data.
    
    Args:
        db: Database session
        scenario_id: ID of the scenario
        roles_data: List of role data from YAML
        
    Returns:
        Optional[Dict[str, int]]: Mapping of YAML role names to database role IDs if successful, None otherwise
    """
    try:
        role_id_mapping = {}
        
        # Create special learner role if not in roles_data
        has_learner = any(role.get("name") == "learner" for role in roles_data)
        if not has_learner:
            # Add learner role automatically
            roles_data.append({"name": "learner", "description": "Learner role"})
        
        for role_data in roles_data:
            role_name = role_data.get("name")
            if not role_name:
                logger.error("Role name is required")
                continue
            
            # Check if role exists
            existing = db.query(AgentRole).filter(
                AgentRole.scenario_id == scenario_id,
                AgentRole.name == role_name
            ).first()
            
            if existing:
                logger.info(f"Role already exists: {role_name}")
                role_id_mapping[role_name] = existing.id
                continue
            
            # Create role
            role = AgentRole(
                scenario_id=scenario_id,
                name=role_name,
                description=role_data.get("description", ""),
                model=role_data.get("model", "")
            )
            
            db.add(role)
            db.flush()  # Get ID without committing
            
            role_id_mapping[role_name] = role.id
            logger.info(f"Created role: {role_name} with ID: {role.id}")
        
        db.commit()
        logger.info(f"Created or found {len(role_id_mapping)} agent roles")
        
        # Store in data store
        roles_list = [
            {
                "id": role_id,
                "name": role_name,
                "description": roles_data[i].get("description", "") if i < len(roles_data) else "",
                "model": roles_data[i].get("model", "") if i < len(roles_data) else ""
            }
            for i, (role_name, role_id) in enumerate(role_id_mapping.items())
        ]
        set_agent_roles(roles_list)
        
        return role_id_mapping
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create agent roles: {str(e)}")
        return None