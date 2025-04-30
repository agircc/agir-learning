import logging

from sqlalchemy.orm import Session
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.process import ProcessNode
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
                node_id_mapping[node.name] = existing_node.id
                continue
                
            # Special handling for "learner" role - don't try to find a role_id
            role_id = None
            if node.role != "learner":
                # Get the role ID from the mapping
                role_id = role_id_mapping.get(node.role)
                if not role_id:
                    logger.warning(f"Role not found for node: {node.name}, role: {node.role}")
            
            db_node = ProcessNode(
                process_id=process_id,
                name=node.name,
                description=node.description,
                role_id=role_id,
                node_type="STANDARD"  # Default node type
            )
            
            db.add(db_node)
            db.flush()  # Get the ID without committing
            
            # In the YAML file, nodes don't have explicit IDs, so use the name as key
            node_id_mapping[node.name] = db_node.id
        
        db.commit()
        logger.info(f"Created or found {len(node_id_mapping)} process nodes")
        
        # Store nodes data in data_store
        set_process_nodes(node_id_mapping)
        
        return node_id_mapping
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process nodes: {str(e)}")
        return None