import os
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.process_role import ProcessRole
from agir_db.models.process import Process, ProcessNode, ProcessTransition
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.process_instance_step import ProcessInstanceStep
from agir_db.models.process_role_user import ProcessRoleUser
from agir_db.schemas.process import ProcessNodeDTO

from src.db.create_process_role_user import create_process_role_user
from src.evolution.process_manager.generate_llm_response import generate_llm_response
from src.llms.llm_provider_manager import LLMProviderManager

logger = logging.getLogger(__name__)

def get_next_node(db: Session, process_id: int, current_node_id: int, instance_id: int) -> Optional[ProcessNode]:
  """
  Get the next node in a process based on conditions.
  
  Args:
      db: Database session
      process_id: ID of the process
      current_node_id: ID of the current node
      instance_id: ID of the process instance
      
  Returns:
      Optional[ProcessNode]: Next node if found, None otherwise
  """
  try:
      # Find all transitions from current node
      transitions = db.query(ProcessTransition).filter(
          ProcessTransition.process_id == process_id,
          ProcessTransition.from_node_id == current_node_id
      ).all()
      
      if not transitions:
          logger.info(f"No transitions found from node {current_node_id} - this may be the final node")
          return None
      
      # If only one transition without condition, return the destination node
      if len(transitions) == 1 and not transitions[0].condition:
          next_node = db.query(ProcessNode).filter(ProcessNode.id == transitions[0].to_node_id).first()
          if not next_node:
              logger.error(f"Next node not found: {transitions[0].to_node_id}")
              return None
          return ProcessNodeDTO.model_validate(next_node)
      
      # Get the current node's data
      current_node = db.query(ProcessNode).filter(ProcessNode.id == current_node_id).first()
      if not current_node:
          logger.error(f"Current node not found: {current_node_id}")
          return None
      
      # Find the current step in the process instance
      current_step = db.query(ProcessInstanceStep).filter(
          ProcessInstanceStep.process_instance_id == instance_id,
          ProcessInstanceStep.node_id == current_node_id
      ).first()
      
      if not current_step:
          logger.error(f"Current step not found for instance {instance_id} and node {current_node_id}")
          return None
      
      # Find the previous step to get context
      previous_step = db.query(ProcessInstanceStep).filter(
          ProcessInstanceStep.process_instance_id == instance_id,
          ProcessInstanceStep.created_at < current_step.created_at
      ).order_by(ProcessInstanceStep.created_at.desc()).first()
      
      context = ""
      if previous_step and previous_step.comment:
          context = previous_step.comment
      
      if current_step.comment:
          context += f"\n\nCurrent status: {current_step.comment}"
      
      # Use LLM to evaluate conditions and determine the next node
      selected_transition = None
      if len(transitions) > 1:
          # Prepare prompt for LLM
          conditions = []
          for t in transitions:
              if t.condition:
                  conditions.append(f"- Transition to '{t.to_node.name}' if: {t.condition}")
          
          prompt = f"""
          Based on the following patient information:
          
          {context}
          
          Determine which of the following conditions is true:
          {'\n'.join(conditions)}
          
          Respond with ONLY the name of the destination node that matches the condition.
          """
          
          # Get LLM response
          llm_manager = LLMProviderManager()
          response = llm_manager.generate(prompt, max_tokens=50)
          
          # Find the transition based on LLM response
          for t in transitions:
              if t.to_node and t.to_node.name.lower() in response.lower():
                  selected_transition = t
                  break
      
      # If LLM couldn't determine or there's only one transition with condition
      if not selected_transition and transitions:
          # Default to first transition if we couldn't determine
          selected_transition = transitions[0]
          logger.warning(f"Defaulting to first transition for node {current_node_id} to {selected_transition.to_node_id}")
      
      if not selected_transition:
          logger.error(f"No valid transition found from node {current_node_id}")
          return None
      
      # Get the next node
      next_node = db.query(ProcessNode).filter(ProcessNode.id == selected_transition.to_node_id).first()
      if not next_node:
          logger.error(f"Next node not found: {selected_transition.to_node_id}")
          return None
      
      return ProcessNodeDTO.model_validate(next_node)
      
  except Exception as e:
      logger.error(f"Failed to get next node: {str(e)}")
      return None