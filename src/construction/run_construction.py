import logging

from src.construction.create_or_find_learner import create_or_find_learner
from src.construction.create_or_find_scenario import create_or_find_scenario
from src.construction.create_or_find_agent_roles import create_or_find_agent_roles
from src.construction.create_or_find_states import create_or_find_states
from src.construction.create_or_find_state_transitions import create_or_find_state_transitions
from src.construction.check_database_tables import check_database_tables
from typing import Dict, Any, List, Optional, Tuple, Union
from src.utils.yaml_loader import load_scenario_from_file
from agir_db.db.session import get_db

logger = logging.getLogger(__name__)

def run_construction(yaml_file_path: str, created_by: Optional[str] = None) -> Optional[int]:
        """
        Create a scenario from a YAML file.
        
        Args:
            yaml_file_path: Path to the YAML file
            created_by: Username of the creator (optional)
            
        Returns:
            Optional[int]: ID of the created scenario if successful, None otherwise
        """
        # Check if database tables exist
        if not check_database_tables():
            logger.error("Database tables check failed. Please run database migrations.")
            return None
        
        # Load scenario from YAML
        yaml_scenario = load_scenario_from_file(yaml_file_path)
        if not yaml_scenario:
            logger.error(f"Failed to load scenario from {yaml_file_path}")
            return None
        
        # Create or update database records
        try:
            db = next(get_db())
            
            # 1. Create or find target user
            learner_id = create_or_find_learner(db, yaml_scenario.learner)
            if not learner_id:
                return None
            
            # 2. Create or find scenario
            scenario_id = create_or_find_scenario(db, yaml_scenario.name, yaml_scenario.description, yaml_scenario.learner_role, created_by, learner_id)
            if not scenario_id:
                return None
            
            # 3. Create roles
            role_id_mapping = create_or_find_agent_roles(db, scenario_id, yaml_scenario.roles)
            if not role_id_mapping:
                return None
            
            # 4. Create states
            state_id_mapping = create_or_find_states(db, scenario_id, yaml_scenario.states)
            if not state_id_mapping:
                return None
            
            # 5. Create transitions
            if not create_or_find_state_transitions(db, scenario_id, yaml_scenario.transitions, state_id_mapping):
                return None
            
            return scenario_id
            
        except Exception as e:
            logger.error(f"Failed to initialize scenario from {yaml_file_path}: {str(e)}")
            return None