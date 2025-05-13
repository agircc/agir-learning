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
from agir_db.models.scenario import Scenario, State, StateTransition, StateRole
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step
from agir_db.models.agent_assignment import AgentAssignment
from agir_db.models.chat_message import ChatMessage
from agir_db.schemas.scenario import StateInDBBase

from src.construction.create_agent_assignment import create_agent_assignment

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
    def _get_initial_state(db: Session, scenario_id: int) -> Optional[State]:
        """
        Get the initial state of a scenario.
        
        Args:
            db: Database session
            scenario_id: ID of the scenario
            
        Returns:
            Optional[State]: Initial state if found, None otherwise
        """
        try:
            # Get all states in the scenario
            all_states = db.query(State).filter(State.scenario_id == scenario_id).all()
            if not all_states:
                logger.error(f"No states found for scenario: {scenario_id}")
                return None
            
            # Get all 'to' states in transitions
            to_states = db.query(StateTransition.to_state_id).filter(
                StateTransition.scenario_id == scenario_id
            ).all()
            to_state_ids = {t[0] for t in to_states}
            
            # Find states that are not 'to' states in any transition
            # These are potential starting states
            for state in all_states:
                if state.id not in to_state_ids:
                    return StateInDBBase.model_validate(state)
            
            # If no clear starting state, return the first state
            logger.warning(f"No clear starting state found for scenario: {scenario_id}, using first state")
            return all_states[0]
            
        except Exception as e:
            logger.error(f"Failed to get initial state: {str(e)}")
            return None
    
    @staticmethod
    def _get_state_roles(db: Session, state_id: int) -> List[AgentRole]:
        """
        Get all roles associated with a state.
        
        Args:
            db: Database session
            state_id: ID of the state
            
        Returns:
            List[AgentRole]: Roles associated with the state
        """
        try:
            # Get all role IDs for this state from the StateRole table
            state_roles = db.query(StateRole).filter(
                StateRole.state_id == state_id
            ).all()
            
            if not state_roles:
                logger.error(f"No roles found for state: {state_id}")
                return []
            
            # Get the actual AgentRole objects
            roles = []
            for state_role in state_roles:
                role = db.query(AgentRole).filter(
                    AgentRole.id == state_role.agent_role_id
                ).first()
                
                if role:
                    roles.append(role)
            
            return roles
            
        except Exception as e:
            logger.error(f"Failed to get state roles: {str(e)}")
            return []
    
    @staticmethod
    def _get_or_create_agent_assignment(db: Session, role_id: int, episode_id: int) -> Optional[User]:
        """
        Get or create a user for a role in an episode.
        
        Args:
            db: Database session
            role_id: ID of the role
            episode_id: ID of the episode
            
        Returns:
            Optional[User]: User if found or created, None otherwise
        """
        try:
            # Try to find existing agent assignment for this episode
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                logger.error(f"Episode not found: {episode_id}")
                return None
            
            role = db.query(AgentRole).filter(AgentRole.id == role_id).first()
            if not role:
                logger.error(f"Role not found: {role_id}")
                return None
            
            # Check if agent assignment exists
            agent_assignment = db.query(AgentAssignment).filter(
                AgentAssignment.role_id == role_id
            ).first()
            
            if agent_assignment:
                # User exists for this role
                user = db.query(User).filter(User.id == agent_assignment.user_id).first()
                if user:
                    logger.info(f"Found existing user {user.username} for role {role.name}")
                    return user
            
            # Create a new user for this role
            logger.info(f"Creating new user for role {role.name} in scenario {episode.scenario_id}")
            user = create_agent_assignment(
                db, 
                role.name, 
                episode.scenario_id, 
                username=f"{role.name}_{episode.id}",
                model=getattr(role, 'model', None)
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get or create agent assignment: {str(e)}")
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

    

    
 
def execute_scenario(scenario_id: int, initiator_id: int) -> Optional[int]:
    """
    Execute a scenario from start to finish.
    
    Args:
        scenario_id: ID of the scenario
        initiator_id: ID of the initiator
        
    Returns:
        Optional[int]: ID of the episode if successful, None otherwise
    """
    try:
        logger.info(f"Step 0")
        db = next(get_db())
        logger.info(f"Step 1")
        # 1. Create episode
        episode_id = ScenarioManager._create_episode(db, scenario_id, initiator_id)
        if not episode_id:
            return None
        
        logger.info(f"Step 2")
        # 2. Get initial state and create first step
        current_state = ScenarioManager._get_initial_state(db, scenario_id)
        if not current_state:
            logger.error(f"No initial state found for scenario: {scenario_id}")
            return None
        
        logger.info(f"Current state: {current_state}")


        logger.info(f"Step 3")
        # Initialize episode with current state
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        episode.current_state_id = current_state.id
        db.commit()
        
        # Keep track of all steps
        all_steps = []
        
        # Continue processing states until we reach the end
        while current_state:
            # 3. Get all roles associated with the state
            roles = ScenarioManager._get_state_roles(db, current_state.id)
            if not roles:
                logger.error(f"Failed to get roles for state: {current_state.id}")
                return None
            
            # 4. Get or create users for each role
            role_users = []
            for role in roles:
                user = ScenarioManager._get_or_create_agent_assignment(db, role.id, episode_id)
                if not user:
                    logger.error(f"Failed to get or create user for role: {role.id}")
                    return None
                role_users.append((role, user))
            
            # 5. If there's only one role, generate a simple response
            if len(role_users) == 1:
                role, user = role_users[0]
                response = generate_llm_response(db, current_state, role, user, all_steps)
                
                # Create step with generated data
                step_id = ScenarioManager._create_step(
                    db, episode_id, current_state.id, user.id, response
                )
                
                if not step_id:
                    logger.error(f"Failed to create step for state: {current_state.id}")
                    return None
                
                # Add step to history
                step = db.query(Step).filter(Step.id == step_id).first()
                all_steps.append(step)
            
            # 6. If there are multiple roles, conduct a multi-turn conversation
            else:
                # First create a step for the conversation
                step_id = ScenarioManager._create_step(
                    db, episode_id, current_state.id, role_users[0][1].id,
                    f"Multi-role conversation for state: {current_state.name}"
                )
                
                if not step_id:
                    logger.error(f"Failed to create step for state: {current_state.id}")
                    return None
                
                # Add step to history
                step = db.query(Step).filter(Step.id == step_id).first()
                all_steps.append(step)
                
                # Create conversation linked to the step
                conversation = create_conversation(db, current_state, episode_id, role_users, step_id)
                if not conversation:
                    logger.error(f"Failed to create conversation for state: {current_state.id}")
                    return None
                
                # Conduct multi-turn conversation
                conversation_result = conduct_multi_turn_conversation(
                    db, conversation, current_state, role_users
                )
                
                # Update the step with conversation results
                step.generated_text = conversation_result
                db.commit()
                
                # Also update episode status to mark this state as processed
                episode = db.query(Episode).filter(Episode.id == episode_id).first()
                if episode:
                    episode.last_updated = time.time()
                    db.commit()
            
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