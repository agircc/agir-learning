import logging
import sys
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.episode import Episode
from agir_db.models.agent_assignment import AgentAssignment
from agir_db.models.scenario import Scenario
from src.evolution.scenario_manager.create_agent_assignment import create_agent_assignment
from src.evolution.store import get_episode
from src.common.data_store import get_learner, get_scenario
from src.evolution.assignment_config import (
    is_multi_assign_enabled, 
    get_current_assign_count,
    track_user_assignment,
    get_least_assigned_users,
    should_increment_assign_count,
    increment_assign_count,
    get_user_assignment_count
)

logger = logging.getLogger(__name__)

def d_get_or_create_user_for_state(db: Session, role_id: int) -> Optional[User]:
    """
    Get or create a user for a role in an episode with support for multi-assignment strategy.
    
    Args:
        db: Database session
        role_id: ID of the role
        
    Returns:
        Optional[User]: User if found or created, None otherwise
    """
    try:
        episode = get_episode()
        
        if not episode:
            logger.error(f"Episode not found")
            sys.exit(1)
            
        agentRole = db.query(AgentRole).filter(AgentRole.id == role_id).first()
        if not agentRole:
            logger.error(f"Role not found: {role_id}")
            sys.exit(1)
        
        # Check if agent assignment already exists for this episode
        agent_assignment = db.query(AgentAssignment).filter(
            AgentAssignment.role_id == role_id,
            AgentAssignment.episode_id == episode.id
        ).first()
        
        if agent_assignment:
            # User already assigned to this episode
            user = db.query(User).filter(User.id == agent_assignment.user_id).first()
            if user:
                logger.info(f"Found existing user {user.username} for role {agentRole.name}")
                return user
        
        # No existing assignment for this episode, need to find or create user
        if not is_multi_assign_enabled():
            # Original single-assignment logic
            return _handle_single_assignment(db, role_id, episode, agentRole)
        else:
            # New multi-assignment logic with load balancing
            return _handle_multi_assignment(db, role_id, episode, agentRole)
        
    except Exception as e:
        logger.error(f"Failed to get or create agent assignment: {str(e)}")
        return None

def _handle_single_assignment(db: Session, role_id: int, episode: Episode, agentRole: AgentRole) -> Optional[User]:
    """
    Handle user assignment with single-assignment strategy (original logic).
    """
    # Find users who have been assigned to this role in other scenarios
    # First, get all users assigned to this role
    role_assignments = db.query(AgentAssignment).filter(
        AgentAssignment.role_id == role_id
    ).all()
    
    # Find episodes with the current scenario
    episodes_in_scenario = db.query(Episode).filter(
        Episode.scenario_id == episode.scenario_id
    ).all()
    scenario_episode_ids = [ep.id for ep in episodes_in_scenario]
    
    # Find users who have been assigned to this role but not in the current scenario
    for assignment in role_assignments:
        # Check if this user has been assigned to any episode in the current scenario
        user_scenario_assignments = db.query(AgentAssignment).filter(
            AgentAssignment.user_id == assignment.user_id,
            AgentAssignment.episode_id.in_(scenario_episode_ids)
        ).first()
        
        # If user hasn't been assigned to this scenario yet, we can reuse them
        if not user_scenario_assignments:
            user = db.query(User).filter(User.id == assignment.user_id).first()
            if user:
                logger.info(f"Reusing existing user {user.username} for role {agentRole.name} in new scenario")
                # Create new assignment for this episode
                new_assignment = AgentAssignment(
                    user_id=user.id,
                    role_id=role_id,
                    episode_id=episode.id
                )
                db.add(new_assignment)
                db.commit()
                return user
    
    # If no existing user can be reused, create a new user for this role
    logger.info(f"Creating new user for role {agentRole.name} in scenario {episode.scenario_id}")
    user = create_agent_assignment(
        db, 
        agentRole.name, 
        episode.scenario_id, 
        username=f"{agentRole.name}_{episode.id}",
        model=getattr(agentRole, 'model', None)
    )
    
    return user

