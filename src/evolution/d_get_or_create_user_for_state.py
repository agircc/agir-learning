import logging
import sys
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.episode import Episode
from agir_db.models.agent_assignment import AgentAssignment
from src.evolution.scenario_manager.create_agent_assignment import create_agent_assignment
from src.evolution.store import get_episode

logger = logging.getLogger(__name__)

def d_get_or_create_user_for_state(db: Session, role_id: int) -> Optional[User]:
  """
  Get or create a user for a role in an episode.
  
  Args:
      db: Database session
      role_id: ID of the role
      episode_id: ID of the episode
      
  Returns:
      Optional[User]: User if found or created, None otherwise
  """
  try:
    episode = get_episode()
      
    if not episode:
      logger.error(f"Episode not found")
      sys.exit(1)
      
    agentRole = db.query(AgentRole).filter(AgentRole.id == role_id).first()
    if not agentRole:
        logger.error(f"Role not found: {role_id}")
        sys.exit(1)
      
    # Check if agent assignment exists
    agent_assignment = db.query(AgentAssignment).filter(
        AgentAssignment.role_id == role_id,
        AgentAssignment.episode_id == episode.id
    ).first()
      
    if agent_assignment:
        # User exists for this role
        user = db.query(User).filter(User.id == agent_assignment.user_id).first()
        if user:
            logger.info(f"Found existing user {user.username} for role {agentRole.name}")
            return user
      
      # Create a new user for this role
    logger.info(f"Creating new user for role {agentRole.name} in scenario {episode.scenario_id}")
    user = create_agent_assignment(
      db, 
      agentRole.name, 
      episode.scenario_id, 
      username=f"{agentRole.name}_{episode.id}",
      model=getattr(agentRole, 'model', None)
    )
      
    return user
      
  except Exception as e:
      logger.error(f"Failed to get or create agent assignment: {str(e)}")
      return None