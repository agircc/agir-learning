import logging

from sqlalchemy.orm import Session
from src.db.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.process_role import ProcessRole

logger = logging.getLogger(__name__)

def create_or_find_process_roles(db: Session, process_id: int, roles: List[Union[Dict[str, Any], Any]]) -> Optional[Dict[str, int]]:
    """
    Create roles for a process based on YAML process.
    
    Args:
        db: Database session
        process_id: ID of the process
        roles: List of roles
        
    Returns:
        Optional[Dict[str, int]]: Mapping of role names to IDs if successful, None otherwise
    """
    try:
        if not roles:
            logger.warning("No roles defined in process YAML")
            return {}
        
        # Create role ID mapping
        role_id_mapping = {}
        
        # Process each role
        for role_data in roles:
            role_name = None
            role_description = None
            model = None
            
            # Handle both formats (dict and Role object)
            if isinstance(role_data, dict):
                role_name = role_data.get("name") or role_data.get("id")
                role_description = role_data.get("description", "")
                model = role_data.get("model", "")  # Get model from role data
            else:
                role_name = role_data.name or role_data.id
                role_description = role_data.description
                # Try to get model from role object attributes
                model = getattr(role_data, "model", "") if hasattr(role_data, "model") else ""
            
            if not role_name:
                logger.error("Role name not specified in YAML")
                continue
            
            # Log role information for debugging
            logger.debug(f"Processing role: name='{role_name}', description='{role_description}', model='{model}'")
            
            # Check if role exists - use case-insensitive comparison for name
            existing_roles = db.query(ProcessRole).filter(
                ProcessRole.process_id == process_id
            ).all()
            
            role = None
            for existing_role in existing_roles:
                if existing_role.name.lower() == role_name.lower():
                    role = existing_role
                    break
            
            if role:
                logger.info(f"Found existing role: {role.name} (matched with '{role_name}')")
                # Update model if it's provided
                if model and hasattr(role, "model"):
                    role.model = model
                    db.commit()
                    logger.info(f"Updated role model to {model}")
            else:
                # Create role data
                role_data = {
                    "process_id": process_id,
                    "name": role_name,
                    "description": role_description
                }
                
                # Add model if it exists
                if model:
                    role_data["model"] = model
                
                # Create role
                role = ProcessRole(**role_data)
                db.add(role)
                db.commit()
                logger.info(f"Created new role: {role_name} with ID: {role.id}")
            
            # Add to mapping
            role_id_mapping[role_name] = role.id
        
        return role_id_mapping
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create roles: {str(e)}")
        return None