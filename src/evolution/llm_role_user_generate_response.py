def role_user_generate_response(
  self, 
  node: ProcessNode, 
  context: Dict[str, Any],
  history: List[Dict[str, Any]]
) -> str:
  """
  Generate a prompt for an agent.
  
  Args:
      node: Current node
      context: Context information
      history: Conversation history
      
  Returns:
      Formatted prompt string
  """
  prompt_parts = [
      f"You are now in the '{node.name}' phase.",
      node.description,
      "\nPrevious conversation:",
  ]
  
  # Add conversation history
  if history:
      for i, entry in enumerate(history):
          prompt_parts.append(f"{i+1}. {entry['role']}: {entry['content']}")
  else:
      prompt_parts.append("No previous conversation.")
      
  prompt_parts.append("\nPlease respond based on your role and the current phase.")
  
  return "\n".join(prompt_parts)