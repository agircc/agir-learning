import logging
import uuid
import sys
import time
from typing import Optional, Union, List, Dict, Any
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step, StepStatus
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.common.data_store import get_learner
from src.evolution.a_create_or_find_episode import a_create_or_find_episode
from src.evolution.b_get_initial_state import b_get_initial_state
from src.evolution.c_get_state_roles import c_get_state_roles
from src.evolution.d_get_or_create_user_for_state import d_get_or_create_user_for_state
from src.evolution.e_create_or_find_step import e_create_or_find_step
from src.evolution.g_update_step import g_update_step
from src.common.utils.memory_utils import create_user_memory

from .j_get_next_state import j_get_next_state
from .f_generate_llm_response import f_generate_llm_response
from .h_create_conversation import h_create_conversation
from .i_conduct_multi_turn_conversation import i_conduct_multi_turn_conversation

logger = logging.getLogger(__name__)

def create_episode_memories(db: Session, episode_id: uuid.UUID) -> bool:
    """
    Create memories for an episode after it completes.
    
    Args:
        db: Database session (existing session, don't close it)
        episode_id: ID of the completed episode
        
    Returns:
        bool: True if memories were created successfully, False otherwise
    """
    try:
        # Get the episode
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            logger.error(f"Episode with ID {episode_id} not found")
            return False
            
        # Get the scenario
        scenario = db.query(Scenario).filter(Scenario.id == episode.scenario_id).first()
        if not scenario:
            logger.error(f"Scenario with ID {episode.scenario_id} not found")
            return False
            
        # Find the learner user assigned to this episode
        learner_user = get_learner()
        
        if not learner_user:
            logger.error(f"Learner user not found for episode {episode_id}")
            return False
            
        if not learner_user.llm_model:
            logger.error(f"Learner user {learner_user.id} has no LLM model specified")
            return False
            
        # Get all steps in the episode
        steps = db.query(Step).filter(
            Step.episode_id == episode_id,
            Step.status == StepStatus.COMPLETED
        ).all()
        
        # Get all conversations in the episode by joining through steps
        # First, get all step IDs for this episode
        step_ids = [step.id for step in steps]
        
        # Then get conversations linked to these steps
        conversations = []
        if step_ids:
            conversations = db.query(ChatConversation).filter(
                ChatConversation.related_id.in_(step_ids)
            ).all()
        
        # Collect content from all steps and conversations
        all_content = []
        
        # Add step content
        for step in steps:
            if step.generated_text and len(step.generated_text.strip()) > 0:
                state = db.query(State).filter(State.id == step.state_id).first()
                if state:
                    all_content.append({
                        "state_name": state.name,
                        "content": step.generated_text,
                        "type": "step"
                    })
                    
        # Add conversation content
        for conversation in conversations:
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.created_at).all()
            
            if messages:
                conversation_text = ""
                for msg in messages:
                    sender = db.query(User).filter(User.id == msg.sender_id).first()
                    if sender:
                        conversation_text += f"{sender.username}: {msg.content}\n\n"
                
                if conversation_text:
                    # Find the state through the step
                    step = db.query(Step).filter(Step.id == conversation.related_id).first()
                    if step:
                        state = db.query(State).filter(State.id == step.state_id).first()
                        if state:
                            all_content.append({
                                "state_name": state.name,
                                "content": conversation_text,
                                "type": "conversation"
                            })
        
        # Create a comprehensive memory for the entire episode
        if all_content:
            # Prepare the content for memory creation
            episode_summary = f"Episode {episode_id} Summary:\n\n"
            
            for item in all_content:
                episode_summary += f"=== {item['state_name']} ({item['type']}) ===\n"
                episode_summary += item['content']
                episode_summary += "\n\n"
                
            # Prepare context info
            context_info = {
                "state_name": "Episode Summary",
                "task": f"Episode {episode_id} for scenario '{scenario.name}'",
                "content_type": "Full Episode"
            }
            
            # Prepare metadata
            metadata = {
                "episode_id": episode_id,
                "scenario_id": scenario.id,
                "scenario_name": scenario.name
            }
            
            # Use the passed db session to create memory, don't create a new connection
            memory_id = create_user_memory(
                db=db,
                user_id=learner_user.id,
                context_info=context_info,
                original_content=episode_summary,
                model_name=learner_user.llm_model,
                metadata=metadata,
                source="episode",
                source_id=episode_id,
                importance=1.5  # Higher importance for episode summaries
            )
            
            if memory_id:
                logger.info(f"Successfully created episode memory with ID {memory_id} for episode {episode_id}")
                return True
            else:
                logger.error(f"Failed to create episode memory for episode {episode_id}")
                return False
        else:
            logger.warning(f"No content found to create memory for episode {episode_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating episode memories: {str(e)}")
        return False