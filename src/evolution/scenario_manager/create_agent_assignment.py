import logging
import sys
from uuid import uuid4
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.agent_assignment import AgentAssignment
from src.common.data_store import get_learner, get_scenario, set_learner
import random
import time
from datetime import datetime

from src.evolution.store import get_episode
from src.llm.user_generator import generate_user_with_llm
from src.common.utils.memory_utils import DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

def create_agent_assignment(db: Session, role: str, scenario_id: Any, username: Optional[str] = None, model: Optional[str] = None, embedding_model: Optional[str] = None) -> User:
    """
    Create a user for a specific role and scenario and associate them in agent_assignments.
    
    Args:
        db: Database session
        role: Role name
        scenario_id: ID of the scenario
        username: Username (optional, will be generated if None)
        model: LLM model to use (optional)
        embedding_model: Embedding model to use (optional)
        
    Returns:
        User: Created or found user
    """
    try:
        scenario = get_scenario()
        episode = get_episode()
        
        # Check if this is the learner role (if scenario is available)
        learner_role = None
        if scenario:
            logger.info(f"Scenario learner role: {scenario.learner_role}")
            learner_role = scenario.learner_role
        else:
            logger.warning("Scenario not found in data store, creating user without learner role check")
        
        if learner_role and learner_role == role:
            # Use existing learner
            learner = get_learner()
            if learner:
                logger.info(f"Using existing learner: {learner.username}")
                user = db.query(User).filter(User.id == learner.id).first()
                if user:
                    return user
            else:
                logger.error("No learner found in data store")
                sys.exit(1)
        
        # Find or create user
        if username:
            user = db.query(User).filter(User.username == username).first()
        else:
            user = None
        
        if not user:
            llm_model = model
            
            # Get scenario description if available for better context
            scenario_description = getattr(scenario, 'description', None) if scenario else None
            
            # Use default embedding model if not specified
            if not embedding_model:
                embedding_model = DEFAULT_EMBEDDING_MODEL
            
            # Generate user with LLM
            user, memory_ids = generate_user_with_llm(
                db=db,
                role=role,
                model_name=llm_model,
                username=username,
                scenario_id=scenario_id,
                scenario_description=scenario_description,
                embedding_model=embedding_model
            )
            
            logger.info(f"Created new LLM-generated user: {user.username} with ID: {user.id} and {len(memory_ids)} memories")
        
        # Find the agent role if episode exists
        if episode:
            agent_role = db.query(AgentRole).filter(
                AgentRole.scenario_id == scenario_id,
                AgentRole.name == role
            ).first()
            
            if not agent_role:
                logger.warning(f"Role '{role}' not found for scenario {scenario_id}. Creating a default role.")
                sys.exit(1)
            
            # Create role-user association if it doesn't exist
            existing_assignment = db.query(AgentAssignment).filter(
                AgentAssignment.role_id == agent_role.id,
                AgentAssignment.user_id == user.id,
                AgentAssignment.episode_id == episode.id
            ).first()
            
            if not existing_assignment:
                agent_assignment = AgentAssignment(
                    role_id=agent_role.id,
                    user_id=user.id,
                    episode_id=episode.id
                )
                
                db.add(agent_assignment)
                logger.info(f"Created agent assignment for user {user.username} with role {role}")
            
            # Set as learner if this is the learner role
            if scenario and scenario.learner_role == role:
                set_learner(user)
        else:
            logger.warning(f"Episode not found, skipping agent assignment creation for user {user.username}")
        
        db.commit()
        
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create agent assignment: {str(e)}")
        raise
