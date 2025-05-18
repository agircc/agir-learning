import logging
import sys
from typing import List, Optional, Dict
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.step import Step
from sqlalchemy.orm import Session

from src.llm.llm_provider import get_llm_model, call_llm_with_memory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import BaseMessage

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
      # Get the appropriate LLM model from the user
      model_name = user.llm_model
      if not model_name:
          logger.error("User has no LLM model specified")
          sys.exit(1)
      
      logger.info(f"Using model {model_name} for state {state.name}")
      
      # Get user ID for memory functionality
      user_id = str(user.id)
      
      # Get LangChain model (without memory patching)
      llm_model = get_llm_model(model_name)
      
      # Prepare system prompt
      system_prompt = f"You are a human working on a scenario called \"{state.name}\". Your role is {user.username}. Task: {state.description}"
      
      # Convert previous steps to LangChain message format
      messages = [SystemMessage(content=system_prompt)]
      
      # Add previous step data as conversation history
      for step in previous_steps:
          if step.generated_text:
              # Determine if this is from the user or AI based on user_id comparison
              # This is a simplification - you might need to adjust based on your data model
              if step.user_id == user.id:
                  messages.append(HumanMessage(content=step.generated_text))
              else:
                  messages.append(AIMessage(content=step.generated_text))
      
      # Add current request
      current_message = f"Please respond as {user.username} for the current step: {state.name}"
      messages.append(HumanMessage(content=current_message))
      
      # Generate response using our simplified memory function
      # Extract a query for memory retrieval from the messages
      query = f"{state.name} {state.description} {current_message}"
      response = call_llm_with_memory(llm_model, messages, user_id, query=query)
      
      logger.info(f"Generated LLM response for state {state.name} with user {user.username}")
      
      # Extract content from response
      if hasattr(response, 'content'):
          return response.content
      return str(response)
      
  except Exception as e:
      logger.error(f"Failed to generate LLM response: {str(e)}")
      return f"Error generating response: {str(e)}" 