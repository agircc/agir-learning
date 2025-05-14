"""
Run evolution process
"""

import logging
import yaml
import os
import uuid
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.state import State
from src.evolution.episode_manager import EpisodeManager

logger = logging.getLogger(__name__)


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
        
        # First, look for the scenario
        logger.info(f"Looking up scenario with ID: {scenario_id}")
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        
        if not scenario:
            logger.error(f"No scenario found with ID: {scenario_id}")
            return False
        
        logger.info(f"Found scenario: {scenario.name}")
        
        # Find the start node
        start_node = None
        for node in scenario.states:
            if node.is_start:
                start_node = node
                break
        
        if not start_node:
            logger.error(f"No start node found for scenario: {scenario.name}")
            return False
        
        logger.info(f"Found start node: {start_node.name}")
        
        # Run the requested number of episodes
        logger.info(f"Running {num_episodes} episodes for scenario: {scenario.name}")
        
        for i in range(num_episodes):
            logger.info(f"Starting episode {i+1} of {num_episodes}")
            
            # Create an episode manager
            episode_manager = EpisodeManager(scenario_id)
            
            # Start the process from the beginning
            episode = episode_manager.create_episode()
            
            if not episode:
                logger.error(f"Failed to create episode for scenario: {scenario.name}")
                success = False
                continue
                
            logger.info(f"Created episode with ID: {episode.id}")
            
            # Execute the process until completion or error
            result = episode_manager.execute_episode(start_node.id)
            
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