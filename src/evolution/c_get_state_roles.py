import logging
import time
import json
import uuid
from typing import List
from sqlalchemy.orm import Session
from agir_db.models.agent_role import AgentRole
from agir_db.models.state_role import StateRole

logger = logging.getLogger(__name__)

def c_get_state_roles(db: Session, state_id: int) -> List[AgentRole]:
  """
  Get all roles associated with a state.
  
  Args:
      db: Database session
      state_id: ID of the state
      
  Returns:
      List[AgentRole]: Roles associated with the state
  """
  try:
      # Get all role IDs for this state from the StateRole table
      state_roles = db.query(StateRole).filter(
          StateRole.state_id == state_id
      ).all()
      
      if not state_roles:
          logger.error(f"No roles found for state: {state_id}")
          return []
      
      # Get the actual AgentRole objects
      roles = []
      for state_role in state_roles:
          role = db.query(AgentRole).filter(
              AgentRole.id == state_role.agent_role_id
          ).first()
          
          if role:
              roles.append(role)
      
      return roles
      
  except Exception as e:
      logger.error(f"Failed to get state roles: {str(e)}")
      return []