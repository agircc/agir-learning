import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.process_role import ProcessRole
from agir_db.models.process import Process, ProcessNode, ProcessTransition
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.process_instance_step import ProcessInstanceStep
from src.llms.llm_provider_manager import LLMProviderManager
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
def generate_llm_response(db: Session, node: ProcessNode, current_node_role: ProcessRole, user: User, previous_steps: List[ProcessInstanceStep]) -> Optional[str]:
  """
  Generate LLM response for a node using the appropriate LLM provider.
  
  Args:
      db: Database session
      node: Process node
      user: User associated with the node
      previous_steps: Previous steps in the process
      
  Returns:
      Optional[str]: Generated response if successful, None otherwise
  """
  try:
      # Create context from previous steps
      context = {
          "node_name": node.name,
          "node_description": node.description,
          "history": []
      }
      
      # Add previous step data to history
      for step in previous_steps:
          if step.comment:
              context["history"].append({
                  "step_id": step.id,
                  "node_id": step.node_id,
                  "user_id": step.user_id,
                  "content": step.comment
              })
      
      # Get the appropriate LLM model from the user
      model_name = user.llm_model
      if not model_name:
          if current_node_role and hasattr(current_node_role, 'model') and current_node_role.model:
              model_name = current_node_role.model
      
      logger.info(f"Using model {model_name} for node {node.name}")
      
      # Initialize LLM provider manager
      llm_provider_manager = LLMProviderManager()
      provider = llm_provider_manager.get_provider(model_name)
      
      # Build prompt
      prompt = f"""You are an AI assistant working on a process called "{node.name}".
      
Your role: {user.username}
Task: {node.description}

"""
      
      # Add conversation history if available
      if context["history"]:
          prompt += "Previous conversation:\n\n"
          for i, entry in enumerate(context["history"]):
              prompt += f"Step {i+1}: {entry['content']}\n\n"
      
      prompt += f"Please respond as {user.username} for the current step: {node.name}\n"
      
      # Call the LLM provider to generate a response
      response = provider.generate(prompt)
      
      logger.info(f"Generated LLM response for node {node.name} with user {user.username}")
      
      return response
      
  except Exception as e:
      logger.error(f"Failed to generate LLM response: {str(e)}")
      return f"Error generating response: {str(e)}"