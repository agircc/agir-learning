"""
Evolution module - handles the main evolution process
"""

import os
import logging
import json
import uuid
from uuid import UUID
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from agir_db.db.session import SessionLocal, get_db
from agir_db.models.user import User
from agir_db.models.process import Process as DBProcess, ProcessNode as DBProcessNode
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.custom_field import CustomField  # 明确从agir_db包导入CustomField
from .models.process import Process, ProcessNode
from .models.agent import Agent
from .llms import BaseLLMProvider, OpenAIProvider, AnthropicProvider
from .utils.database import get_or_create_user, create_or_update_agent, find_agent_by_role, create_process_record
from .utils.yaml_loader import load_process_from_file
from .process_manager import ProcessManager  # Import the new ProcessManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()



class EvolutionEngine:
    """
    Main engine for running the evolution process.
    """
    
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None, llm_provider_manager = None):
        """
        Initialize the evolution engine.
        
        Args:
            llm_provider: Optional LLM provider, defaults to OpenAI if not provided
            llm_provider_manager: Optional LLM provider manager for managing multiple providers
        """
        if llm_provider_manager:
            self.llm_provider_manager = llm_provider_manager
            self.llm_provider = llm_provider_manager.default_provider
        else:
            self.llm_provider = llm_provider or self._create_default_provider()
            self.llm_provider_manager = None
        
    def _create_default_provider(self) -> BaseLLMProvider:
        """
        Create a default LLM provider based on available API keys.
        
        Returns:
            LLM provider instance
        """
        # Try OpenAI first
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            return OpenAIProvider(model_name="gpt-4")
            
        # Try Anthropic next
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            return AnthropicProvider()
            
        # Fallback to an error if neither is available
        raise ValueError(
            "No API keys found for LLM providers. "
            "Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables."
        )
        
    def _get_provider_for_node(self, db: Session, node: ProcessNode, default_provider: BaseLLMProvider) -> BaseLLMProvider:
        """
        Get the appropriate LLM provider for a node based on its role's model.
        
        Args:
            db: Database session
            node: Process node
            default_provider: Default provider to use if no specific model is found
            
        Returns:
            LLM provider instance
        """
        if not self.llm_provider_manager:
            return default_provider
            
        # Get the role for this node
        if not node.role:
            return default_provider
            
        # Special handling for learner role
        if node.role == "learner":
            # Get the learner user
            if hasattr(node, 'assigned_to') and node.assigned_to:
                user = db.query(User).filter(User.username == node.assigned_to).first()
                if user and hasattr(user, 'llm_model') and user.llm_model:
                    logger.info(f"Using learner's model '{user.llm_model}' for node: {node.name}")
                    return self.llm_provider_manager.get_provider(user.llm_model)
            
            # If no user found or no model specified, try to find a default learner
            user = db.query(User).filter(User.is_active == True).first()
            if user and hasattr(user, 'llm_model') and user.llm_model:
                logger.info(f"Using active user's model '{user.llm_model}' for learner node: {node.name}")
                return self.llm_provider_manager.get_provider(user.llm_model)
                
            return default_provider
            
        # Query the database to get the role's model
        from agir_db.models.process_role import ProcessRole
        role = db.query(ProcessRole).filter(ProcessRole.id == node.role).first()
        
        if not role or not hasattr(role, 'model') or not role.model:
            # If role has no model specified, try to get the model from assigned_to user if available
            if hasattr(node, 'assigned_to') and node.assigned_to:
                user = db.query(User).filter(User.username == node.assigned_to).first()
                if user and hasattr(user, 'llm_model') and user.llm_model:
                    return self.llm_provider_manager.get_provider(user.llm_model)
            return default_provider
            
        # Use the model specified for the role
        return self.llm_provider_manager.get_provider(role.model)
        
    def run_evolution_from_file(self, file_path: str) -> bool:
        """
        Run the evolution process from a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            True if successful, False otherwise
        """
        process = load_process_from_file(file_path)
        if not process:
            logger.error(f"Failed to load process from {file_path}")
            return False
            
        return self.run_evolution(process)
        
    def run_evolution_with_id(self, process_id: int) -> bool:
        """
        Run the evolution process using a process ID from the database.
        
        Args:
            process_id: ID of the process in the database
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting evolution process with ID: {process_id}")
        
        # Create database session
        with SessionLocal() as db:
            try:
                # Get process from database
                db_process = db.query(DBProcess).filter(DBProcess.id == process_id).first()
                if not db_process:
                    logger.error(f"Process with ID {process_id} not found in database")
                    return False
                
                logger.info(f"Found process: {db_process.name}")
                
                # Find the target user (initiator)
                learner = None
                
                # Try to find a user who would be appropriate for this process
                # This could be improved to check for users with specific roles/permissions
                user = db.query(User).filter(User.is_active == True).first()
                if not user:
                    logger.error("No active users found in the database")
                    return False
                
                learner = user
                logger.info(f"Using user {learner.username} as target user")
                
                # Execute the process using ProcessManager
                instance_id = ProcessManager.execute_process(process_id, learner.id)
                if not instance_id:
                    logger.error("Failed to execute process")
                    return False
                
                logger.info(f"Created process instance with ID: {instance_id}")
                
                # Get the process instance
                process_instance = db.query(ProcessInstance).filter(
                    ProcessInstance.id == instance_id
                ).first()
                
                if not process_instance:
                    logger.error(f"Process instance with ID {instance_id} not found")
                    return False
                
                # Get the current node
                current_node_id = process_instance.current_node_id
                if not current_node_id:
                    logger.error("Process instance has no current node")
                    return False
                
                current_db_node = db.query(DBProcessNode).filter(
                    DBProcessNode.id == current_node_id
                ).first()
                
                if not current_db_node:
                    logger.error(f"Node with ID {current_node_id} not found")
                    return False
                
                # Fetch all roles from the database
                from agir_db.models.process_role import ProcessRole
                roles = []
                db_roles = db.query(ProcessRole).filter(ProcessRole.process_id == process_id).all()
                
                for db_role in db_roles:
                    from .models.role import Role
                    roles.append(Role(
                        id=str(db_role.id),
                        name=db_role.name,
                        description=db_role.description,
                        system_prompt_template=""
                    ))
                
                # Convert DB node to model node for processing
                current_node = ProcessNode(
                    id=str(current_db_node.id),
                    name=current_db_node.name,
                    role=str(current_db_node.role.id) if current_db_node.role else "unknown",
                    description=current_db_node.description
                )
                
                # Process nodes sequentially, advancing through the process
                history = []  # Conversation history
                
                # Create a simple process object for compatibility with existing code
                process = Process(
                    id=str(db_process.id),
                    name=db_process.name,
                    description=db_process.description,
                    nodes=[current_node],  # Start with just the current node
                    transitions=[],  # We'll use ProcessManager for transitions
                    roles=roles  # Use the roles we fetched from the database
                )
                
                # Process the current node
                while current_node:
                    result = self._process_node(db, process, current_node, learner, history, process_id)
                    if not result:
                        logger.error(f"Failed to process node: {current_node.name}")
                        # Mark process as failed
                        ProcessManager.complete_process(instance_id, success=False)
                        return False
                    
                    processed_node, response, next_node = result
                    
                    # Advance the process to the next node using ProcessManager
                    if next_node:
                        step_id = ProcessManager.advance_process(instance_id, next_node.name)
                        if not step_id:
                            logger.error(f"Failed to advance process to node: {next_node.name}")
                            ProcessManager.complete_process(instance_id, success=False)
                            return False
                        
                        # Update current node
                        current_node = next_node
                    else:
                        # No next node, process is complete
                        logger.info("Process complete, no more nodes to process")
                        ProcessManager.complete_process(instance_id, success=True)
                        current_node = None
                
                # Process evolution
                self._process_evolution(db, process, learner, history, process_id)
                
                return True
                
            except Exception as e:
                logger.error(f"Error running evolution process: {str(e)}")
                return False
        
    def run_evolution(self, process: Process) -> bool:
        """
        Run the evolution process.
        
        Args:
            process: Process instance
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting evolution process: {process.name}")
        
        # Create database session
        with SessionLocal() as db:
            try:
                # Get or create target user first
                learnername = process.learner.get("username")
                if not learnername:
                    logger.error("Target user username not specified in process")
                    return False
                
                learner, created = get_or_create_user(db, learnername, process.learner)
                if created:
                    logger.info(f"Created new target user: {learnername}")
                else:
                    logger.info(f"Using existing target user: {learnername}")
                
                # 保存process实例到数据库，使用learner.id作为created_by
                db_process = create_process_record(db, {
                    "name": process.name,
                    "description": process.description,
                    "created_by": str(learner.id)  # Use learner.id as the creator
                })
                logger.info(f"Created process record in database with ID: {db_process.id}")
                
                # 保存配置作为自定义字段到数据库
                try:
                    # 将配置保存到process_instance表
                    from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
                    
                    # Now create the process instance with learner.id
                    process_instance = ProcessInstance(
                        process_id=db_process.id,
                        initiator_id=learner.id,  # Now we have learner.id
                        status=ProcessInstanceStatus.RUNNING,
                        config=json.dumps(process.to_dict())
                    )
                    db.add(process_instance)
                    db.commit()
                    logger.info(f"Saved process instance to database")
                    process_instance_id = process_instance.id
                    
                    # Create ProcessNode records in the database for each node in the process
                    from agir_db.models.process import ProcessNode as DBProcessNode, ProcessRole
                    
                    # Dictionary to store mapping from YAML node IDs to database node IDs
                    node_id_mapping = {}
                    
                    # First, create role records
                    role_id_mapping = {}
                    for role in process.roles:
                        db_role = ProcessRole(
                            process_id=db_process.id,
                            name=role.name,
                            description=role.description,
                            model=role.model
                        )
                        db.add(db_role)
                        db.flush()  # Get the ID without committing
                        role_id_mapping[role.id] = db_role.id
                    
                    # Now create node records
                    for node in process.nodes:
                        # Get the role ID from the mapping
                        role_id = role_id_mapping.get(node.role)
                        
                        db_node = DBProcessNode(
                            process_id=db_process.id,
                            name=node.name,
                            description=node.description,
                            role_id=role_id
                        )
                        db.add(db_node)
                        db.flush()  # Get the ID without committing
                        node_id_mapping[node.id] = db_node.id
                    
                    db.commit()
                    logger.info(f"Created {len(node_id_mapping)} process node records in database")
                    
                    # Store the mapping in the process instance for later use
                    config = json.loads(process_instance.config) if process_instance.config else {}
                    config["node_id_mapping"] = {k: str(v) for k, v in node_id_mapping.items()}
                    process_instance.config = json.dumps(config)
                    db.commit()
                
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to save process configuration: {str(e)}")
                    process_instance_id = None
                    node_id_mapping = {}
                
                # Process each node in the process
                current_node = process.nodes[0]  # Start with the first node
                history = []  # Conversation history
                
                while current_node:
                    result = self._process_node(db, process, current_node, learner, history, db_process.id)
                    if not result:
                        logger.error(f"Failed to process node: {current_node.id}")
                        return False
                        
                    processed_node, response, next_node = result
                    
                    # Add to conversation history
                    history.append({
                        "node": processed_node.id,
                        "role": processed_node.role,
                        "content": response
                    })
                    
                    # Update current node
                    current_node = next_node
                    
                    if not current_node:
                        logger.info("Reached end of process or no valid next node")
                        break
                
                # 更新process实例状态为已完成
                if process_instance_id:
                    try:
                        process_instance = db.query(ProcessInstance).filter(ProcessInstance.id == process_instance_id).first()
                        if process_instance:
                            process_instance.status = ProcessInstanceStatus.COMPLETED
                            db.commit()
                            logger.info(f"Updated process instance status to completed")
                    except Exception as e:
                        logger.error(f"Failed to update process instance status: {str(e)}")
                
                # Process evolution
                self._process_evolution(db, process, learner, history, db_process.id)
                
                logger.info(f"Evolution process completed successfully: {process.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error in evolution process: {str(e)}")
                # 如果出错，更新process实例状态为失败
                if 'process_instance_id' in locals() and process_instance_id:
                    try:
                        db.rollback()  # Rollback any pending transaction
                        process_instance = db.query(ProcessInstance).filter(ProcessInstance.id == process_instance_id).first()
                        if process_instance:
                            process_instance.status = ProcessInstanceStatus.TERMINATED
                            process_instance.error = str(e)
                            db.commit()
                    except Exception as inner_e:
                        logger.error(f"Failed to update process instance error status: {str(inner_e)}")
                return False
                
    def _process_node(
        self, 
        db: Session, 
        process: Process, 
        node: ProcessNode, 
        target_user: Any,
        history: List[Dict[str, Any]],
        process_id: Any = None
    ) -> Optional[Tuple[ProcessNode, str, Optional[ProcessNode]]]:
        """
        Process a node in the evolution process.
        
        Args:
            db: Database session
            process: Process instance
            node: Current node to process
            target_user: Target user for the process
            history: Conversation history
            process_id: ID of the process in the database
            
        Returns:
            Optional tuple of (node, response, next_node)
        """
        logger.info(f"Processing node: {node.name}")
        
        try:
            # Get the appropriate LLM provider for this node
            llm_provider = self._get_provider_for_node(db, node, self.llm_provider)
            
            # Get the role for this node
            role_id = node.role
            
            # Check if node is assigned to a specific user or if it's a learner node
            is_learner_node = False
            if role_id == "learner":
                is_learner_node = True
                logger.info(f"Node {node.name} is a learner node, will use learner's model")
            elif hasattr(node, 'assigned_to') and node.assigned_to and node.assigned_to == target_user.username:
                is_learner_node = True
                logger.info(f"Node {node.name} is assigned to target user {target_user.username}")
                
            # Generate context for the node
            context = self._generate_node_context(process, node, history, target_user)
            
            # If node is for the learner, handle differently
            response = ""
            if is_learner_node:
                response = self._simulate_target_user_response(node, context)
            else:
                # Generate agent prompt
                prompt = self._generate_agent_prompt(node, context, history)
                
                # Get response from LLM
                response = llm_provider.generate(
                    prompt=prompt,
                    system_prompt=f"You are simulating a {node.role} in a process called {process.name}. {node.description}",
                    temperature=0.7,
                    max_tokens=1000
                )
                
            # Add to history
            history.append({
                "node": node.name,
                "role": role_id,
                "response": response
            })
            
            # Find next node if available
            next_node = self._find_next_node(process, node)
            
            return (node, response, next_node)
            
        except Exception as e:
            logger.error(f"Error processing node {node.name}: {str(e)}")
            return None
    
    def _update_node_status(self, db: Session, node_record_id: Any, status: str, response: str = None, error: str = None):
        """更新节点执行记录状态"""
        if not node_record_id:
            return
            
        try:
            # 使用process_instance_step表更新状态
            from agir_db.models.process_instance_step import ProcessInstanceStep
            node_record = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == node_record_id).first()
            if node_record:
                # Check if the model has a status field before trying to update it
                if hasattr(node_record, 'status'):
                    node_record.status = status
                else:
                    # If status field doesn't exist, log a warning
                    logger.warning(f"ProcessInstanceStep model doesn't have a status field, skipping status update")
                
                # Update response if the field exists and a value is provided
                if response and hasattr(node_record, 'response'):
                    node_record.response = response
                
                # Update error if the field exists and a value is provided
                if error and hasattr(node_record, 'error'):
                    node_record.error = error
                
                db.commit()
                logger.info(f"Updated node record {node_record_id}")
        except Exception as e:
            logger.error(f"Failed to update node record status: {str(e)}")
    
    def _generate_node_context(
        self, 
        process: Process, 
        node: ProcessNode, 
        history: List[Dict[str, Any]],
        user: Any
    ) -> Dict[str, Any]:
        """
        Generate context for a node.
        
        Args:
            process: Process instance
            node: Current node
            history: Conversation history
            user: User or agent for this node
            
        Returns:
            Context dictionary
        """
        return {
            "process_name": process.name,
            "process_description": process.description,
            "node_name": node.name,
            "node_description": node.description,
            "user_name": f"{user.first_name} {user.last_name}".strip(),
            "user_id": user.id,
            "history": history
        }
    
    def _generate_agent_prompt(
        self, 
        node: ProcessNode, 
        context: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a prompt for an agent.
        
        Args:
            node: Current node
            context: Context information
            history: Conversation history
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"You are now in the '{node.name}' phase.",
            node.description,
            "\nPrevious conversation:",
        ]
        
        # Add conversation history
        if history:
            for i, entry in enumerate(history):
                prompt_parts.append(f"{i+1}. {entry['role']}: {entry['content']}")
        else:
            prompt_parts.append("No previous conversation.")
            
        prompt_parts.append("\nPlease respond based on your role and the current phase.")
        
        return "\n".join(prompt_parts)
    
    def _simulate_target_user_response(self, node: ProcessNode, context: Dict[str, Any]) -> str:
        """
        Simulate a response from the target user.
        
        In a real system, this would involve actual user interaction.
        
        Args:
            node: Current node
            context: Context information
            
        Returns:
            Simulated response
        """
        # For simulation, generate a response with LLM
        system_prompt = (
            f"You are {context['user_name']}, a {node.role}. "
            f"You are currently in the '{node.name}' phase of a process. "
            f"Respond as if you are this person."
        )
        
        prompt = (
            f"Phase description: {node.description}\n\n"
            f"Please provide your response as {context['user_name']}."
        )
        
        return self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
    
    def _process_evolution(
        self, 
        db: Session, 
        process: Process, 
        learner: Any,
        history: List[Dict[str, Any]],
        process_id: Any = None
    ) -> None:
        """
        Process the evolution part of the process.
        
        Args:
            db: Database session
            process: Process instance
            learner: Target user for the process
            history: Conversation history
            process_id: ID of the process in the database
        """
        if not process.evolution:
            logger.info("No evolution defined for process")
            return
            
        logger.info(f"Processing evolution for process: {process.name}")
        
        # Get or create agent for target user
        agent = find_agent_by_role(db, "learner", process_id)
        if not agent:
            agent = create_or_update_agent(db, "learner", process_id, learner.username)
            if not agent:
                logger.error("Failed to create agent for target user")
                return
                
        # Generate evolution prompt
        prompt = f"""
        # Evolution Process for {learner.first_name} {learner.last_name}

        You are part of an evolution process called "{process.name}".
        Your objective: {process.learner.get('evolution_objective', 'Improve your skills and knowledge.')}

        ## Conversation History:
        {json.dumps(history, indent=2)}

        ## Your task:
        1. Review the conversation history.
        2. Identify strengths and weaknesses.
        3. Generate insights and recommendations for improvement.
        4. Create action items for future iterations.
        """
        
        # Get the appropriate LLM provider for evolution
        # For evolution, we'll use the target user's model if available
        llm_provider = self.llm_provider
        if self.llm_provider_manager and learner and hasattr(learner, 'llm_model') and learner.llm_model:
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
        
        # Store as a custom field for the user (另一种方法，确保至少有一种成功)
        evolution_field_name = f"evolution_{process.id}"
        
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
                # 添加调试日志
                logger.info(f"Creating second CustomField with: user_id={learner.id}, field_name={evolution_field_name}, field_value={evolution_result[:20]}...")
                # Create new CustomField without db parameter
                evolution_field = CustomField(
                    user_id=learner.id,
                    field_name=evolution_field_name,
                    field_value=evolution_result
                )
                db.add(evolution_field)
            except Exception as e:
                logger.error(f"Failed to create CustomField: {str(e)}")
                # 添加详细错误日志
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return
            
        db.commit() 

    def _find_next_node(self, process: Process, current_node: ProcessNode) -> Optional[ProcessNode]:
        """
        Find the next node in the process based on the current node.
        
        Args:
            process: Process instance
            current_node: Current node
            
        Returns:
            Optional[ProcessNode]: Next node if available, None otherwise
        """
        if not hasattr(process, 'transitions') or not process.transitions:
            return None
            
        # Find transitions where current node is the 'from' node
        next_node_names = []
        for transition in process.transitions:
            if transition.get('from') == current_node.name:
                next_node_names.append(transition.get('to'))
                
        if not next_node_names:
            return None
            
        # Get the first next node (could be extended with branching logic)
        next_node_name = next_node_names[0]
        
        # Find the node in the process nodes
        for node in process.nodes:
            if node.name == next_node_name:
                return node
                
        return None 