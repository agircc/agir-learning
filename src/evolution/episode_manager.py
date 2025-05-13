"""
Episode Manager - handles creation and execution of scenarios
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
from agir_db.models.agent_role import AgentRole
from agir_db.models.scenario import Scenario, State, StateTransition
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step

from ..models.process import Process as YamlProcess

logger = logging.getLogger(__name__)


class EpisodeManager:
    """
    Manages the creation and execution of scenarios.
    """        
    
    
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
                    return state
            
            # If no clear starting state, return the first state
            logger.warning(f"No clear starting state found for scenario: {scenario_id}, using first state")
            return all_states[0]
            
        except Exception as e:
            logger.error(f"Failed to get initial state: {str(e)}")
            return None
    
    @staticmethod
    def _create_step(
        db: Session, 
        episode_id: int, 
        state_id: int, 
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Create a step.
        
        Args:
            db: Database session
            episode_id: ID of the episode
            state_id: ID of the state
            user_id: ID of the user (optional)
            
        Returns:
            Optional[int]: ID of the step if successful, None otherwise
        """
        try:
            step = Step(
                episode_id=episode_id,
                state_id=state_id,
                user_id=user_id,
                action="process"  # Default action
            )
            
            db.add(step)
            db.commit()
            logger.info(f"Created step with ID: {step.id}")
            
            return step.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create step: {str(e)}")
            return None
    
    @staticmethod
    def advance_scenario(episode_id: int, next_state_name: Optional[str] = None) -> Optional[int]:
        """
        Advance an episode to the next state.
        
        Args:
            episode_id: ID of the episode
            next_state_name: Name of the next state (optional)
            
        Returns:
            Optional[int]: ID of the new step if successful, None otherwise
        """
        try:
            db = next(get_db())
            
            # Get episode
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                logger.error(f"Episode not found: {episode_id}")
                return None
            
            # Get current state
            current_state_id = episode.current_state_id
            if not current_state_id:
                logger.error(f"Current state not set for episode: {episode_id}")
                return None
            
            # Find next state
            next_state_id = None
            
            if next_state_name:
                # If next state name is specified, find it by name
                next_state = db.query(State).filter(
                    State.scenario_id == episode.scenario_id,
                    State.name == next_state_name
                ).first()
                
                if next_state:
                    next_state_id = next_state.id
            
            if not next_state_id:
                # Find next state from transitions
                transition = db.query(StateTransition).filter(
                    StateTransition.scenario_id == episode.scenario_id,
                    StateTransition.from_state_id == current_state_id
                ).first()
                
                if transition:
                    next_state_id = transition.to_state_id
            
            if not next_state_id:
                logger.error(f"No next state found for episode: {episode_id}")
                return None
            
            # Create step for next state
            step_id = EpisodeManager._create_step(
                db, episode_id, next_state_id, episode.initiator_id
            )
            
            if not step_id:
                return None
            
            # Update episode with current state
            episode.current_state_id = next_state_id
            db.commit()
            
            logger.info(f"Advanced episode {episode_id} to state {next_state_id}")
            
            return step_id
            
        except Exception as e:
            logger.error(f"Failed to advance scenario: {str(e)}")
            return None
    
    @staticmethod
    def complete_episode(episode_id: int, success: bool = True) -> bool:
        """
        Complete an episode.
        
        Args:
            episode_id: ID of the episode
            success: Whether the episode completed successfully
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = next(get_db())
            
            # Get episode
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                logger.error(f"Episode not found: {episode_id}")
                return False
            
            # Update episode status
            episode.status = EpisodeStatus.COMPLETED if success else EpisodeStatus.FAILED
            db.commit()
            
            logger.info(f"Completed episode {episode_id} with status: {episode.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete episode: {str(e)}")
            return False
    
    @staticmethod
    def get_scenario(scenario_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a scenario by ID from the database.
        
        Args:
            scenario_id: ID of the scenario
            
        Returns:
            Scenario data as a dictionary if found, None otherwise
        """
        try:
            db = next(get_db())
            
            # Get the scenario from the database
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            
            if not scenario:
                logger.error(f"Scenario not found with ID: {scenario_id}")
                return None
                
            # Get episode for config
            episode = db.query(Episode).filter(
                Episode.scenario_id == scenario_id
            ).order_by(Episode.created_at.desc()).first()
                
            # Create a dictionary with scenario data
            scenario_data = {
                "id": scenario.id,
                "name": scenario.name,
                "description": scenario.description,
                "config": episode.config if episode else None
            }
            
            # Add yaml-compatible attributes for compatibility with evolution engine
            scenario_data["learner"] = {}
            scenario_data["roles"] = []
            scenario_data["states"] = []
            scenario_data["transitions"] = []
            scenario_data["evolution"] = {}
            
            # If we have config, parse and add it
            if scenario_data["config"]:
                try:
                    if isinstance(scenario_data["config"], str):
                        config = json.loads(scenario_data["config"])
                    else:
                        config = scenario_data["config"]
                        
                    # Add config details to the scenario data
                    if "learner" in config:
                        scenario_data["learner"] = config["learner"]
                    if "roles" in config:
                        scenario_data["roles"] = config["roles"]
                    if "states" in config:
                        scenario_data["states"] = config["states"]
                    if "transitions" in config:
                        scenario_data["transitions"] = config["transitions"]
                    if "evolution" in config:
                        scenario_data["evolution"] = config["evolution"]
                except Exception as e:
                    logger.error(f"Failed to parse scenario config: {str(e)}")
            
            return scenario_data
            
        except Exception as e:
            logger.error(f"Error getting scenario {scenario_id}: {str(e)}")
            return None 