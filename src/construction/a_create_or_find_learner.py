import logging
import json

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.schemas.user import UserDTO
from src.common.data_store import set_learner, get_scenario
from src.llm.user_generator import generate_user_with_llm
from src.common.utils.memory_utils import DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

def create_or_find_learner(db: Session, learner_data: Dict[str, Any]) -> Optional[int]:
        """
        Create or find target user based on YAML process.
        
        Args:
            db: Database session
            learner_data: learner data from YAML process
            
        Returns:
            Optional[int]: ID of the target user if successful, None otherwise
        """
        try:
            username = learner_data.get("username")
            
            if not username:
                logger.error("Target user username not specified in process YAML")
                return None
            
            # Check if user exists
            user = db.query(User).filter(User.username == username).first()
            
            if user:
                logger.info(f"Found existing user: {username}")
                # Store learner data in data_store
                learner_info = UserDTO(
                    id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    llm_model=user.llm_model,
                    email=user.email
                )
                set_learner(learner_info)
                
                return user.id
            
            # Get scenario for context if available
            scenario = get_scenario()
            scenario_description = scenario.description if scenario else None
            
            # Get model from learner data or use default
            model_name = learner_data.get("model", "gpt-3.5-turbo")
            
            # Extract YAML-defined profile data
            yaml_profile = {
                "first_name": learner_data.get("first_name"),
                "last_name": learner_data.get("last_name"),
                "gender": learner_data.get("gender"),
                "birth_date": learner_data.get("birth_date"),
                "profession": learner_data.get("profession"),
                "skills": learner_data.get("skills", []),
                "interests": learner_data.get("interests", []),
                "personality_traits": learner_data.get("personality_traits", []),
                "background": learner_data.get("background"),
                "description": learner_data.get("description")
            }
            
            # Remove None values from yaml_profile
            yaml_profile = {k: v for k, v in yaml_profile.items() if v is not None}
            
            # Generate user with LLM including profile and memories
            user, memory_ids = generate_user_with_llm(
                db=db,
                role="learner",
                model_name=model_name,
                username=username,
                scenario_description=scenario_description,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                existing_profile=yaml_profile  # Pass YAML profile to merge with LLM generation
            )
            
            logger.info(f"Created new learner: {username} with ID: {user.id} and {len(memory_ids)} memories")
            
            # Store learner data in data_store
            learner_info = UserDTO(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                llm_model=user.llm_model,
                email=user.email
            )
            set_learner(learner_info)
            
            return user.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create or find target user: {str(e)}")
            return None