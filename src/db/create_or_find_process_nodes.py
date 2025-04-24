import logging

from sqlalchemy.orm import Session
from src.db.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.process import ProcessNode

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
        
        for i, node in enumerate(nodes):
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
        logger.info(f"Created {len(node_id_mapping)} process nodes")
        
        return node_id_mapping
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create process nodes: {str(e)}")
        return None