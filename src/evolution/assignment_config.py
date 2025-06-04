"""
Assignment configuration and tracking module for managing user assignments to episodes.

This module provides global configuration and tracking for user assignment strategies,
supporting both single-assignment and multi-assignment modes with intelligent
load balancing.
"""

import logging
from typing import Dict, Any, Optional
from collections import defaultdict
from sqlalchemy import func

logger = logging.getLogger(__name__)

# Global configuration
_assignment_config = {
    'allow_multi_assign': False,
    'start_assign_count': 1,
    'current_assign_count': 1
}

# Global tracking for user assignment counts
# Structure: {role_id: {user_id: current_assignment_count}}
_user_assignment_counts = defaultdict(lambda: defaultdict(int))

def set_assignment_config(config: Dict[str, Any]) -> None:
    """
    Set the global assignment configuration.
    
    Args:
        config: Dictionary containing assignment configuration
    """
    global _assignment_config
    
    _assignment_config.update(config)
    _assignment_config['current_assign_count'] = config.get('start_assign_count', 1)
    
    logger.info(f"Assignment configuration updated: {_assignment_config}")

def get_assignment_config() -> Dict[str, Any]:
    """
    Get the current assignment configuration.
    
    Returns:
        Dictionary containing current assignment configuration
    """
    return _assignment_config.copy()

def is_multi_assign_enabled() -> bool:
    """
    Check if multi-assignment is enabled.
    
    Returns:
        True if multi-assignment is enabled, False otherwise
    """
    return _assignment_config.get('allow_multi_assign', False)

def get_current_assign_count() -> int:
    """
    Get the current assignment count threshold.
    
    Returns:
        Current assignment count threshold
    """
    return _assignment_config.get('current_assign_count', 1)

def increment_assign_count() -> None:
    """
    Increment the global assignment count threshold.
    This is called when all users for a role have reached the current threshold.
    """
    global _assignment_config
    _assignment_config['current_assign_count'] += 1
    logger.info(f"Assignment count incremented to {_assignment_config['current_assign_count']}")

def track_user_assignment(role_id: int, user_id: int) -> None:
    """
    Track a user assignment for a specific role.
    
    Args:
        role_id: ID of the role
        user_id: ID of the user
    """
    global _user_assignment_counts
    _user_assignment_counts[role_id][user_id] += 1
    
    current_count = _user_assignment_counts[role_id][user_id]
    logger.debug(f"User {user_id} assigned to role {role_id}, total assignments: {current_count}")

def get_user_assignment_count(role_id: int, user_id: int) -> int:
    """
    Get the current assignment count for a user in a specific role.
    
    Args:
        role_id: ID of the role
        user_id: ID of the user
        
    Returns:
        Current assignment count for the user in the role
    """
    return _user_assignment_counts[role_id].get(user_id, 0)

def get_least_assigned_users(role_id: int, user_ids: list) -> list:
    """
    Get users with the least number of assignments for a specific role.
    
    Args:
        role_id: ID of the role
        user_ids: List of user IDs to consider
        
    Returns:
        List of user IDs with the least assignments, sorted by assignment count
    """
    if not user_ids:
        return []
    
    # Get assignment counts for all users
    user_counts = [(user_id, get_user_assignment_count(role_id, user_id)) for user_id in user_ids]
    
    # Sort by assignment count (ascending)
    user_counts.sort(key=lambda x: x[1])
    
    # Find the minimum assignment count
    min_count = user_counts[0][1]
    
    # Return all users with the minimum count
    least_assigned = [user_id for user_id, count in user_counts if count == min_count]
    
    logger.debug(f"Least assigned users for role {role_id}: {least_assigned} (count: {min_count})")
    return least_assigned

def should_increment_assign_count(role_id: int, available_users: list) -> bool:
    """
    Check if all available users have reached the current assignment threshold.
    
    Args:
        role_id: ID of the role
        available_users: List of available user IDs
        
    Returns:
        True if assignment count should be incremented, False otherwise
    """
    if not available_users:
        return False
    
    current_threshold = get_current_assign_count()
    
    # Check if all users have reached the current threshold
    all_reached_threshold = all(
        get_user_assignment_count(role_id, user_id) >= current_threshold 
        for user_id in available_users
    )
    
    if all_reached_threshold:
        logger.info(f"All users for role {role_id} have reached threshold {current_threshold}")
        return True
    
    return False

def reset_assignment_tracking() -> None:
    """
    Reset all assignment tracking data.
    This should be called when starting a new scenario or when needed.
    """
    global _user_assignment_counts
    _user_assignment_counts.clear()
    logger.info("Assignment tracking data reset")

def get_assignment_stats() -> Dict[str, Any]:
    """
    Get current assignment statistics.
    
    Returns:
        Dictionary containing assignment statistics
    """
    stats = {
        'config': get_assignment_config(),
        'role_assignments': dict(_user_assignment_counts)
    }
    return stats

def initialize_assignment_counts_from_db(db, scenario_id: Optional[int] = None) -> None:
    """
    Initialize assignment counts from existing database records.
    This should be called when starting a scenario to ensure tracking is consistent
    with existing assignments.
    
    Args:
        db: Database session
        scenario_id: Optional scenario ID to limit initialization to specific scenario
    """
    from agir_db.models.agent_assignment import AgentAssignment
    from agir_db.models.episode import Episode
    
    global _user_assignment_counts
    
    try:
        # Query to get assignment counts per role and user
        query = db.query(AgentAssignment.role_id, AgentAssignment.user_id, 
                        func.count(AgentAssignment.id).label('count'))
        
        if scenario_id:
            # Join with Episode to filter by scenario
            query = query.join(Episode, AgentAssignment.episode_id == Episode.id)
            query = query.filter(Episode.scenario_id == scenario_id)
        
        assignments = query.group_by(AgentAssignment.role_id, AgentAssignment.user_id).all()
        
        # Update tracking counts
        for role_id, user_id, count in assignments:
            _user_assignment_counts[role_id][user_id] = count
        
        logger.info(f"Initialized assignment counts from database: {len(assignments)} records")
        
    except Exception as e:
        logger.error(f"Failed to initialize assignment counts from database: {str(e)}")

def validate_assignment_counts(db, scenario_id: Optional[int] = None) -> bool:
    """
    Validate that tracking counts match database records.
    
    Args:
        db: Database session
        scenario_id: Optional scenario ID to limit validation to specific scenario
        
    Returns:
        True if counts match, False otherwise
    """
    from agir_db.models.agent_assignment import AgentAssignment
    from agir_db.models.episode import Episode
    
    try:
        # Get counts from database
        query = db.query(AgentAssignment.role_id, AgentAssignment.user_id, 
                        func.count(AgentAssignment.id).label('count'))
        
        if scenario_id:
            query = query.join(Episode, AgentAssignment.episode_id == Episode.id)
            query = query.filter(Episode.scenario_id == scenario_id)
        
        db_assignments = query.group_by(AgentAssignment.role_id, AgentAssignment.user_id).all()
        
        # Compare with tracking
        mismatches = []
        for role_id, user_id, db_count in db_assignments:
            tracked_count = get_user_assignment_count(role_id, user_id)
            if tracked_count != db_count:
                mismatches.append(f"Role {role_id}, User {user_id}: DB={db_count}, Tracked={tracked_count}")
        
        if mismatches:
            logger.warning(f"Assignment count mismatches found: {mismatches}")
            return False
        
        logger.debug("Assignment counts validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate assignment counts: {str(e)}")
        return False 