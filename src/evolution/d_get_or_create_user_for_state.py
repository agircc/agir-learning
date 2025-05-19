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
    
    # Find users who have been assigned to this role in other scenarios
    # First, get all users assigned to this role
    role_assignments = db.query(AgentAssignment).filter(
        AgentAssignment.role_id == role_id
    ).all()
    
    # Find episodes with the current scenario
    episodes_in_scenario = db.query(Episode).filter(
        Episode.scenario_id == episode.scenario_id
    ).all()
    scenario_episode_ids = [ep.id for ep in episodes_in_scenario]
    
    # Find users who have been assigned to this role but not in the current scenario
    for assignment in role_assignments:
        # Check if this user has been assigned to any episode in the current scenario
        user_scenario_assignments = db.query(AgentAssignment).filter(
            AgentAssignment.user_id == assignment.user_id,
            AgentAssignment.episode_id.in_(scenario_episode_ids)
        ).first()
        
        # If user hasn't been assigned to this scenario yet, we can reuse them
        if not user_scenario_assignments:
            user = db.query(User).filter(User.id == assignment.user_id).first()
            if user:
                logger.info(f"Reusing existing user {user.username} for role {agentRole.name} in new scenario")
                # Create new assignment for this episode
                new_assignment = AgentAssignment(
                    user_id=user.id,
                    role_id=role_id,
                    episode_id=episode.id
                )
                db.add(new_assignment)
                db.commit()
                return user
      
    # If no existing user can be reused, create a new user for this role
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