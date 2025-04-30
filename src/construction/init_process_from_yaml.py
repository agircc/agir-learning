import logging

from src.construction.create_or_find_learner import create_or_find_learner
from src.construction.create_or_find_process import create_or_find_process
from src.construction.create_or_find_process_roles import create_or_find_process_roles
from src.construction.create_or_find_process_nodes import create_or_find_process_nodes
from src.construction.create_or_find_process_transitions import create_or_find_process_transitions
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from src.utils.yaml_loader import load_process_from_file
from agir_db.db.session import get_db

logger = logging.getLogger(__name__)

def init_process_from_yaml(yaml_file_path: str, created_by: Optional[str] = None) -> Optional[int]:
        """
        Create a process from a YAML file.
        
        Args:
            yaml_file_path: Path to the YAML file
            created_by: Username of the creator (optional)
            
        Returns:
            Optional[int]: ID of the created process if successful, None otherwise
        """
        # Check if database tables exist
        if not check_database_tables():
            logger.error("Database tables check failed. Please run database migrations.")
            return None
        
        # Load process from YAML
        yaml_process = load_process_from_file(yaml_file_path)
        if not yaml_process:
            logger.error(f"Failed to load process from {yaml_file_path}")
            return None
        
        # Create or update database records
        try:
            db = next(get_db())
            
            # 1. Create or find target user
            learner_id = create_or_find_learner(db, yaml_process.learner)
            if not learner_id:
                return None
            
            # 2. Create or find process
            process_id = create_or_find_process(db, yaml_process.name, yaml_process.description, yaml_process.learner_role, created_by, learner_id)
            if not process_id:
                return None
            
            # 3. Create roles
            role_id_mapping = create_or_find_process_roles(db, process_id, yaml_process.roles)
            if not role_id_mapping:
                return None
            
            # 4. Create nodes
            node_id_mapping = create_or_find_process_nodes(db, process_id, yaml_process.nodes, role_id_mapping)
            if not node_id_mapping:
                return None
            
            # 5. Create transitions
            if not create_or_find_process_transitions(db, process_id, yaml_process.transitions, node_id_mapping):
                return None
            
            return process_id
            
        except Exception as e:
            logger.error(f"Failed to initialize process from {yaml_file_path}: {str(e)}")
            return None