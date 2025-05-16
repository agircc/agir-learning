"""
Execute scenario - handles running a specific episode
"""

import logging
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.scenario import Scenario
from agir_db.models.state_role import StateRole
from agir_db.models.state import State
from agir_db.models.state_transition import StateTransition
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step, StepStatus
from agir_db.models.agent_assignment import AgentAssignment
from agir_db.models.chat_message import ChatMessage
from agir_db.schemas.state import StateInDBBase

from src.evolution.b_get_state import b_get_state
from src.evolution.c_get_state_roles import c_get_state_roles
from src.evolution.d_get_or_create_agent_assignment import d_get_or_create_agent_assignment
from src.evolution.scenario_manager.create_agent_assignment import create_agent_assignment
from src.evolution.update_step import update_step

from .scenario_manager.get_next_state import get_next_state
from .scenario_manager.generate_llm_response import generate_llm_response
from .coversation.create_conversation import create_conversation
from .coversation.conduct_multi_turn_conversation import conduct_multi_turn_conversation

logger = logging.getLogger(__name__)

class ScenarioManager:
    """
    Manages the creation and execution of scenarios.
    """
    
    @staticmethod
    def _create_episode(db: Session, scenario_id: int, initiator_id: int) -> Optional[int]:
        """
        Create an episode.
        
        Args:
            db: Database session
            scenario_id: ID of the scenario
            initiator_id: ID of the initiator
            
        Returns:
            Optional[int]: ID of the episode if successful, None otherwise
        """
        try:
            episode = Episode(
                scenario_id=scenario_id,
                initiator_id=initiator_id,
                status=EpisodeStatus.RUNNING
            )
            
            db.add(episode)
            db.commit()
            db.refresh(episode)
            
            logger.info(f"Created episode with ID: {episode.id}")
            return episode.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create episode: {str(e)}")
            return None
    
    
    
    
    
    
    
    @staticmethod
    def _create_step(
        db: Session, 
        episode_id: int, 
        state_id: int, 
        user_id: Optional[int] = None,
        generated_text: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a step.
        
        Args:
            db: Database session
            episode_id: ID of the episode
            state_id: ID of the state
            user_id: ID of the user (optional)
            generated_text: Comment/data from LLM (optional)
            
        Returns:
            Optional[int]: ID of the step if successful, None otherwise
        """
        try:
            step = Step(
                episode_id=episode_id,
                state_id=state_id,
                user_id=user_id,
                action="scenario",
                generated_text=generated_text
            )
            
            db.add(step)
            db.commit()
            db.refresh(step)
            
            logger.info(f"Created step with ID: {step.id}")
            
            return step.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create step: {str(e)}")
            return None

    

    
 
def execute_episode(scenario_id: int, episode_id: int) -> Optional[int]:
    """
    Execute a scenario from start to finish.
    
    Args:
        scenario_id: ID of the scenario
        
    Returns:
        Optional[int]: ID of the episode if successful, None otherwise
    """
    try:
        db = next(get_db())
        
        # Check if the episode exists and is not completed
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            logger.error(f"Episode with ID {episode_id} not found")
            return None
        
        # If episode has a current state, use it instead of getting initial state
        if episode.current_state_id and episode.status == EpisodeStatus.RUNNING:
            current_state = db.query(State).filter(State.id == episode.current_state_id).first()
            logger.info(f"Continuing with existing state: {current_state.name if current_state else None}")
            
            # Check for unfinished or failed steps in the current state
            unfinished_steps = db.query(Step).filter(
                Step.episode_id == episode_id,
                Step.state_id == current_state.id,
                Step.status.in_([StepStatus.PENDING, StepStatus.RUNNING, StepStatus.FAILED])
            ).all()
            
            if unfinished_steps:
                logger.info(f"Found {len(unfinished_steps)} unfinished steps in current state {current_state.name}")
                
                # Update unfinished/running steps back to pending so they can be retried
                for step in unfinished_steps:
                    logger.info(f"Resetting step {step.id} from status {step.status} to PENDING")
                    update_step(db, step.id, status=StepStatus.PENDING)
                
                # Load all completed steps for context
                completed_steps = db.query(Step).filter(
                    Step.episode_id == episode_id,
                    Step.status == StepStatus.COMPLETED
                ).all()
                all_steps = completed_steps
            else:
                # No unfinished steps found, load all steps for context
                all_steps = db.query(Step).filter(
                    Step.episode_id == episode_id
                ).all()
        else:
            # Get initial state if episode is new or doesn't have a current state
            current_state = b_get_state(db, scenario_id)
            if not current_state:
                logger.error(f"No initial state found for scenario: {scenario_id}")
                return None
            
            # Initialize episode with current state
            episode.current_state_id = current_state.id
            db.commit()
            
            # No steps yet
            all_steps = []
        
        logger.info(f"Current state: {current_state}")
        
        # Continue processing states until we reach the end
        while current_state:
            # 3. Get all roles associated with the state
            roles = c_get_state_roles(db, current_state.id)
            if not roles:
                logger.error(f"Failed to get roles for state: {current_state.id}")
                return None
            
            # 4. Get or create users for each role
            role_users = []
            for role in roles:
                user = d_get_or_create_agent_assignment(db, role.id, episode_id)
                if not user:
                    logger.error(f"Failed to get or create user for role: {role.id}")
                    return None
                role_users.append((role, user))
            
            # 5. If there's only one role, generate a simple response
            if len(role_users) == 1:
                role, user = role_users[0]
                
                # Create step with RUNNING status
                step_id = ScenarioManager._create_step(
                    db, episode_id, current_state.id, user.id
                )
                
                if not step_id:
                    logger.error(f"Failed to create step for state: {current_state.id}")
                    return None
                
                # Update the step status to RUNNING
                update_step(db, step_id, status=StepStatus.RUNNING)
                
                try:
                    # Generate LLM response
                    response = generate_llm_response(db, current_state, role, user, all_steps)
                    
                    # Update step with generated data and mark as COMPLETED
                    update_step(db, step_id, response, StepStatus.COMPLETED)
                    
                    # Add step to history
                    step = db.query(Step).filter(Step.id == step_id).first()
                    all_steps.append(step)
                    
                except Exception as e:
                    # Update step status to FAILED if there's an error
                    update_step(db, step_id, f"Failed to generate response: {str(e)}", StepStatus.FAILED)
                    logger.error(f"Failed to generate response: {str(e)}")
                    episode.status = EpisodeStatus.FAILED
                    db.commit()
                    return None
            
            # 6. If there are multiple roles, conduct a multi-turn conversation
            else:
                # Create step for the conversation with RUNNING status
                step_id = ScenarioManager._create_step(
                    db, episode_id, current_state.id, role_users[0][1].id
                )
                
                if not step_id:
                    logger.error(f"Failed to create step for state: {current_state.id}")
                    return None
                
                # Update the step status to RUNNING
                update_step(db, step_id, f"Multi-role conversation for state: {current_state.name}", StepStatus.RUNNING)
                
                try:
                    # Add step to history
                    step = db.query(Step).filter(Step.id == step_id).first()
                    all_steps.append(step)
                    
                    # Create conversation linked to the step
                    conversation = create_conversation(db, current_state, episode_id, role_users, step_id)
                    if not conversation:
                        logger.error(f"Failed to create conversation for state: {current_state.id}")
                        update_step(db, step_id, "Failed to create conversation", StepStatus.FAILED)
                        episode.status = EpisodeStatus.FAILED
                        db.commit()
                        return None
                    
                    # Conduct multi-turn conversation
                    conversation_result = conduct_multi_turn_conversation(
                        db, conversation, current_state, role_users
                    )
                    
                    # Update the step with conversation results and mark as COMPLETED
                    update_step(db, step_id, conversation_result, StepStatus.COMPLETED)
                    
                    # Also update episode status to mark this state as processed
                    episode = db.query(Episode).filter(Episode.id == episode_id).first()
                    if episode:
                        episode.last_updated = time.time()
                        db.commit()
                        
                except Exception as e:
                    # Update step status to FAILED if there's an error
                    update_step(db, step_id, f"Failed in conversation: {str(e)}", StepStatus.FAILED)
                    logger.error(f"Failed in conversation: {str(e)}")
                    episode.status = EpisodeStatus.FAILED
                    db.commit()
                    return None
            
            # Update episode with current state
            episode.current_state_id = current_state.id
            db.commit()
            
            logger.info(f"Current state in the circle: {current_state}")
            # 7. Find next state
            next_state = get_next_state(db, scenario_id, current_state.id, episode_id, role_users[0][1])
            
            # If no next state, we've reached the end
            if not next_state:
                logger.info(f"Episode {episode_id} completed successfully")
                episode.status = EpisodeStatus.COMPLETED
                db.commit()
                break
            
            # Move to next state
            current_state = next_state
        
        return episode_id
        
    except Exception as e:
        logger.error(f"Failed to execute scenario: {str(e)}")
        return None