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
from agir_db.models.custom_field import CustomField

from src.llms.llm_provider_manager import LLMProviderManager  # 明确从agir_db包导入CustomField
from src.models.process import Process, ProcessNode
from src.models.agent import Agent
from src.llms import BaseLLMProvider, OpenAIProvider, AnthropicProvider
from src.utils.database import get_or_create_user, find_user_by_role, create_process_record, find_or_create_learner
from src.utils.yaml_loader import load_process_from_file
from src.process_manager import ProcessManager  # Import the new ProcessManager

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
    
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the evolution engine.
        
        Args:
            llm_provider: Optional LLM provider (deprecated, use llm_provider_manager instead)
        """
            
        self.llm_provider_manager = LLMProviderManager()
        
        # For backward compatibility - use only in methods that don't support specific models
        self.llm_provider = llm_provider
        
        # Initialize the process manager
        from src.process_manager import ProcessManager
        self.process_manager = ProcessManager()
        
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
            default_provider: Default provider to use if no specific model is found (ignored)
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If no model is specified for the role or user
        """
        if not self.llm_provider_manager:
            raise ValueError("LLM provider manager is required")
            
        # Get the role for this node
        if not node.role:
            raise ValueError(f"Node {node.name} has no role specified")
            
        # Special handling for learner role
        if node.role == "learner":
            # Get the learner user
            if hasattr(node, 'assigned_to') and node.assigned_to:
                user = db.query(User).filter(User.username == node.assigned_to).first()
                if user and hasattr(user, 'llm_model') and user.llm_model:
                    logger.info(f"Using learner's model '{user.llm_model}' for node: {node.name}")
                    return self.llm_provider_manager.get_provider(user.llm_model)
                else:
                    raise ValueError(f"Learner user '{node.assigned_to}' has no model specified")
            
            # Try to find an active learner user
            user = db.query(User).filter(User.is_active == True).first()
            if user and hasattr(user, 'llm_model') and user.llm_model:
                logger.info(f"Using active user's model '{user.llm_model}' for learner node: {node.name}")
                return self.llm_provider_manager.get_provider(user.llm_model)
            else:
                raise ValueError("No active user with model specified found for learner role")
            
        # Query the database to get the role's model
        from agir_db.models.process_role import ProcessRole
        role = db.query(ProcessRole).filter(ProcessRole.id == node.role).first()
        
        if not role:
            raise ValueError(f"Role with ID {node.role} not found")
            
        if not hasattr(role, 'model') or not role.model:
            # Try to get the model from assigned_to user if available
            if hasattr(node, 'assigned_to') and node.assigned_to:
                user = db.query(User).filter(User.username == node.assigned_to).first()
                if user and hasattr(user, 'llm_model') and user.llm_model:
                    logger.info(f"Using assigned user's model '{user.llm_model}' for node: {node.name}")
                    return self.llm_provider_manager.get_provider(user.llm_model)
                else:
                    raise ValueError(f"Assigned user '{node.assigned_to}' for node {node.name} has no model specified")
            else:
                raise ValueError(f"Role '{role.name}' has no model specified and node is not assigned to a user")
            
        # Use the model specified for the role
        logger.info(f"Using role's model '{role.model}' for node: {node.name}")
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
        
    
        
    def run_evolution(self, process: Process) -> bool:
        """
        Run the evolution process.
        
        Args:
            process: Process instance
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If process fails for any reason
        """
        logger.info(f"Starting evolution process: {process.name}")
        
        # Create database session
        with SessionLocal() as db:
            # Get or create target user first
            learnername = process.learner.get("username")
            if not learnername:
                raise ValueError("Target user username not specified in process")
            
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
            
            # Process each node in the process
            current_node = process.nodes[0]  # Start with the first node
            history = []  # Conversation history
            
            while current_node:
                result = self._process_node(db, process, current_node, learner, history, db_process.id)
                
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
                process_instance = db.query(ProcessInstance).filter(ProcessInstance.id == process_instance_id).first()
                if process_instance:
                    process_instance.status = ProcessInstanceStatus.COMPLETED
                    db.commit()
                    logger.info(f"Updated process instance status to completed")
            
            # Process evolution
            self._process_evolution(db, process, learner, history, db_process.id)
            
            logger.info(f"Evolution process completed successfully: {process.name}")
            return True
        
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
            Tuple of (node, response, next_node)
            
        Raises:
            ValueError: If there is an error processing the node
        """
        logger.info(f"Processing node: {node.name}")
        
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
        try:
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
            error_msg = f"Error processing node {node.name}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
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
            
        Raises:
            ValueError: If user has no model specified
        """
        # Get the user ID from context
        user_id = context.get('user_id')
        if not user_id:
            raise ValueError("User ID not found in context")
            
        # Get the user from database
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
                
            # Check if user has a model specified
            if not hasattr(user, 'llm_model') or not user.llm_model:
                raise ValueError(f"User '{user.username}' has no model specified")
                
            # Get the appropriate LLM provider for this user
            llm_provider = self.llm_provider_manager.get_provider(user.llm_model)
            
            # Generate system prompt
            system_prompt = (
                f"You are {context['user_name']}, a {node.role}. "
                f"You are currently in the '{node.name}' phase of a process. "
                f"Respond as if you are this person."
            )
            
            # Generate prompt
            prompt = (
                f"Phase description: {node.description}\n\n"
                f"Please provide your response as {context['user_name']}."
            )
            
            logger.info(f"Generating response for {context['user_name']} using model: {user.llm_model}")
            return llm_provider.generate(
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
            learner: The learner user that is evolving through this process
            history: Conversation history
            process_id: ID of the process in the database
            
        Raises:
            ValueError: If learner has no model specified
        """
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
        agent = find_user_by_role(db, "learner", process_id)
        if not agent:
            agent = create_user(db, "learner", process_id, learner.username)
            if not agent:
                raise ValueError(f"Failed to create agent for learner {learner.username}")
                
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

    def _find_next_node(self, process: Process, current_node: ProcessNode) -> Optional[ProcessNode]:
        """
        Find the next node in the process based on the current node.
        
        Args:
            process: Process instance
            current_node: Current node
            
        Returns:
            Optional[ProcessNode]: Next node if available, None otherwise
        """
        # Check if process is a dictionary (from get_process) or a Process object
        is_dict = isinstance(process, dict)
        
        # Access transitions based on the object type
        if is_dict:
            transitions = process.get("transitions", [])
            if not transitions:
                return None
        else:
            if not hasattr(process, 'transitions') or not process.transitions:
                return None
            transitions = process.transitions
            
        # Find transitions where current node is the 'from' node
        next_node_names = []
        for transition in transitions:
            # Handle both dictionary and object cases
            if is_dict:
                from_node = transition.get('from') 
                to_node = transition.get('to')
            else:
                from_node = transition.get('from') if isinstance(transition, dict) else getattr(transition, 'from_node', None)
                to_node = transition.get('to') if isinstance(transition, dict) else getattr(transition, 'to_node', None)
                
            # Get current node name, accounting for both dict and object
            current_node_name = current_node.name if hasattr(current_node, 'name') else current_node.get('name')
            
            if from_node == current_node_name:
                next_node_names.append(to_node)
                
        if not next_node_names:
            return None
            
        # Get the first next node (could be extended with branching logic)
        next_node_name = next_node_names[0]
        
        # Access nodes based on the object type
        if is_dict:
            nodes = process.get("nodes", [])
        else:
            nodes = process.nodes
            
        # Find the node in the process nodes
        for node in nodes:
            # Handle both dictionary and object cases
            node_name = node.name if hasattr(node, 'name') else node.get('name')
            if node_name == next_node_name:
                return node
                
        return None 