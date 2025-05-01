import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.process import ProcessNode, ProcessNodeRole
from src.construction.data_store import set_process_nodes

logger = logging.getLogger(__name__)

def create_or_find_process_nodes(
    db: Session, 
    process_id: int, 
    nodes: List[Any],
    role_id_mapping: Dict[str, int]
) -> Optional[Dict[str, int]]:
    """
    Create process nodes from YAML process.
    
    Args:
        db: Database session
        process_id: ID of the process
        nodes: List of nodes
        role_id_mapping: Mapping of YAML role IDs to database role IDs
        
    Returns:
        Optional[Dict[str, int]]: Mapping of YAML node names to database node IDs if successful, None otherwise
    """
    try:
        node_id_mapping = {}
        
        # Fetch existing nodes for this process to avoid duplicates
        existing_nodes = db.query(ProcessNode).filter(
            ProcessNode.process_id == process_id
        ).all()
        
        # Create mapping of existing node names to node objects
        existing_node_map = {node.name.lower(): node for node in existing_nodes}
        
        for i, node in enumerate(nodes):
            # Check if node already exists (case-insensitive)
            existing_node = existing_node_map.get(node.name.lower())
            
            if existing_node:
                logger.info(f"Found existing node: {existing_node.name}")
                node_id = existing_node.id
            else:
                # Create new node without role_id (multiple roles are handled by ProcessNodeRole)
                db_node = ProcessNode(
                    process_id=process_id,
                    name=node.name,
                    description=node.description,
                    node_type="STANDARD"  # Default node type
                )
                
                db.add(db_node)
                db.flush()  # Get the ID without committing
                node_id = db_node.id
            
            # Now handle multiple roles for this node
            for role_name in node.roles:
                if role_name == "learner":
                    # Special handling for "learner" role
                    continue
                
                # Get the role ID from the mapping
                role_id = role_id_mapping.get(role_name)
                if not role_id:
                    logger.warning(f"Role not found for node: {node.name}, role: {role_name}")
                    continue
                
                # Check if node-role relationship already exists
                existing_node_role = db.query(ProcessNodeRole).filter(
                    ProcessNodeRole.process_node_id == node_id,
                    ProcessNodeRole.process_role_id == role_id
                ).first()
                
                if not existing_node_role:
                    # Create node-role relationship only if it doesn't exist
                    node_role = ProcessNodeRole(
                        process_node_id=node_id,
                        process_role_id=role_id
                    )
                    db.add(node_role)
                    logger.info(f"Created node-role relationship for node: {node.name}, role: {role_name}")
            
            # In the YAML file, nodes don't have explicit IDs, so use the name as key
            node_id_mapping[node.name] = node_id
        
        db.commit()
        logger.info(f"Created or found {len(node_id_mapping)} process nodes")
        
        # Store nodes data in data_store
        set_process_nodes(node_id_mapping)
        
        return node_id_mapping
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process nodes: {str(e)}")
        return None