"""
Process Manager - handles creation and execution of processes
"""

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


class ProcessManager:
    """
    Manages the creation and execution of processes.
    """        
    
    
    
    
    @staticmethod
    def _get_initial_node(db: Session, process_id: int) -> Optional[ProcessNode]:
        """
        Get the initial node of a process.
        
        Args:
            db: Database session
            process_id: ID of the process
            
        Returns:
            Optional[ProcessNode]: Initial node if found, None otherwise
        """
        try:
            # Get all nodes in the process
            all_nodes = db.query(ProcessNode).filter(ProcessNode.process_id == process_id).all()
            if not all_nodes:
                logger.error(f"No nodes found for process: {process_id}")
                return None
            
            # Get all 'to' nodes in transitions
            to_nodes = db.query(ProcessTransition.to_node_id).filter(
                ProcessTransition.process_id == process_id
            ).all()
            to_node_ids = {t[0] for t in to_nodes}
            
            # Find nodes that are not 'to' nodes in any transition
            # These are potential starting nodes
            for node in all_nodes:
                if node.id not in to_node_ids:
                    return node
            
            # If no clear starting node, return the first node
            logger.warning(f"No clear starting node found for process: {process_id}, using first node")
            return all_nodes[0]
            
        except Exception as e:
            logger.error(f"Failed to get initial node: {str(e)}")
            return None
    
    @staticmethod
    def _create_process_instance_step(
        db: Session, 
        instance_id: int, 
        node_id: int, 
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Create a process instance step.
        
        Args:
            db: Database session
            instance_id: ID of the process instance
            node_id: ID of the process node
            user_id: ID of the user (optional)
            
        Returns:
            Optional[int]: ID of the process instance step if successful, None otherwise
        """
        try:
            step = ProcessInstanceStep(
                instance_id=instance_id,
                node_id=node_id,
                user_id=user_id,
                action="process"  # Default action
            )
            
            db.add(step)
            db.commit()
            logger.info(f"Created process instance step with ID: {step.id}")
            
            return step.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create process instance step: {str(e)}")
            return None
    
    @staticmethod
    def advance_process(instance_id: int, next_node_name: Optional[str] = None) -> Optional[int]:
        """
        Advance a process instance to the next node.
        
        Args:
            instance_id: ID of the process instance
            next_node_name: Name of the next node (optional)
            
        Returns:
            Optional[int]: ID of the new process instance step if successful, None otherwise
        """
        try:
            db = next(get_db())
            
            # Get process instance
            instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
            if not instance:
                logger.error(f"Process instance not found: {instance_id}")
                return None
            
            # Get current node
            current_node_id = instance.current_node_id
            if not current_node_id:
                logger.error(f"Current node not set for process instance: {instance_id}")
                return None
            
            # Find next node
            next_node_id = None
            
            if next_node_name:
                # If next node name is specified, find it by name
                next_node = db.query(ProcessNode).filter(
                    ProcessNode.process_id == instance.process_id,
                    ProcessNode.name == next_node_name
                ).first()
                
                if next_node:
                    next_node_id = next_node.id
            
            if not next_node_id:
                # Find next node from transitions
                transition = db.query(ProcessTransition).filter(
                    ProcessTransition.process_id == instance.process_id,
                    ProcessTransition.from_node_id == current_node_id
                ).first()
                
                if transition:
                    next_node_id = transition.to_node_id
            
            if not next_node_id:
                logger.error(f"No next node found for process instance: {instance_id}")
                return None
            
            # Create step for next node
            step_id = ProcessManager._create_process_instance_step(
                db, instance_id, next_node_id, instance.initiator_id
            )
            
            if not step_id:
                return None
            
            # Update instance with current node
            instance.current_node_id = next_node_id
            db.commit()
            
            logger.info(f"Advanced process instance {instance_id} to node {next_node_id}")
            
            return step_id
            
        except Exception as e:
            logger.error(f"Failed to advance process: {str(e)}")
            return None
    
    @staticmethod
    def complete_process(instance_id: int, success: bool = True) -> bool:
        """
        Complete a process instance.
        
        Args:
            instance_id: ID of the process instance
            success: Whether the process completed successfully
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = next(get_db())
            
            # Get process instance
            instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
            if not instance:
                logger.error(f"Process instance not found: {instance_id}")
                return False
            
            # Update status - check available enum values
            if success:
                instance.status = ProcessInstanceStatus.COMPLETED
            else:
                # Try to use FAILED, TERMINATED, or CANCELLED, depending on what's available
                # We do this to be compatible with different versions of agir_db
                if hasattr(ProcessInstanceStatus, 'FAILED'):
                    instance.status = ProcessInstanceStatus.FAILED
                elif hasattr(ProcessInstanceStatus, 'TERMINATED'):
                    instance.status = ProcessInstanceStatus.TERMINATED
                elif hasattr(ProcessInstanceStatus, 'CANCELLED'):
                    instance.status = ProcessInstanceStatus.CANCELLED
                else:
                    # If none of these are available, fall back to a string value
                    instance.status = 'failed'
                    logger.warning("ProcessInstanceStatus enum doesn't have FAILED/TERMINATED/CANCELLED; using string value 'failed'")
            
            db.commit()
            logger.info(f"Completed process instance {instance_id} with status: {instance.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete process: {str(e)}")
            return False
    
    @staticmethod
    def get_process(process_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a process by ID from the database.
        
        Args:
            process_id: ID of the process
            
        Returns:
            Process data as a dictionary if found, None otherwise
        """
        try:
            db = next(get_db())
            
            # Get the process from the database
            process = db.query(Process).filter(Process.id == process_id).first()
            
            if not process:
                logger.error(f"Process not found with ID: {process_id}")
                return None
                
            # Get process instance for config
            process_instance = db.query(ProcessInstance).filter(
                ProcessInstance.process_id == process_id
            ).order_by(ProcessInstance.created_at.desc()).first()
                
            # Create a dictionary with process data
            process_data = {
                "id": process.id,
                "name": process.name,
                "description": process.description,
                "config": process_instance.config if process_instance else None
            }
            
            # Add yaml-compatible attributes for compatibility with evolution engine
            process_data["learner"] = {}
            process_data["roles"] = []
            process_data["nodes"] = []
            process_data["transitions"] = []
            process_data["evolution"] = {}
            
            # If we have config, parse and add it
            if process_data["config"]:
                try:
                    if isinstance(process_data["config"], str):
                        config = json.loads(process_data["config"])
                    else:
                        config = process_data["config"]
                        
                    # Add config details to the process data
                    if "learner" in config:
                        process_data["learner"] = config["learner"]
                    if "roles" in config:
                        process_data["roles"] = config["roles"]
                    if "nodes" in config:
                        process_data["nodes"] = config["nodes"]
                    if "transitions" in config:
                        process_data["transitions"] = config["transitions"]
                    if "evolution" in config:
                        process_data["evolution"] = config["evolution"]
                except Exception as e:
                    logger.error(f"Failed to parse process config: {str(e)}")
            
            return process_data
            
        except Exception as e:
            logger.error(f"Error getting process {process_id}: {str(e)}")
            return None 