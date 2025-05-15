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
from agir_db.models.scenario import StateRole
from agir_db.models.agent_assignment import AgentAssignment

from src.construction.data_store import get_learner
from src.evolution.scenario_manager.create_agent_assignment import create_agent_assignment

from ..models.process import Process as YamlProcess

logger = logging.getLogger(__name__)

def create_episode(scenario_id: int) -> Optional[Episode]:
        """
        Create a new episode for the scenario.
        
        Returns:
            Optional[Episode]: Created episode if successful, None otherwise
        """
        db = None
        try:
            db = next(get_db())
            
            logger.info(f"Creating episode for scenario: {scenario_id}")

            # Get scenario
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if not scenario:
                logger.error(f"Scenario not found: {scenario_id}")
                return None
            
            learner = get_learner()            
            # Create episode
            episode = Episode(
                scenario_id=scenario_id,
                status=EpisodeStatus.RUNNING,
                initiator_id=learner.id
            )
            
            db.add(episode)
            db.commit()
            
            logger.info(f"Created episode {episode.id} for scenario {scenario_id}")
            
            return episode
            
        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create episode: {str(e)}")
            return None
        finally:
            if db:
                db.close()