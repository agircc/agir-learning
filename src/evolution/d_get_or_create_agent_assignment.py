@staticmethod
def d_get_or_create_agent_assignment(db: Session, role_id: int, episode_id: int) -> Optional[User]:
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
      # Try to find existing agent assignment for this episode
      episode = db.query(Episode).filter(Episode.id == episode_id).first()
      if not episode:
          logger.error(f"Episode not found: {episode_id}")
          return None
      
      role = db.query(AgentRole).filter(AgentRole.id == role_id).first()
      if not role:
          logger.error(f"Role not found: {role_id}")
          return None
      
      # Check if agent assignment exists
      agent_assignment = db.query(AgentAssignment).filter(
          AgentAssignment.role_id == role_id
      ).first()
      
      if agent_assignment:
          # User exists for this role
          user = db.query(User).filter(User.id == agent_assignment.user_id).first()
          if user:
              logger.info(f"Found existing user {user.username} for role {role.name}")
              return user
      
      # Create a new user for this role
      logger.info(f"Creating new user for role {role.name} in scenario {episode.scenario_id}")
      user = create_agent_assignment(
          db, 
          role.name, 
          episode.scenario_id, 
          username=f"{role.name}_{episode.id}",
          model=getattr(role, 'model', None)
      )
      
      return user
      
  except Exception as e:
      logger.error(f"Failed to get or create agent assignment: {str(e)}")
      return None