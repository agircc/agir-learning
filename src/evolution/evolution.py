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
    

    

    