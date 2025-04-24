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

from ..models.process import Process as YamlProcess

logger = logging.getLogger(__name__)

def execute_process(process_id: int, initiator_id: int) -> Optional[int]:
  try:
      db = next(get_db())
      
      # 1. Create process instance
      instance_id = ProcessManager._create_process_instance(db, process_id, initiator_id)
      if not instance_id:
          return None
      
      # 2. Get initial node and create first step
      initial_node = ProcessManager._get_initial_node(db, process_id)
      if not initial_node:
          logger.error(f"No initial node found for process: {process_id}")
          return None
      
      # Create the first step
      step_id = ProcessManager._create_process_instance_step(
          db, instance_id, initial_node.id, initiator_id
      )
      
      if not step_id:
          return None
      
      # Update instance with current node
      instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
      instance.current_node_id = initial_node.id
      db.commit()
      
      logger.info(f"Process instance {instance_id} started with initial node {initial_node.id}")
      
      return instance_id
      
  except Exception as e:
      logger.error(f"Failed to execute process: {str(e)}")
      return None