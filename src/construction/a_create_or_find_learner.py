import logging
import json

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.schemas.user import UserDTO
from src.construction.data_store import set_learner

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
            
            # Prepare user data
            user_data = {
                "username": username,
                "first_name": learner_data.get("first_name", ""),
                "last_name": learner_data.get("last_name", ""),
                "email": learner_data.get("email", f"{username}@example.com"),
                "is_active": True
            }
            
            # Add model if it exists in YAML
            if "model" in learner_data:
                user_data["llm_model"] = learner_data["model"]
            
            # Create new user
            user = User(**user_data)
            
            # Add additional profile data
            profile_data = {}
            for key, value in learner_data.items():
                if key not in ["username", "first_name", "last_name", "email", "model"]:
                    profile_data[key] = value
            
            if profile_data:
                user.profile = json.dumps(profile_data)
            
            db.add(user)
            db.commit()
            logger.info(f"Created new user: {username} with ID: {user.id}")
            
            # Store learner data in data_store
            learner_info = UserDTO(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email
            )
            set_learner(learner_info)
            
            return user.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create or find target user: {str(e)}")
            return None