"""
Run evolution process
"""
import logging
import uuid
import sys
import time
from typing import Optional, Union, List, Dict, Any

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step, StepStatus
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.evolution.a_create_or_find_episode import a_create_or_find_episode
from src.evolution.b_get_initial_state import b_get_initial_state
from src.evolution.c_get_state_roles import c_get_state_roles
from src.evolution.d_get_or_create_user_for_state import d_get_or_create_user_for_state
from src.evolution.e_create_or_find_step import e_create_or_find_step
from src.evolution.g_update_step import g_update_step
from src.common.utils.memory_utils import create_user_memory
from src.evolution.k_create_memory import create_episode_memories

from .j_get_next_state import j_get_next_state
from .f_generate_llm_response import f_generate_llm_response
from .h_create_conversation import h_create_conversation
from .i_conduct_multi_turn_conversation import i_conduct_multi_turn_conversation

logger = logging.getLogger(__name__)

def start_episode(scenario_id: int) -> Optional[int]:
    """
    Execute a scenario from start to finish.
    
    Args:
        scenario_id: ID of the scenario
        
    Returns:
        Optional[int]: ID of the episode if successful, None otherwise
    """
    try:
        db = next(get_db())
        episode = a_create_or_find_episode(scenario_id)
        episode_id = episode.id
        current_state = b_get_initial_state(db, scenario_id)
                 
        # Load all completed steps for context
        all_steps = db.query(Step).filter(
            Step.episode_id == episode_id,
            Step.status == StepStatus.COMPLETED
        ).all()

        # Continue processing states until we reach the end
        while current_state:
            roles = c_get_state_roles(db, current_state.id)

            role_users = []
            for role in roles:
                user = d_get_or_create_user_for_state(db, role.id)
                if not user:
                    logger.error(f"Failed to get or create user for role: {role.id}")
                    sys.exit(1)
                role_users.append((role, user))
            
            if len(role_users) == 1:
                role, user = role_users[0]
                
                # Create step with RUNNING status
                step_id = e_create_or_find_step(
                    db, episode_id, current_state.id, user.id
                )
                
                try:
                    # Generate LLM response
                    response = f_generate_llm_response(db, current_state, role, user, all_steps)
                    
                    # Update step with generated data and mark as COMPLETED
                    g_update_step(db, step_id, response, StepStatus.COMPLETED)
                    
                    # Add step to history
                    step = db.query(Step).filter(Step.id == step_id).first()
                    all_steps.append(step)
                    
                except Exception as e:
                    # Update step status to FAILED if there's an error
                    g_update_step(db, step_id, f"Failed to generate response: {str(e)}", StepStatus.FAILED)
                    logger.error(f"Failed to generate response: {str(e)}")
                    episode.status = EpisodeStatus.FAILED
                    db.commit()
                    sys.exit(1)
            
            else:
                # Create step for the conversation with RUNNING status
                step_id = e_create_or_find_step(
                    db, episode_id, current_state.id, role_users[0][1].id
                )
                
                try:
                    # Add step to history
                    step = db.query(Step).filter(Step.id == step_id).first()
                    all_steps.append(step)
                    
                    # Create conversation linked to the step
                    conversation = h_create_conversation(db, current_state, episode_id, role_users, step_id)
                    if not conversation:
                        logger.error(f"Failed to create conversation for state: {current_state.id}")
                        g_update_step(db, step_id, "Failed to create conversation", StepStatus.FAILED)
                        episode.status = EpisodeStatus.FAILED
                        db.commit()
                        return None
                    
                    # Conduct multi-turn conversation
                    conversation_result = i_conduct_multi_turn_conversation(
                        db, conversation, current_state, role_users
                    )
                    
                    # Update the step with conversation results and mark as COMPLETED
                    g_update_step(db, step_id, conversation_result, StepStatus.COMPLETED)
                    
                    # Also update episode status to mark this state as processed
                    episode = db.query(Episode).filter(Episode.id == episode_id).first()
                    if episode:
                        episode.last_updated = time.time()
                        db.commit()
                        
                except Exception as e:
                    # Update step status to FAILED if there's an error
                    g_update_step(db, step_id, f"Failed in conversation: {str(e)}", StepStatus.FAILED)
                    logger.error(f"Failed in conversation: {str(e)}")
                    episode.status = EpisodeStatus.FAILED
                    db.commit()
                    return None
            
            # Update episode with current state
            episode.current_state_id = current_state.id
            db.commit()
            
            logger.info(f"Current state in the circle: {current_state}")
            # 7. Find next state
            next_state = j_get_next_state(db, scenario_id, current_state.id, episode_id, role_users[0][1])
            
            # If no next state, we've reached the end
            if not next_state:
                logger.info(f"Episode {episode_id} completed successfully")
                episode = db.query(Episode).filter(Episode.id == episode_id).first()
                episode.current_state_id = current_state.id
                episode.status = EpisodeStatus.COMPLETED
                db.commit()
                
                # Create memories for the episode after it completes
                memory_created = create_episode_memories(db, episode_id)
                if memory_created:
                    logger.info(f"Successfully created memories for episode {episode_id}")
                else:
                    logger.warning(f"Failed to create memories for episode {episode_id}")
                
                break
            
            # Move to next state
            current_state = next_state
        
        return episode_id
        
    except Exception as e:
        logger.error(f"Failed to execute scenario: {str(e)}")
        return None

def run_evolution(scenario_id: Union[int, str, uuid.UUID], num_episodes: int = 1) -> bool:
    """
    Run a previously defined scenario.
    
    Args:
        scenario_id: ID of the scenario to run
        num_episodes: Number of episodes to run (default: 1)
        
    Returns:
        bool: True if successful, False otherwise
    """
    db = None
    success = True
    
    try:
        db = next(get_db())
        
        logger.info(f"Looking up scenario with ID: {scenario_id}")
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        
        if not scenario:
            logger.error(f"No scenario found with ID: {scenario_id}")
            return False
        
        logger.info(f"Found scenario: {scenario.name}")
        
        logger.info(f"Running {num_episodes} episodes for scenario: {scenario.name}")
        
        for i in range(num_episodes):
            logger.info(f"Starting episode {i+1} of {num_episodes}")
            
            result = start_episode(scenario_id)
            
            if not result:
                logger.error(f"Failed to execute episode {i+1}")
                success = False
            else:
                   
                logger.info(f"Successfully completed episode {i+1}")
        
        return success
        
    except Exception as e:
        logger.exception(f"Error running evolution: {str(e)}")
        return False
    finally:
        if db:
            db.close()