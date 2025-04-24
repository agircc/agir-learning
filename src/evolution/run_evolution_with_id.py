import logging

from agir_db.db.session import SessionLocal, get_db

from src.db.create_process_role_user import create_process_role_user
from src.db.data_store import get_learner, get_process, get_process_nodes, get_process_roles
logger = logging.getLogger(__name__)

def run_evolution_with_id(process_id: int) -> bool:
  # Create database session to fetch the process
  with SessionLocal() as db:
      # Get the process data
      process = get_process()
      
      if not process:
          logger.error(f"Process not found: {process_id}")
          return False
      
      # Get process name with fallback
      process_name = process.get("name", f"Process {process_id}") if isinstance(process, dict) else f"Process {process_id}"
      logger.info(f"Running evolution for process: {process_name} (ID: {process_id})")
      
      # Find or create the learner user
      learner = get_learner()
      logger.info(f"Using learner: {learner['username']} (ID: {learner['id']})")
      

      roles_config = get_process_roles()
      logger.info(f"Roles config is a list: {roles_config}")
      # If roles_config is a list of role objects
      for role in roles_config:
          # For list format, each role should be a dictionary with at least 'name' or 'id'
          if isinstance(role, dict):
              role_name = role.get('name') or role.get('id')
              role_data = role
          else:
              # If it's not a dict, try to extract name/id as attribute
              role_name = getattr(role, 'name', None) or getattr(role, 'id', None)
              # Convert object to dict for easier handling
              role_data = vars(role) if hasattr(role, '__dict__') else {'name': role_name}
          
          if not role_name or role_name.lower() == "learner":
              # Skip if no name/id or if it's the learner role
              continue
          
          logger.info(f"Creating user for role: {role_name}")
          username = role_data.get("username", f"{role_name}_{process_id}")
          agent = create_process_role_user(db, role_name, process_id, username, role_data.get("model", None))
          logger.info(f"Created user: {agent.username} (ID: {agent.id})")
      
      
      # Run the evolution process
    #   self._process_evolution(db, process, learner, process_id)
      from src.evolution.execute_process import execute_process
      execute_process(process_id, learner['id'])
      return True