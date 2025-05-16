import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Union
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.agent_assignment import AgentAssignment
from src.common.data_store import get_learner, get_scenario, set_learner
import random
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Lists of common first and last names for more realistic user generation
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth",
    "Lisa", "Nancy", "Betty", "Sandra", "Margaret", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson",
    "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King",
    "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter"
]

def generate_realistic_user(role, scenario_id):
    """
    Generate a realistic user with unique username based on role and scenario_id
    
    Args:
        role: The role of the user
        scenario_id: The scenario ID
        
    Returns:
        tuple: (username, first_name, last_name)
    """
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    
    # Create a unique identifier using timestamp and a random number
    unique_id = f"{int(time.time() * 1000) % 100000:05d}{random.randint(100, 999)}"
    
    # Create username: combine parts of first and last name with unique ID
    username = f"{first_name.lower()[:4]}_{last_name.lower()[:4]}_{unique_id}"
    
    return username, first_name, last_name

def create_agent_assignment(db: Session, role: str, scenario_id: Any, username: Optional[str] = None, model: Optional[str] = None) -> User:
    """
    Create a user for a specific role and scenario and associate them in agent_assignments.
    
    Args:
        db: Database session
        role: Role name
        scenario_id: ID of the scenario
        username: Username (optional, will be generated if None)
        model: LLM model to use (optional)
        
    Returns:
        User: Created or found user
    """
    try:
        scenario = get_scenario()
        
        # Check if this is the learner role
        logger.info(f"Scenario learner role: {scenario.learner_role}")
        
        if scenario.learner_role == role:
            # Use existing learner
            learner = get_learner()
            if learner:
                logger.info(f"Using existing learner: {learner.username}")
                user = db.query(User).filter(User.id == learner.id).first()
                if user:
                    return user
        
        # Generate user information
        if not username:
            # Generate a new username and name information
            username, first_name, last_name = generate_realistic_user(role, scenario_id)
        else:
            # Username was provided, assign default names
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
        
        # Find or create user
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            # Create new user
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@agir.ai",
                is_active=True
            )
            
            # Set model if provided
            if model and hasattr(user, 'llm_model'):
                user.llm_model = model
                
            db.add(user)
            db.flush()  # Get ID without committing
            
            logger.info(f"Created new user: {username} with ID: {user.id}")
        
        # Find the agent role
        agent_role = db.query(AgentRole).filter(
            AgentRole.scenario_id == scenario_id,
            AgentRole.name == role
        ).first()
        
        if not agent_role:
            logger.warning(f"Role '{role}' not found for scenario {scenario_id}. Creating a default role.")
            
            agent_role = AgentRole(
                scenario_id=scenario_id,
                name=role,
                description=f"Auto-created role for {role}"
            )
            
            db.add(agent_role)
            db.flush()
        
        # Create role-user association if it doesn't exist
        existing_assignment = db.query(AgentAssignment).filter(
            AgentAssignment.role_id == agent_role.id,
            AgentAssignment.user_id == user.id
        ).first()
        
        if not existing_assignment:
            agent_assignment = AgentAssignment(
                role_id=agent_role.id,
                user_id=user.id
            )
            
            db.add(agent_assignment)
            logger.info(f"Created agent assignment for user {user.username} with role {role}")
        
        db.commit()
        
        if scenario.learner_role == role:
            # Store as learner
            set_learner(user)
        
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create agent assignment: {str(e)}")
        raise
