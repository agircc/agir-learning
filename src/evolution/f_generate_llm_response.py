import logging
import sys
from typing import List, Optional
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.step import Step
from src.llms.llm_provider_manager import LLMProviderManager
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def f_generate_llm_response(db: Session, state: State, current_state_role: AgentRole, user: User, previous_steps: List[Step]) -> Optional[str]:
  """
  Generate LLM response for a state using the appropriate LLM provider.
  
  Args:
      db: Database session
      state: State in the scenario
      current_state_role: Agent role for this state
      user: User associated with the state
      previous_steps: Previous steps in the scenario
      
  Returns:
      Optional[str]: Generated response if successful, None otherwise
  """
  try:
      # Create context from previous steps
      context = {
          "state_name": state.name,
          "state_description": state.description,
          "history": []
      }
      
      # Add previous step data to history
      for step in previous_steps:
          if step.generated_text:
              context["history"].append({
                  "step_id": step.id,
                  "state_id": step.state_id,
                  "user_id": step.user_id,
                  "content": step.generated_text
              })
      
      # Get the appropriate LLM model from the user
      model_name = user.llm_model
      if not model_name:
          sys.exit(1)
      
      logger.info(f"Using model {model_name} for state {state.name}")
      
      # Initialize LLM provider manager
      llm_provider_manager = LLMProviderManager()
      provider = llm_provider_manager.get_provider(model_name)
      
      # Build prompt
      prompt = f"""You are a human working on a scenario called "{state.name}".
      
Your role: {user.username}
Task: {state.description}

"""
      
      # Add conversation history if available
      if context["history"]:
          prompt += "Previous conversation:\n\n"
          for i, entry in enumerate(context["history"]):
              prompt += f"Step {i+1}: {entry['content']}\n\n"
      
      prompt += f"Please respond as {user.username} for the current step: {state.name}\n"
      
      # Call the LLM provider to generate a response
      response = provider.generate(prompt)
      
      logger.info(f"Generated LLM response for state {state.name} with user {user.username}")
      
      return response
      
  except Exception as e:
      logger.error(f"Failed to generate LLM response: {str(e)}")
      return f"Error generating response: {str(e)}" 