def _handle_multi_assignment(db: Session, role_id: int, episode: Episode, agentRole: AgentRole) -> Optional[User]:
    """
    Handle user assignment with multi-assignment strategy and load balancing.
    Only uses existing users from the database, never creates new users.
    Handles learner role specially - learner role can only use learner user,
    other roles cannot use learner user.
    Ensures that within the same episode, a user is not assigned to multiple different roles.
    """
    # Get scenario and learner role information
    scenario = get_scenario()
    learner_role = None
    if scenario:
        logger.info(f"Scenario learner role: {scenario.learner_role}")
        learner_role = scenario.learner_role
    else:
        logger.warning("Scenario not found in data store, proceeding without learner role check")
    
    # Check if current role is the learner role
    if learner_role and learner_role == agentRole.name:
        # This is the learner role - use existing learner
        learner = get_learner()
        if learner:
            logger.info(f"Using existing learner: {learner.username} for learner role {agentRole.name} (no assignment created)")
            user = db.query(User).filter(User.id == learner.id).first()
            if user:
                # For learner role, return user directly without creating assignment
                return user
        else:
            logger.error("No learner found and this is learner role")
            return None
    
    # This is not the learner role - get all users except learner
    all_users = db.query(User).all()
    
    if not all_users:
        # No users exist in the database at all
        logger.error(f"No users exist in database for role {agentRole.name}")
        return None
    
    # Filter out learner user if it exists
    available_users = []
    learner = get_learner()
    learner_user_id = learner.id if learner else None
    
    # TODO: Optimize this implementation by using environment variables to control excluded usernames
    # instead of hardcoding them here. This would make the system more configurable and maintainable.
    excluded_usernames = {'emotion_master', 'dentist_001'}
    
    for user in all_users:
        if learner_user_id and user.id == learner_user_id:
            # Skip learner user for non-learner roles
            continue
        if user.username in excluded_usernames:
            # Skip specifically excluded users
            logger.info(f"Skipping excluded user: {user.username}")
            continue
        available_users.append(user)
    
    if not available_users:
        logger.error(f"No available users for non-learner role {agentRole.name} (learner user excluded)")
        return None
    
    # Get users already assigned to OTHER roles in this episode
    # to avoid assigning the same user to multiple roles in the same episode
    existing_assignments_in_episode = db.query(AgentAssignment).filter(
        AgentAssignment.episode_id == episode.id,
        AgentAssignment.role_id != role_id  # Exclude current role (different roles only)
    ).all()
    
    users_already_assigned_in_episode = set(assignment.user_id for assignment in existing_assignments_in_episode)
    
    if users_already_assigned_in_episode:
        logger.info(f"Found {len(users_already_assigned_in_episode)} users already assigned to other roles in episode {episode.id}")
    
    # Filter out users already assigned to other roles in this episode
    available_users_for_episode = []
    for user in available_users:
        if user.id not in users_already_assigned_in_episode:
            available_users_for_episode.append(user)
    
    if not available_users_for_episode:
        logger.warning(f"No available users for role {agentRole.name} - all users are already assigned to other roles in episode {episode.id}")
        # Fallback: use all available users (allow same user for multiple roles as last resort)
        available_users_for_episode = available_users
        logger.warning(f"Fallback: allowing same user for multiple roles in episode {episode.id}")
    
    # Get user IDs from available users for this episode
    user_ids = [user.id for user in available_users_for_episode]
    
    logger.info(f"Found {len(user_ids)} available users for non-learner role {agentRole.name} (learner excluded, episode conflicts excluded)")
    
    # Get users with the least assignments for this specific role
    least_assigned_user_ids = get_least_assigned_users(role_id, user_ids)
    
    # Check if we need to increment the assignment count
    if should_increment_assign_count(role_id, user_ids):
        increment_assign_count()
        logger.info(f"All users for role {agentRole.name} have reached current threshold, incremented assignment count")
    
    # Choose the first user from the least assigned list
    selected_user_id = least_assigned_user_ids[0]
    user = db.query(User).filter(User.id == selected_user_id).first()
    
    if user:
        logger.info(f"Selected existing user {user.username} for non-learner role {agentRole.name} (assignments: {get_user_assignment_count(role_id, user.id)}, episode: {episode.id})")
        
        # Create new assignment for this episode
        new_assignment = AgentAssignment(
            user_id=user.id,
            role_id=role_id,
            episode_id=episode.id
        )
        db.add(new_assignment)
        db.commit()
        
        # Track this assignment
        track_user_assignment(role_id, user.id)
        
        return user
    else:
        logger.error(f"User {selected_user_id} not found")
        return None