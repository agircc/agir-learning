import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.scenario import State, StateRole
from src.construction.data_store import set_process_nodes

logger = logging.getLogger(__name__)

def create_or_find_process_nodes(db: Session, process_id: int, nodes_data: List[Dict[str, Any]]) -> bool:
    """
    Create or find process nodes based on YAML process nodes.
    
    Args:
        db: Database session
        process_id: ID of the process
        nodes_data: List of node data from YAML
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Keep track of node IDs for lookup
        node_ids = {}
        
        # Create nodes
        for node_data in nodes_data:
            name = node_data.get("name")
            if not name:
                logger.error("Node name is required")
                return False
            
            # Check if node exists
            node = db.query(State).filter(
                State.scenario_id == process_id,
                State.name == name
            ).first()
            
            if node:
                logger.info(f"Node already exists: {name}")
                node_ids[name] = node.id
                continue
            
            # Create node
            node = State(
                scenario_id=process_id,
                name=name,
                description=node_data.get("description", ""),
                role=node_data.get("role", ""),
                is_required=node_data.get("is_required", True),
                external_id=str(uuid4())
            )
            
            db.add(node)
            db.flush()  # Get ID without committing
            
            logger.info(f"Created node: {name} with ID: {node.id}")
            node_ids[name] = node.id
            
            # Handle node roles if present
            roles_data = node_data.get("roles", [])
            if roles_data:
                for role_data in roles_data:
                    role_name = role_data.get("name")
                    if not role_name:
                        continue
                    
                    # Check if node role exists
                    node_role = db.query(StateRole).filter(
                        StateRole.state_id == node.id,
                        StateRole.name == role_name
                    ).first()
                    
                    if node_role:
                        logger.info(f"Node role already exists: {role_name} for node: {name}")
                        continue
                    
                    # Create node role
                    node_role = StateRole(
                        state_id=node.id,
                        name=role_name,
                        description=role_data.get("description", "")
                    )
                    
                    db.add(node_role)
                    logger.info(f"Created node role: {role_name} for node: {name}")
        
        db.commit()
        logger.info(f"All nodes created successfully for process: {process_id}")
        
        # Store nodes data in data_store
        set_process_nodes(node_ids)
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find process nodes: {str(e)}")
        return False