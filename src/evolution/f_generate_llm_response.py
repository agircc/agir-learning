import logging
import sys
import random
import json
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
      
      # Handle prompts array - randomly select one prompt if available
      custom_prompt = None
      if state.prompts:
          # Log prompts type and content for debugging
          logger.info(f"State prompts type: {type(state.prompts)}")
          logger.info(f"State prompts length: {len(state.prompts) if hasattr(state.prompts, '__len__') else 'N/A'}")
          
          # Prompts should be a string list (PostgreSQL text[] type)
          if isinstance(state.prompts, list) and len(state.prompts) > 0:
              # Randomly select a prompt
              custom_prompt = random.choice(state.prompts)
              logger.info(f"Randomly selected prompt from {len(state.prompts)} available prompts")
          else:
              logger.error(f"Invalid prompts format for state {state.name}: {type(state.prompts)}")
              sys.exit(1)
          
          logger.info(f"Using custom prompt for state {state.name}")
      
      # Prepare system prompt
      if custom_prompt:
          system_prompt = custom_prompt
      else:
          system_prompt = f"You are a human working on a scenario called \"{state.name}\". Your role is {user.username}. Task: {state.description}"
      
      # Log the actual prompt being used
      logger.info(f"Using prompt (first 100 chars): {system_prompt[:100]}...")
      
      # Always convert previous steps to LangChain message format and include conversation history
      messages = [SystemMessage(content=system_prompt)]
      
      # Add previous step data as conversation history - always include history
      for step in previous_steps:
          if step.generated_text:
              # Determine if this is from the user or AI based on user_id comparison
              if step.user_id == user.id:
                  messages.append(HumanMessage(content=step.generated_text))
              else:
                  messages.append(AIMessage(content=step.generated_text))
      
      # Add current request only if we're not using a custom prompt
      if not custom_prompt:
          current_message = f"Please respond as {user.username} for the current step: {state.name}"
          messages.append(HumanMessage(content=current_message))
      
      # Generate response using memory function - this ensures user memories are used for personalization
      # The query is used to retrieve relevant memories for the current context
      query = f"{state.name} {state.description}"
      
      # Log the messages being sent to the LLM
      logger.info(f"Sending {len(messages)} messages to LLM:")
      for i, msg in enumerate(messages):
          logger.info(f"Message {i+1} type: {type(msg).__name__}, content: {msg.content[:50]}...")
      
      # call_llm_with_memory automatically includes user memories for personalization
      # by retrieving relevant memories based on the query and including them in the context
      response = call_llm_with_memory(llm_model, messages, user_id, query=query)
      
      logger.info(f"Generated LLM response for state {state.name} with user {user.username}")
      
      # Extract content from response
      if hasattr(response, 'content'):
          return response.content
      return str(response)
      
  except Exception as e:
      logger.error(f"Failed to generate LLM response: {str(e)}")
      sys.exit(1) 