"""
Evolution module - handles the main evolution process
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from agir_db.db.session import SessionLocal
# 使用User模型的自定义字段，而不是直接导入可能不存在的CustomField
from agir_db.models.user import User
from agir_db.models.process import Process as DBProcess  # 使用正确的Process类名
from .models.process import Process, ProcessNode
from .models.agent import Agent
from .llms import BaseLLMProvider, OpenAIProvider, AnthropicProvider
from .utils.database import get_or_create_user, create_or_update_agent, find_agent_by_role, create_process_record, CustomField
from .utils.yaml_loader import load_process_from_file

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EvolutionEngine:
    """
    Main engine for running the evolution process.
    """
    
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the evolution engine.
        
        Args:
            llm_provider: Optional LLM provider, defaults to OpenAI if not provided
        """
        self.llm_provider = llm_provider or self._create_default_provider()
        
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
            True if successful, False otherwise
        """
        logger.info(f"Starting evolution process: {process.name}")
        
        # Create database session
        with SessionLocal() as db:
            try:
                # 保存process实例到数据库
                db_process = create_process_record(db, {
                    "name": process.name,
                    "description": process.description
                })
                logger.info(f"Created process record in database with ID: {db_process.id}")
                
                # 保存配置作为自定义字段到数据库
                try:
                    # 将配置保存到process_instance_step表
                    from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
                    process_instance = ProcessInstance(
                        process_id=db_process.id,
                        status=ProcessInstanceStatus.RUNNING
                    )
                    db.add(process_instance)
                    db.commit()
                    logger.info(f"Saved process instance to database")
                    process_instance_id = process_instance.id
                except Exception as e:
                    logger.error(f"Failed to save process configuration: {str(e)}")
                    process_instance_id = None
                
                # Get or create target user
                target_username = process.target_user.get("username")
                if not target_username:
                    logger.error("Target user username not specified in process")
                    return False
                
                target_user, created = get_or_create_user(db, target_username, process.target_user)
                if created:
                    logger.info(f"Created new target user: {target_username}")
                else:
                    logger.info(f"Using existing target user: {target_username}")
                
                # Process each node in the process
                current_node = process.nodes[0]  # Start with the first node
                history = []  # Conversation history
                
                while current_node:
                    result = self._process_node(db, process, current_node, target_user, history, db_process.id)
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
                self._process_evolution(db, process, target_user, history, db_process.id)
                
                logger.info(f"Evolution process completed successfully: {process.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error in evolution process: {str(e)}")
                # 如果出错，更新process实例状态为失败
                if 'process_instance_id' in locals() and process_instance_id:
                    try:
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
        Process a single node in the process.
        
        Args:
            db: Database session
            process: Process instance
            node: Current node to process
            target_user: Target user
            history: Conversation history
            process_id: 数据库中的进程ID
            
        Returns:
            Tuple of (processed_node, response, next_node) or None if failed
        """
        logger.info(f"Processing node: {node.id} - {node.name}")
        
        # 保存节点执行记录到数据库
        node_record_id = None
        if process_id:
            try:
                # 使用process_instance_step表记录节点执行
                from agir_db.models.process_instance_step import ProcessInstanceStep
                
                # 查找当前进程实例
                from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
                process_instance = db.query(ProcessInstance).filter(
                    ProcessInstance.process_id == process_id,
                    ProcessInstance.status.in_([ProcessInstanceStatus.RUNNING])
                ).first()
                
                if process_instance:
                    # 创建步骤记录
                    node_record = ProcessInstanceStep(
                        process_instance_id=process_instance.id,
                        step_id=node.id,
                        name=node.name,
                        role=node.role,
                        status="started",
                        data=json.dumps({
                            "description": node.description,
                            "assigned_to": node.assigned_to
                        })
                    )
                    db.add(node_record)
                    db.commit()
                    node_record_id = node_record.id
                    logger.info(f"Created node record with ID: {node_record_id}")
                else:
                    logger.warning(f"No active process instance found for process ID: {process_id}")
            except Exception as e:
                logger.error(f"Failed to create node record: {str(e)}")
        
        # Get the role
        role = process.get_role(node.role)
        if not role:
            logger.error(f"Role not found for node: {node.id}, role: {node.role}")
            self._update_node_status(db, node_record_id, "failed", error="Role not found")
            return None
            
        # Check if this node is assigned to the target user
        if node.assigned_to and node.assigned_to == target_user.username:
            logger.info(f"Node {node.id} is assigned to target user {target_user.username}")
            
            # Generate context for this node
            context = self._generate_node_context(process, node, history, target_user)
            
            # Determine how to handle this node (could involve user interaction in a real system)
            response = self._simulate_target_user_response(node, context)
            
        else:
            # Create or get agent for this role
            agent_data = {
                "username": f"{node.role}_{node.id}",
                "role": node.role,
                "name": role.name,
                "description": role.description
            }
            
            agent_user = create_or_update_agent(db, agent_data, target_user.id)
            
            # Generate context for this node
            context = self._generate_node_context(process, node, history, agent_user)
            
            # Create agent model
            agent = Agent(
                id=agent_user.id,
                name=role.name,
                role=node.role,
                description=role.description
            )
            
            # Generate system prompt
            system_prompt = role.format_system_prompt(context)
            
            # Generate prompt for the agent
            prompt = self._generate_agent_prompt(node, context, history)
            
            # Get response from LLM
            response = self.llm_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # Save response as memory for the agent
            agent.add_memory(
                content=f"In {node.name}: {response}",
                metadata={"node_id": node.id, "process_id": process.id}
            )
            
            # 保存记忆到数据库
            try:
                # 检查memory表是否存在
                from agir_db.models.memory import Memory
                memory = Memory(
                    user_id=agent_user.id,
                    content=f"In {node.name}: {response}",
                    metadata=json.dumps({
                        "node_id": node.id, 
                        "process_id": process.id,
                        "node_name": node.name
                    })
                )
                db.add(memory)
                db.commit()
                logger.info(f"Saved agent memory to database for user {agent_user.id}")
            except Exception as e:
                logger.error(f"Failed to save agent memory: {str(e)}")
        
        # 更新节点状态为已完成
        self._update_node_status(db, node_record_id, "completed", response=response)
        
        # Determine next node
        next_nodes = process.next_nodes(node.id)
        if not next_nodes:
            return node, response, None
            
        # For simplicity, just take the first next node
        # In a real system, this could involve branching logic
        next_node = next_nodes[0]
        
        return node, response, next_node
    
    def _update_node_status(self, db: Session, node_record_id: int, status: str, response: str = None, error: str = None):
        """更新节点执行记录状态"""
        if not node_record_id:
            return
            
        try:
            # 使用process_instance_step表更新状态
            from agir_db.models.process_instance_step import ProcessInstanceStep
            node_record = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == node_record_id).first()
            if node_record:
                node_record.status = status
                if response:
                    # 更新response字段
                    node_record.response = response
                if error:
                    # 更新error字段
                    node_record.error = error
                db.commit()
                logger.info(f"Updated node record {node_record_id} status to {status}")
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
        target_user: Any,
        history: List[Dict[str, Any]],
        process_id: Any = None
    ) -> None:
        """
        Process the evolution of the target user based on the completed process.
        
        Args:
            db: Database session
            process: Process instance
            target_user: Target user
            history: Conversation history
            process_id: 数据库中的进程ID
        """
        logger.info(f"Processing evolution for user: {target_user.username}")
        
        # Extract evolution method from process
        evolution_method = process.evolution.get("method", "default")
        evolution_description = process.evolution.get("description", "")
        
        # Generate a reflection prompt for the evolution
        system_prompt = (
            f"You are an AI mentor helping {target_user.first_name} {target_user.last_name} "
            f"evolve their skills using the {evolution_method} method. "
            f"Generate a thoughtful reflection on their performance and learning."
        )
        
        # Create a summary of the process history
        history_summary = "\n".join([
            f"- In {entry['node']}, {entry['role']} said: {entry['content'][:200]}..." 
            for entry in history
        ])
        
        prompt = (
            f"Evolution Method: {evolution_method}\n"
            f"Evolution Description: {evolution_description}\n"
            f"User: {target_user.first_name} {target_user.last_name}\n"
            f"Evolution Objective: {process.target_user.get('evolution_objective', 'Improve skills')}\n\n"
            f"Process Summary:\n{history_summary}\n\n"
            f"Based on this experience, provide:\n"
            f"1. A reflection on what the user has learned\n"
            f"2. Key insights gained\n"
            f"3. Skills that were improved\n"
            f"4. Suggestions for further improvement\n"
        )
        
        # Generate the evolution reflection
        reflection = self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000
        )
        
        # 保存进化反思到数据库
        if process_id:
            try:
                # 使用custom_fields保存进化反思
                evolution_field = CustomField(
                    user_id=target_user.id,
                    field_name=f"evolution_{process_id}",
                    field_value=reflection
                )
                db.add(evolution_field)
                db.commit()
                logger.info(f"Saved evolution reflection to database for user {target_user.id}")
                
                # 如果process_instance存在，关联evolution到进程实例
                try:
                    from agir_db.models.process_instance import ProcessInstance
                    process_instance = db.query(ProcessInstance).filter(
                        ProcessInstance.process_id == process_id
                    ).first()
                    
                    if process_instance:
                        # process_instance.evolution field doesn't exist - logging instead
                        logger.info(f"Process instance found but evolution field doesn't exist on the model")
                        db.commit()
                        logger.info(f"Updated process instance")
                except Exception as e:
                    logger.error(f"Failed to update process instance with evolution: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to save evolution reflection: {str(e)}")
        
        # Store as a custom field for the user (另一种方法，确保至少有一种成功)
        evolution_field_name = f"evolution_{process.id}"
        
        # Check if we already have an evolution field for this process
        existing_field = db.query(CustomField).filter(
            CustomField.user_id == target_user.id,
            CustomField.field_name == evolution_field_name
        ).first()
        
        if existing_field:
            # Update existing field
            existing_field.field_value = reflection
        else:
            # Create new field
            try:
                # Check if CustomField requires db parameter
                import inspect
                custom_field_params = inspect.signature(CustomField.__init__).parameters
                if 'db' in custom_field_params:
                    evolution_field = CustomField(
                        db=db,
                        user_id=target_user.id,
                        field_name=evolution_field_name,
                        field_value=reflection
                    )
                else:
                    evolution_field = CustomField(
                        user_id=target_user.id,
                        field_name=evolution_field_name,
                        field_value=reflection
                    )
                db.add(evolution_field)
            except Exception as e:
                logger.error(f"Failed to create CustomField: {str(e)}")
                return
            
        db.commit() 