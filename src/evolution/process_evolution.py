import logging
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple

from agir_db.db.session import SessionLocal, get_db
from agir_db.models.process import Process

from src.db.create_process_role_user import create_process_role_user
from src.db.data_store import get_learner, get_process, get_process_nodes, get_process_roles
logger = logging.getLogger(__name__)

def process_evolution(
  db: Session, 
  process: Process, 
  learner: Any,
  process_id: Any = None
) -> None:
  """
  Process the evolution part of the process.
  
  Args:
      db: Database session
      process: Process instance
      learner: The learner user that is evolving through this process
      history: Conversation history
      process_id: ID of the process in the database
      
  Raises:
      ValueError: If learner has no model specified
  """
  history = []
  # Check if process is a dictionary (from get_process) or a Process object
  is_dict = isinstance(process, dict)
  
  # Access evolution based on the object type
  evolution = process["evolution"] if is_dict else process.evolution
  if not evolution:
      logger.info("No evolution defined for process")
      return
      
  # Get process name based on object type
  process_name = process["name"] if is_dict else process.name
  logger.info(f"Processing evolution for process: {process_name}")
  
  # Get or create agent for learner user
  agent = 
          
  # Safely access learner data
  if is_dict:
      learner_data = process["learner"]
      evolution_objective = learner_data.get('evolution_objective', 'Improve your skills and knowledge.')
  else:
      learner_data = process.learner
      evolution_objective = learner_data.get('evolution_objective', 'Improve your skills and knowledge.')
          
  # Generate evolution prompt
  prompt = f"""
  # Evolution Process for {learner.first_name} {learner.last_name}

  You are part of an evolution process called "{process_name}".
  Your objective: {evolution_objective}

  ## Conversation History:
  {json.dumps(history, indent=2)}

  ## Your task:
  1. Review the conversation history.
  2. Identify strengths and weaknesses.
  3. Generate insights and recommendations for improvement.
  4. Create action items for future iterations.
  """
  
  # Check if learner has a model specified
  if not hasattr(learner, 'llm_model') or not learner.llm_model:
      raise ValueError(f"Learner user '{learner.username}' has no model specified")
  
  # Get the appropriate LLM provider using learner's model
  logger.info(f"Using learner's model '{learner.llm_model}' for evolution")
  llm_provider = self.llm_provider_manager.get_provider(learner.llm_model)
  
  # Generate evolution response
  try:
      evolution_result = llm_provider.generate(
          prompt=prompt,
          system_prompt=f"You are an evolution agent for {learner.first_name} {learner.last_name}.",
          temperature=0.7,
          max_tokens=2000
      )
      
      # Update agent with evolution results
      agent.status = "evolved"
      agent.description = evolution_result[:500]  # Truncate to fit in DB column
      agent.updated = True
      db.commit()
      
      logger.info("Evolution process completed successfully")
      
  except Exception as e:
      logger.error(f"Error in evolution process: {str(e)}")
      db.rollback()
      raise ValueError(f"Failed to generate evolution response: {str(e)}")
  
  # Store as a custom field for the user
  # Get process ID based on object type 
  process_id_value = process["id"] if is_dict else process.id
  evolution_field_name = f"evolution_{process_id_value}"
  
  # Check if we already have an evolution field for this process
  existing_field = db.query(CustomField).filter(
      CustomField.user_id == learner.id,
      CustomField.field_name == evolution_field_name
  ).first()
  
  if existing_field:
      # Update existing field
      existing_field.field_value = evolution_result
  else:
      # Create new field
      try:
          # Add debug logs
          logger.info(f"Creating CustomField with: user_id={learner.id}, field_name={evolution_field_name}, field_value={evolution_result[:20]}...")
          # Create new CustomField
          evolution_field = CustomField(
              user_id=learner.id,
              field_name=evolution_field_name,
              field_value=evolution_result
          )
          db.add(evolution_field)
      except Exception as e:
          logger.error(f"Failed to create CustomField: {str(e)}")
          # Add detailed error logs
          import traceback
          logger.error(f"Traceback: {traceback.format_exc()}")
          raise ValueError(f"Failed to create custom field for evolution result: {str(e)}")
      
  db.commit()