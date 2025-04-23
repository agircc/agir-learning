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

from .models.process import Process as YamlProcess
from .utils.yaml_loader import load_process_from_file

logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Manages the creation and execution of processes.
    """
    
    @staticmethod
    def check_database_tables() -> bool:
        """
        Check if required database tables exist.
        
        Returns:
            bool: True if all required tables exist, False otherwise
        """
        try:
            db = next(get_db())
            
            # Check essential tables by running simple queries
            tables_to_check = [
                (User, "user"),
                (Process, "process"),
                (ProcessNode, "process_node"),
                (ProcessRole, "process_role"),
                (ProcessTransition, "process_transition"),
                (ProcessInstance, "process_instance"),
                (ProcessInstanceStep, "process_instance_step")
            ]
            
            for model, table_name in tables_to_check:
                try:
                    db.query(model).limit(1).all()
                    logger.debug(f"Table {table_name} exists")
                except SQLAlchemyError as e:
                    logger.error(f"Table {table_name} check failed: {str(e)}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Database check failed: {str(e)}")
            return False
    
    @staticmethod
    def create_process_from_yaml(yaml_file_path: str, created_by: Optional[str] = None) -> Optional[int]:
        """
        Create a process from a YAML file.
        
        Args:
            yaml_file_path: Path to the YAML file
            created_by: Username of the creator (optional)
            
        Returns:
            Optional[int]: ID of the created process if successful, None otherwise
        """
        # Check if database tables exist
        if not ProcessManager.check_database_tables():
            logger.error("Database tables check failed. Please run database migrations.")
            return None
        
        # Load process from YAML
        yaml_process = load_process_from_file(yaml_file_path)
        if not yaml_process:
            logger.error(f"Failed to load process from {yaml_file_path}")
            return None
        
        # Create or update database records
        try:
            db = next(get_db())
            
            # 1. Create or find target user
            target_user_id = ProcessManager._create_or_find_target_user(db, yaml_process)
            if not target_user_id:
                return None
            
            # 2. Create or find process
            process_id = ProcessManager._create_or_find_process(db, yaml_process, created_by, target_user_id)
            if not process_id:
                return None
            
            # 3. Create roles
            role_id_mapping = ProcessManager._create_process_roles(db, process_id, yaml_process)
            if not role_id_mapping:
                return None
            
            # 4. Create nodes
            node_id_mapping = ProcessManager._create_process_nodes(db, process_id, yaml_process, role_id_mapping)
            if not node_id_mapping:
                return None
            
            # 5. Create transitions
            if not ProcessManager._create_process_transitions(db, process_id, yaml_process, node_id_mapping):
                return None
            
            return process_id
            
        except Exception as e:
            logger.error(f"Failed to create process: {str(e)}")
            return None
    
    @staticmethod
    def _create_or_find_target_user(db: Session, yaml_process: YamlProcess) -> Optional[int]:
        """
        Create or find target user based on YAML process.
        
        Args:
            db: Database session
            yaml_process: YAML process object
            
        Returns:
            Optional[int]: ID of the target user if successful, None otherwise
        """
        try:
            target_user_data = yaml_process.target_user
            username = target_user_data.get("username")
            
            if not username:
                logger.error("Target user username not specified in process YAML")
                return None
            
            # Check if user exists
            user = db.query(User).filter(User.username == username).first()
            
            if user:
                logger.info(f"Found existing user: {username}")
                # Update model field if it exists in YAML
                if "model" in target_user_data and hasattr(user, "model"):
                    user.model = target_user_data["model"]
                    db.commit()
                    logger.info(f"Updated user model to {target_user_data['model']}")
                return user.id
            
            # Prepare user data
            user_data = {
                "username": username,
                "first_name": target_user_data.get("first_name", ""),
                "last_name": target_user_data.get("last_name", ""),
                "email": target_user_data.get("email", f"{username}@example.com"),
                "is_active": True
            }
            
            # Add model if it exists in YAML
            if "model" in target_user_data:
                user_data["llm_model"] = target_user_data["model"]
            
            # Create new user
            user = User(**user_data)
            
            # Add additional profile data
            profile_data = {}
            for key, value in target_user_data.items():
                if key not in ["username", "first_name", "last_name", "email", "model"]:
                    profile_data[key] = value
            
            if profile_data:
                user.profile = json.dumps(profile_data)
            
            db.add(user)
            db.commit()
            logger.info(f"Created new user: {username} with ID: {user.id}")
            
            return user.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create or find target user: {str(e)}")
            return None
    
    @staticmethod
    def _create_or_find_process(db: Session, yaml_process: YamlProcess, created_by: Optional[str] = None, default_user_id: Optional[int] = None) -> Optional[int]:
        """
        Create or find process based on YAML process.
        
        Args:
            db: Database session
            yaml_process: YAML process object
            created_by: Username of creator (optional)
            default_user_id: User ID to use as default creator if created_by is None
            
        Returns:
            Optional[int]: ID of the process if successful, None otherwise
        """
        try:
            process_name = yaml_process.name
            
            # Check if process exists
            query = db.query(Process).filter(Process.name == process_name)
            if created_by:
                query = query.filter(Process.created_by == created_by)
                
            process = query.first()
            
            if process:
                logger.info(f"Found existing process: {process_name}")
                return process.id
            
            # If created_by is None, use default_user_id or find the first admin user
            creator_id = None
            if created_by:
                # Find user by username
                creator = db.query(User).filter(User.username == created_by).first()
                if creator:
                    creator_id = str(creator.id)
                else:
                    logger.warning(f"User with username {created_by} not found")
            
            # If still no creator_id, use default_user_id
            if not creator_id and default_user_id:
                creator_id = str(default_user_id)
                logger.info(f"Using target user as process creator since created_by was not provided")
            
            # If still no creator_id, find an admin user
            if not creator_id:
                admin_user = db.query(User).filter(User.is_active == True).first()
                if admin_user:
                    creator_id = str(admin_user.id)
                    logger.info(f"Using first active user as process creator: {admin_user.username}")
                else:
                    logger.error("No active users found in database to use as process creator")
                    return None
            
            # Create new process with the determined creator_id
            process = Process(
                name=process_name,
                description=yaml_process.description,
                created_by=creator_id
            )
            
            db.add(process)
            db.commit()
            logger.info(f"Created new process: {process_name} with ID: {process.id}, creator ID: {creator_id}")
            
            return process.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create or find process: {str(e)}")
            return None
    
    @staticmethod
    def _create_process_roles(db: Session, process_id: int, yaml_process: YamlProcess) -> Optional[Dict[str, int]]:
        """
        Create roles for a process based on YAML process.
        
        Args:
            db: Database session
            process_id: ID of the process
            yaml_process: YAML process object
            
        Returns:
            Optional[Dict[str, int]]: Mapping of role names to IDs if successful, None otherwise
        """
        try:
            roles = yaml_process.roles
            if not roles:
                logger.warning("No roles defined in process YAML")
                return {}
            
            # Create role ID mapping
            role_id_mapping = {}
            
            # Process each role
            for role_data in roles:
                role_name = None
                role_description = None
                model = None
                
                # Handle both formats (dict and Role object)
                if isinstance(role_data, dict):
                    role_name = role_data.get("name") or role_data.get("id")
                    role_description = role_data.get("description", "")
                    model = role_data.get("model", "")  # Get model from role data
                else:
                    role_name = role_data.name or role_data.id
                    role_description = role_data.description
                    # Try to get model from role object attributes
                    model = getattr(role_data, "model", "") if hasattr(role_data, "model") else ""
                
                if not role_name:
                    logger.error("Role name not specified in YAML")
                    continue
                
                # Check if role exists
                role = db.query(ProcessRole).filter(
                    ProcessRole.process_id == process_id,
                    ProcessRole.name == role_name
                ).first()
                
                if role:
                    logger.info(f"Found existing role: {role_name}")
                    # Update model if it's provided
                    if model and hasattr(role, "model"):
                        role.model = model
                        db.commit()
                        logger.info(f"Updated role model to {model}")
                else:
                    # Create role data
                    role_data = {
                        "process_id": process_id,
                        "name": role_name,
                        "description": role_description
                    }
                    
                    # Add model if it exists
                    if model:
                        role_data["model"] = model
                    
                    # Create role
                    role = ProcessRole(**role_data)
                    db.add(role)
                    db.commit()
                    logger.info(f"Created new role: {role_name} with ID: {role.id}")
                
                # Add to mapping
                role_id_mapping[role_name] = role.id
            
            return role_id_mapping
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create roles: {str(e)}")
            return None
    
    @staticmethod
    def _create_process_nodes(
        db: Session, 
        process_id: int, 
        yaml_process: YamlProcess,
        role_id_mapping: Dict[str, int]
    ) -> Optional[Dict[str, int]]:
        """
        Create process nodes from YAML process.
        
        Args:
            db: Database session
            process_id: ID of the process
            yaml_process: YAML process object
            role_id_mapping: Mapping of YAML role IDs to database role IDs
            
        Returns:
            Optional[Dict[str, int]]: Mapping of YAML node names to database node IDs if successful, None otherwise
        """
        try:
            node_id_mapping = {}
            
            for i, node in enumerate(yaml_process.nodes):
                # Get the role ID from the mapping
                role_id = role_id_mapping.get(node.role)
                if not role_id:
                    logger.warning(f"Role not found for node: {node.name}, role: {node.role}")
                    continue
                
                db_node = ProcessNode(
                    process_id=process_id,
                    name=node.name,
                    description=node.description,
                    role_id=role_id,
                    node_type="STANDARD"  # Default node type
                )
                
                db.add(db_node)
                db.flush()  # Get the ID without committing
                
                # In the YAML file, nodes don't have explicit IDs, so use the name as key
                node_id_mapping[node.name] = db_node.id
            
            db.commit()
            logger.info(f"Created {len(node_id_mapping)} process nodes")
            
            return node_id_mapping
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create process nodes: {str(e)}")
            return None
    
    @staticmethod
    def _create_process_transitions(
        db: Session, 
        process_id: int, 
        yaml_process: YamlProcess,
        node_id_mapping: Dict[str, int]
    ) -> bool:
        """
        Create process transitions from YAML process.
        
        Args:
            db: Database session
            process_id: ID of the process
            yaml_process: YAML process object
            node_id_mapping: Mapping of YAML node names to database node IDs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for transition in yaml_process.transitions:
                from_node_id = node_id_mapping.get(transition.from_node)
                to_node_id = node_id_mapping.get(transition.to_node)
                
                if not from_node_id or not to_node_id:
                    logger.warning(f"Node not found for transition: {transition.from_node} -> {transition.to_node}")
                    continue
                
                db_transition = ProcessTransition(
                    process_id=process_id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id
                )
                
                db.add(db_transition)
            
            db.commit()
            logger.info(f"Created process transitions")
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create process transitions: {str(e)}")
            return False
    
    @staticmethod
    def execute_process(process_id: int, initiator_id: int) -> Optional[int]:
        """
        Execute a process.
        
        Args:
            process_id: ID of the process
            initiator_id: ID of the initiator (target user)
            
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
    
    @staticmethod
    def _create_process_instance(db: Session, process_id: int, initiator_id: int) -> Optional[int]:
        """
        Create a process instance.
        
        Args:
            db: Database session
            process_id: ID of the process
            initiator_id: ID of the initiator (target user)
            
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