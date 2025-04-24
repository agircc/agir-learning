   
def _get_provider_for_node(self, db: Session, node: ProcessNode, default_provider: BaseLLMProvider) -> BaseLLMProvider:
  """
  Get the appropriate LLM provider for a node based on its role's model.
  
  Args:
      db: Database session
      node: Process node
      default_provider: Default provider to use if no specific model is found (ignored)
      
  Returns:
      LLM provider instance
      
  Raises:
      ValueError: If no model is specified for the role or user
  """
  if not self.llm_provider_manager:
      raise ValueError("LLM provider manager is required")
      
  # Get the role for this node
  if not node.role:
      raise ValueError(f"Node {node.name} has no role specified")
      
  # Special handling for learner role
  if node.role == "learner":
      # Get the learner user
      if hasattr(node, 'assigned_to') and node.assigned_to:
          user = db.query(User).filter(User.username == node.assigned_to).first()
          if user and hasattr(user, 'llm_model') and user.llm_model:
              logger.info(f"Using learner's model '{user.llm_model}' for node: {node.name}")
              return self.llm_provider_manager.get_provider(user.llm_model)
          else:
              raise ValueError(f"Learner user '{node.assigned_to}' has no model specified")
      
      # Try to find an active learner user
      user = db.query(User).filter(User.is_active == True).first()
      if user and hasattr(user, 'llm_model') and user.llm_model:
          logger.info(f"Using active user's model '{user.llm_model}' for learner node: {node.name}")
          return self.llm_provider_manager.get_provider(user.llm_model)
      else:
          raise ValueError("No active user with model specified found for learner role")
      
  # Query the database to get the role's model
  from agir_db.models.process_role import ProcessRole
  role = db.query(ProcessRole).filter(ProcessRole.id == node.role).first()
  
  if not role:
      raise ValueError(f"Role with ID {node.role} not found")
      
  if not hasattr(role, 'model') or not role.model:
      # Try to get the model from assigned_to user if available
      if hasattr(node, 'assigned_to') and node.assigned_to:
          user = db.query(User).filter(User.username == node.assigned_to).first()
          if user and hasattr(user, 'llm_model') and user.llm_model:
              logger.info(f"Using assigned user's model '{user.llm_model}' for node: {node.name}")
              return self.llm_provider_manager.get_provider(user.llm_model)
          else:
              raise ValueError(f"Assigned user '{node.assigned_to}' for node {node.name} has no model specified")
      else:
          raise ValueError(f"Role '{role.name}' has no model specified and node is not assigned to a user")
      
  # Use the model specified for the role
  logger.info(f"Using role's model '{role.model}' for node: {node.name}")
  return self.llm_provider_manager.get_provider(role.model)