import os
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.scenario import Scenario
from agir_db.models.state import State
from agir_db.models.state_transition import StateTransition
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step
from agir_db.models.agent_assignment import AgentAssignment
from agir_db.schemas.state import StateInDBBase

from src.llm.llm_provider import get_llm_model


logger = logging.getLogger(__name__)

def j_get_next_state(db: Session, scenario_id: int, current_state_id: int, episode_id: int, user: User) -> Optional[State]:
  """
  Get the next state in a scenario based on conditions.
  
  Args:
      db: Database session (existing session, don't close it)
      scenario_id: ID of the scenario
      current_state_id: ID of the current state
      episode_id: ID of the episode
      user: User object for LLM model selection
      
  Returns:
      Optional[State]: Next state if found, None otherwise
  """
  try:
      # Find all transitions from current state
      transitions = db.query(StateTransition).filter(
          StateTransition.scenario_id == scenario_id,
          StateTransition.from_state_id == current_state_id
      ).all()
      
      if not transitions:
          logger.info(f"No transitions found from state {current_state_id} in scenario {scenario_id} - this may be the final state")
          return None
      
      # If only one transition without condition, return the destination state
      if len(transitions) == 1 and not transitions[0].condition:
          next_state = db.query(State).filter(State.id == transitions[0].to_state_id).first()
          if not next_state:
              logger.error(f"Next state with ID {transitions[0].to_state_id} not found in database")
              return None
          try:
              return StateInDBBase.model_validate(next_state)
          except Exception as validation_error:
              logger.error(f"Failed to validate state model: {str(validation_error)}")
              # Fallback to returning the raw state if validation fails
              logger.warning(f"Returning raw state as fallback for state ID: {next_state.id}")
              return next_state
      
      # Get the current state's data
      current_state = db.query(State).filter(State.id == current_state_id).first()
      if not current_state:
          logger.error(f"Current state not found: {current_state_id}")
          return None
      
      # Find the current step in the episode
      current_step = db.query(Step).filter(
          Step.episode_id == episode_id,
          Step.state_id == current_state_id
      ).first()
      
      if not current_step:
          logger.error(f"Current step not found for episode {episode_id} and state {current_state_id}")
          return None
      
      # Find the previous step to get context
      previous_step = db.query(Step).filter(
          Step.episode_id == episode_id,
          Step.created_at < current_step.created_at
      ).order_by(Step.created_at.desc()).first()
      
      context = ""
      if previous_step and previous_step.generated_text:
          context = previous_step.generated_text
      
      if current_step.generated_text:
          context += f"\n\nCurrent status: {current_step.generated_text}"
      
      # Use LLM to evaluate conditions and determine the next state
      selected_transition = None
      if len(transitions) > 1:
          # Prepare prompt for LLM
          conditions = []
          for t in transitions:
              if t.condition:
                  conditions.append(f"- Transition to '{t.to_state.name}' if: {t.condition}")
          
          prompt = f"""
          Based on the following patient information:
          
          {context}
          
          Determine which of the following conditions is true:
          {'\n'.join(conditions)}
          
          Respond with ONLY the name of the destination state that matches the condition.
          """
          
          # Get LLM response
          logger.info(f"User LLM model: {user}")
          llm_model = get_llm_model(user.llm_model)
          response = llm_model.invoke(prompt)
          
          # Extract content from response
          if hasattr(response, 'content'):
              response_text = response.content
          else:
              response_text = str(response)
          
          # Find the transition based on LLM response
          for t in transitions:
              if t.to_state and t.to_state.name.lower() in response_text.lower():
                  selected_transition = t
                  break
      
      # If LLM couldn't determine or there's only one transition with condition
      if not selected_transition and transitions:
          # Default to first transition if we couldn't determine
          selected_transition = transitions[0]
          logger.warning(f"Defaulting to first transition for state {current_state_id} to {selected_transition.to_state_id}")
      
      if not selected_transition:
          logger.error(f"No valid transition found from state {current_state_id}")
          return None
      
      # Get the next state
      next_state = db.query(State).filter(State.id == selected_transition.to_state_id).first()
      if not next_state:
          logger.error(f"Next state not found: {selected_transition.to_state_id}")
          return None
      
      return StateInDBBase.model_validate(next_state)
      
  except Exception as e:
      logger.error(f"Failed to get next state: {str(e)}")
      return None 