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
from src.llms.llm_provider_manager import LLMProviderManager

from ..models.process import Process as YamlProcess

logger = logging.getLogger(__name__)

class ProcessManager:
    """
    Manages the creation and execution of processes.
    """
    
    @staticmethod
    def _create_process_instance(db: Session, process_id: int, initiator_id: int) -> Optional[int]:
        """
        Create a process instance.
        
        Args:
            db: Database session
            process_id: ID of the process
            initiator_id: ID of the initiator
            
        Returns:
            Optional[int]: ID of the process instance if successful, None otherwise
        """
        try:
            instance = ProcessInstance(
                process_id=process_id,
                initiator_id=initiator_id,
                status=ProcessInstanceStatus.RUNNING
            )
            
            db.add(instance)
            db.commit()
            db.refresh(instance)
            
            logger.info(f"Created process instance with ID: {instance.id}")
            return instance.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create process instance: {str(e)}")
            return None
    
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
                    return ProcessNodeDTO.model_validate(node)
            
            # If no clear starting node, return the first node
            logger.warning(f"No clear starting node found for process: {process_id}, using first node")
            return all_nodes[0]
            
        except Exception as e:
            logger.error(f"Failed to get initial node: {str(e)}")
            return None
    
    @staticmethod
    def _get_node_role(db: Session, node_id: int) -> Optional[ProcessRole]:
        """
        Get the role associated with a node.
        
        Args:
            db: Database session
            node_id: ID of the node
            
        Returns:
            Optional[ProcessRole]: Role if found, None otherwise
        """
        try:
            node = db.query(ProcessNode).filter(ProcessNode.id == node_id).first()
            if not node or not node.role_id:
                logger.error(f"Node not found or has no role: {node_id}")
                return None
            
            role = db.query(ProcessRole).filter(ProcessRole.id == node.role_id).first()
            if not role:
                logger.error(f"Role not found for node: {node_id}")
                return None
            
            return role
            
        except Exception as e:
            logger.error(f"Failed to get node role: {str(e)}")
            return None
    
    @staticmethod
    def _get_or_create_role_user(db: Session, role_id: int, process_instance_id: int) -> Optional[User]:
        """
        Get or create a user for a role in a process instance.
        
        Args:
            db: Database session
            role_id: ID of the role
            process_instance_id: ID of the process instance
            
        Returns:
            Optional[User]: User if found or created, None otherwise
        """
        try:
            # Try to find existing role-user mapping for this process instance
            instance = db.query(ProcessInstance).filter(ProcessInstance.id == process_instance_id).first()
            if not instance:
                logger.error(f"Process instance not found: {process_instance_id}")
                return None
            
            role = db.query(ProcessRole).filter(ProcessRole.id == role_id).first()
            if not role:
                logger.error(f"Role not found: {role_id}")
                return None
            
            # Check if role-user mapping exists
            role_user = db.query(ProcessRoleUser).filter(
                ProcessRoleUser.role_id == role_id
            ).first()
            
            if role_user:
                # User exists for this role
                user = db.query(User).filter(User.id == role_user.user_id).first()
                if user:
                    logger.info(f"Found existing user {user.username} for role {role.name}")
                    return user
            
            # Create a new user for this role
            logger.info(f"Creating new user for role {role.name} in process {instance.process_id}")
            user = create_process_role_user(
                db, 
                role.name, 
                instance.process_id, 
                username=f"{role.name}_{instance.id}",
                model=getattr(role, 'model', None)
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get or create role user: {str(e)}")
            return None
    
    @staticmethod
    def _create_process_instance_step(
        db: Session, 
        instance_id: int, 
        node_id: int, 
        user_id: Optional[int] = None,
        comment: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a process instance step.
        
        Args:
            db: Database session
            instance_id: ID of the process instance
            node_id: ID of the process node
            user_id: ID of the user (optional)
            comment: Comment/data from LLM (optional)
            
        Returns:
            Optional[int]: ID of the process instance step if successful, None otherwise
        """
        try:
            step = ProcessInstanceStep(
                instance_id=instance_id,
                node_id=node_id,
                user_id=user_id,
                action="process",
                comment=comment
            )
            
            db.add(step)
            db.commit()
            db.refresh(step)
            
            logger.info(f"Created process instance step with ID: {step.id}")
            
            return step.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create process instance step: {str(e)}")
            return None
    
    @staticmethod
    def _get_next_node(db: Session, process_id: int, current_node_id: int) -> Optional[ProcessNode]:
        """
        Get the next node in a process.
        
        Args:
            db: Database session
            process_id: ID of the process
            current_node_id: ID of the current node
            
        Returns:
            Optional[ProcessNode]: Next node if found, None otherwise
        """
        try:
            # Find transition from current node
            transition = db.query(ProcessTransition).filter(
                ProcessTransition.process_id == process_id,
                ProcessTransition.from_node_id == current_node_id
            ).first()
            
            if not transition:
                logger.info(f"No transitions found from node {current_node_id} - this may be the final node")
                return None
            
            # Get the next node
            next_node = db.query(ProcessNode).filter(ProcessNode.id == transition.to_node_id).first()
            if not next_node:
                logger.error(f"Next node not found: {transition.to_node_id}")
                return None
            
            return ProcessNodeDTO.model_validate(next_node)
            
        except Exception as e:
            logger.error(f"Failed to get next node: {str(e)}")
            return None
    
    @staticmethod
    def _generate_llm_response(node: ProcessNode, previous_steps: List[ProcessInstanceStep]) -> Optional[str]:
        """
        Generate LLM response for a node.
        
        Args:
            node: Process node
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
            
            # For this simple implementation, we'll just return a placeholder
            # In a real implementation, you would use an actual LLM provider
            return f"Generated response for node {node.name}: {node.description}"
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            return None

def execute_process(process_id: int, initiator_id: int) -> Optional[int]:
    """
    Execute a process from start to finish.
    
    Args:
        process_id: ID of the process
        initiator_id: ID of the initiator
        
    Returns:
        Optional[int]: ID of the process instance if successful, None otherwise
    """
    try:
        db = next(get_db())
        
        # 1. Create process instance
        instance_id = ProcessManager._create_process_instance(db, process_id, initiator_id)
        if not instance_id:
            return None
        
        # 2. Get initial node and create first step
        current_node = ProcessManager._get_initial_node(db, process_id)
        if not current_node:
            logger.error(f"No initial node found for process: {process_id}")
            return None
        
        logger.info(f"Current node: {current_node}")
        # Initialize process instance with current node
        instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
        instance.current_node_id = current_node.id
        db.commit()
        
        # Keep track of all steps
        all_steps = []
        
        # Continue processing nodes until we reach the end
        while current_node:
            # 3. Get role associated with the node
            role = ProcessManager._get_node_role(db, current_node.id)
            if not role:
                logger.error(f"Failed to get role for node: {current_node.id}")
                return None
            
            # 4. Get or create user for this role
            user = ProcessManager._get_or_create_role_user(db, role.id, instance_id)
            if not user:
                logger.error(f"Failed to get or create user for role: {role.id}")
                return None
            
            # 5. Generate LLM response for this node
            response = ProcessManager._generate_llm_response(current_node, all_steps)
            
            # Create step with generated data
            step_id = ProcessManager._create_process_instance_step(
                db, instance_id, current_node.id, user.id, response
            )
            
            if not step_id:
                logger.error(f"Failed to create step for node: {current_node.id}")
                return None
            
            # Add step to history
            step = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == step_id).first()
            all_steps.append(step)
            
            # Update instance with current node
            instance.current_node_id = current_node.id
            db.commit()
            
            logger.info(f"Current node in the circle: {current_node}")
            # 6. Find next node
            next_node = ProcessManager._get_next_node(db, process_id, current_node.id)
            
            # If no next node, we've reached the end
            if not next_node:
                logger.info(f"Process instance {instance_id} completed successfully")
                instance.status = ProcessInstanceStatus.COMPLETED
                db.commit()
                break
            
            # Move to next node
            current_node = next_node
        
        return instance_id
        
    except Exception as e:
        logger.error(f"Failed to execute process: {str(e)}")
        return None