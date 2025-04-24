def learner_generate_response(self, node: ProcessNode, context: Dict[str, Any]) -> str:
  """
  Simulate a response from the target user.
  
  In a real system, this would involve actual user interaction.
  
  Args:
      node: Current node
      context: Context information
      
  Returns:
      Simulated response
      
  Raises:
      ValueError: If user has no model specified
  """
  # Get the user ID from context
  user_id = context.get('user_id')
  if not user_id:
      raise ValueError("User ID not found in context")
      
  # Get the user from database
  with SessionLocal() as db:
      user = db.query(User).filter(User.id == user_id).first()
      if not user:
          raise ValueError(f"User with ID {user_id} not found")
          
      # Check if user has a model specified
      if not hasattr(user, 'llm_model') or not user.llm_model:
          raise ValueError(f"User '{user.username}' has no model specified")
          
      # Get the appropriate LLM provider for this user
      llm_provider = self.llm_provider_manager.get_provider(user.llm_model)
      
      # Generate system prompt
      system_prompt = (
          f"You are {context['user_name']}, a {node.role}. "
          f"You are currently in the '{node.name}' phase of a process. "
          f"Respond as if you are this person."
      )
      
      # Generate prompt
      prompt = (
          f"Phase description: {node.description}\n\n"
          f"Please provide your response as {context['user_name']}."
      )
      
      logger.info(f"Generating response for {context['user_name']} using model: {user.llm_model}")
      return llm_provider.generate(
          prompt=prompt,
          system_prompt=system_prompt,
          temperature=0.7
      )