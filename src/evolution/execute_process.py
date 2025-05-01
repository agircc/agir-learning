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
from agir_db.models.process import Process, ProcessNode, ProcessTransition, ProcessNodeRole
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.process_instance_step import ProcessInstanceStep
from agir_db.models.process_role_user import ProcessRoleUser
from agir_db.models.chat_message import ChatMessage
from agir_db.schemas.process import ProcessNodeInDBBase

from src.construction.create_process_role_user import create_process_role_user
from src.evolution.coversation.conduct_multi_turn_conversation import conduct_multi_turn_conversation
from src.evolution.coversation.create_conversation import create_conversation
from src.evolution.process_manager.generate_llm_response import generate_llm_response
from src.evolution.process_manager.get_next_node import get_next_node
from src.llms.llm_provider_manager import LLMProviderManager

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
                    return ProcessNodeInDBBase.model_validate(node)
            
            # If no clear starting node, return the first node
            logger.warning(f"No clear starting node found for process: {process_id}, using first node")
            return all_nodes[0]
            
        except Exception as e:
            logger.error(f"Failed to get initial node: {str(e)}")
            return None
    
    @staticmethod
    def _get_node_roles(db: Session, node_id: int) -> List[ProcessRole]:
        """
        Get all roles associated with a node.
        
        Args:
            db: Database session
            node_id: ID of the node
            
        Returns:
            List[ProcessRole]: Roles associated with the node
        """
        try:
            # Get all role IDs for this node from the ProcessNodeRole table
            node_roles = db.query(ProcessNodeRole).filter(
                ProcessNodeRole.process_node_id == node_id
            ).all()
            
            if not node_roles:
                logger.error(f"No roles found for node: {node_id}")
                return []
            
            # Get the actual ProcessRole objects
            roles = []
            for node_role in node_roles:
                role = db.query(ProcessRole).filter(
                    ProcessRole.id == node_role.process_role_id
                ).first()
                
                if role:
                    roles.append(role)
            
            return roles
            
        except Exception as e:
            logger.error(f"Failed to get node roles: {str(e)}")
            return []
    
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
        generated_text: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a process instance step.
        
        Args:
            db: Database session
            instance_id: ID of the process instance
            node_id: ID of the process node
            user_id: ID of the user (optional)
            generated_text: Comment/data from LLM (optional)
            
        Returns:
            Optional[int]: ID of the process instance step if successful, None otherwise
        """
        try:
            step = ProcessInstanceStep(
                instance_id=instance_id,
                node_id=node_id,
                user_id=user_id,
                action="process",
                generated_text=generated_text
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
        logger.info(f"Step 0")
        db = next(get_db())
        logger.info(f"Step 1")
        # 1. Create process instance
        instance_id = ProcessManager._create_process_instance(db, process_id, initiator_id)
        if not instance_id:
            return None
        
        logger.info(f"Step 2")
        # 2. Get initial node and create first step
        current_node = ProcessManager._get_initial_node(db, process_id)
        if not current_node:
            logger.error(f"No initial node found for process: {process_id}")
            return None
        
        logger.info(f"Current node: {current_node}")


        logger.info(f"Step 3")
        # Initialize process instance with current node
        instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
        instance.current_node_id = current_node.id
        db.commit()
        
        # Keep track of all steps
        all_steps = []
        
        # Continue processing nodes until we reach the end
        while current_node:
            # 3. Get all roles associated with the node
            roles = ProcessManager._get_node_roles(db, current_node.id)
            if not roles:
                logger.error(f"Failed to get roles for node: {current_node.id}")
                return None
            
            # 4. Get or create users for each role
            role_users = []
            for role in roles:
                user = ProcessManager._get_or_create_role_user(db, role.id, instance_id)
                if not user:
                    logger.error(f"Failed to get or create user for role: {role.id}")
                    return None
                role_users.append((role, user))
            
            # 5. If there's only one role, generate a simple response
            if len(role_users) == 1:
                role, user = role_users[0]
                response = generate_llm_response(db, current_node, role, user, all_steps)
                
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
            
            # 6. If there are multiple roles, conduct a multi-turn conversation
            else:
                # Create conversation
                conversation = create_conversation(db, current_node, instance_id, role_users)
                if not conversation:
                    logger.error(f"Failed to create conversation for node: {current_node.id}")
                    return None
                
                # Conduct multi-turn conversation
                conversation_result = conduct_multi_turn_conversation(
                    db, conversation, current_node, role_users
                )
                
                # Create a step for each role to record their participation
                for role, user in role_users:
                    step_id = ProcessManager._create_process_instance_step(
                        db, instance_id, current_node.id, user.id, 
                        f"Participated in conversation for node: {current_node.name}"
                    )
                    
                    if not step_id:
                        logger.error(f"Failed to create step for node: {current_node.id} and user: {user.id}")
                        continue
                    
                    # Add step to history
                    step = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == step_id).first()
                    all_steps.append(step)
                
                # Create a final step with the conversation result
                step_id = ProcessManager._create_process_instance_step(
                    db, instance_id, current_node.id, role_users[0][1].id, conversation_result
                )
                
                if not step_id:
                    logger.error(f"Failed to create final step for node: {current_node.id}")
                    return None
                
                # Add final step to history
                step = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == step_id).first()
                all_steps.append(step)
            
            # Update instance with current node
            instance.current_node_id = current_node.id
            db.commit()
            
            logger.info(f"Current node in the circle: {current_node}")
            # 7. Find next node
            next_node = get_next_node(db, process_id, current_node.id, instance_id, role_users[0][1])
            
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