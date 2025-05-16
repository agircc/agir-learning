import logging

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union 
from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.schemas.scenario import ScenarioDTO
from agir_db.models.user import User
from src.common.data_store import set_scenario

logger = logging.getLogger(__name__)

def create_or_find_scenario(db: Session, scenario_name: str, description: str, learner_role: str, created_by: Optional[str] = None, default_user_id: Optional[int] = None) -> Optional[int]:
    """
    Create or find scenario based on YAML scenario.
    
    Args:
        db: Database session
        scenario_name: Name of the scenario
        description: Description of the scenario
        learner_role: Role of the learner
        created_by: Username of creator (optional)
        default_user_id: User ID to use as default creator if created_by is None
        
    Returns:
        Optional[int]: ID of the scenario if successful, None otherwise
    """
    try:
        # Check if scenario exists
        query = db.query(Scenario).filter(Scenario.name == scenario_name)
        if created_by:
            query = query.filter(Scenario.created_by == created_by)
            
        scenario = query.first()
        
        if scenario:
            logger.info(f"Found existing scenario: {scenario_name}")
            
            # Store scenario data in data_store
            scenario_info = ScenarioDTO.model_validate(scenario)
            set_scenario(scenario_info)
            
            return scenario.id
        
        # If created_by is None, use default_user_id or find the first admin user
        creator_id = None
        if created_by:
            # Find user by username
            creator = db.query(User).filter(User.username == created_by).first()
            if creator:
                creator_id = str(creator.id)
            else:
                logger.warning(f"User with username {created_by} not found")
        
        # If still no creator_id, use default_user_id
        if not creator_id and default_user_id:
            creator_id = str(default_user_id)
            logger.info(f"Using target user as scenario creator since created_by was not provided")
        
        # If still no creator_id, find an admin user
        if not creator_id:
            admin_user = db.query(User).filter(User.is_active == True).first()
            if admin_user:
                creator_id = str(admin_user.id)
                logger.info(f"Using first active user as scenario creator: {admin_user.username}")
            else:
                logger.error("No active users found in database to use as scenario creator")
                return None
        
        # Create new scenario with the determined creator_id
        scenario = Scenario(
            name=scenario_name,
            description=description,
            created_by=creator_id,
            learner_role=learner_role
        )
        
        db.add(scenario)
        db.commit()
        logger.info(f"Created new scenario: {scenario_name} with ID: {scenario.id}, creator ID: {creator_id}")
        
        # Store scenario data in data_store
        scenario_info = ScenarioDTO.model_validate(scenario)
        set_scenario(scenario_info)
        
        return scenario.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create or find scenario: {str(e)}")
        return None
