#!/usr/bin/env python3
"""
Test script for the new user assignment strategy.

This script demonstrates the differences between single-assignment and multi-assignment modes
and shows how the load balancing works.
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.assignment_config import (
    set_assignment_config, 
    get_assignment_config,
    is_multi_assign_enabled,
    get_current_assign_count,
    track_user_assignment,
    get_user_assignment_count,
    get_least_assigned_users,
    should_increment_assign_count,
    increment_assign_count,
    reset_assignment_tracking,
    get_assignment_stats
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_assignment_mode():
    """Test single assignment mode behavior."""
    logger.info("=== Testing Single Assignment Mode ===")
    
    # Configure for single assignment
    config = {
        'allow_multi_assign': False,
        'start_assign_count': 1
    }
    set_assignment_config(config)
    
    logger.info(f"Multi-assign enabled: {is_multi_assign_enabled()}")
    logger.info(f"Current assign count: {get_current_assign_count()}")
    
    # This mode doesn't use the tracking system much
    logger.info("Single assignment mode uses database queries for user selection")
    
def test_multi_assignment_mode():
    """Test multi assignment mode with load balancing."""
    logger.info("\n=== Testing Multi Assignment Mode ===")
    
    # Reset tracking
    reset_assignment_tracking()
    
    # Configure for multi assignment
    config = {
        'allow_multi_assign': True,
        'start_assign_count': 2  # Start with assignment count of 2
    }
    set_assignment_config(config)
    
    logger.info(f"Multi-assign enabled: {is_multi_assign_enabled()}")
    logger.info(f"Current assign count: {get_current_assign_count()}")
    
    # Simulate user assignments for role 1
    role_id = 1
    user_ids = [101, 102, 103]  # Three users
    
    logger.info(f"\nSimulating assignments for role {role_id} with users {user_ids}")
    
    # Simulate some initial assignments
    assignments = [
        (101, 2), (102, 1), (103, 2), # Round 1
        (102, 1), (101, 1), (103, 1), # Round 2 - 102 catches up
        (101, 1), (102, 1), (103, 1)  # Round 3 - all equal now
    ]
    
    for user_id, count in assignments:
        for _ in range(count):
            track_user_assignment(role_id, user_id)
        
        current_count = get_user_assignment_count(role_id, user_id)
        logger.info(f"User {user_id} now has {current_count} assignments")
    
    # Show current state
    logger.info(f"\nCurrent assignment counts:")
    for user_id in user_ids:
        count = get_user_assignment_count(role_id, user_id)
        logger.info(f"  User {user_id}: {count} assignments")
    
    # Test least assigned users selection
    least_assigned = get_least_assigned_users(role_id, user_ids)
    logger.info(f"Least assigned users: {least_assigned}")
    
    # Test threshold checking
    should_increment = should_increment_assign_count(role_id, user_ids)
    logger.info(f"Should increment assign count: {should_increment}")
    
    if should_increment:
        logger.info("All users have reached the current threshold!")
        increment_assign_count()
        logger.info(f"New assign count: {get_current_assign_count()}")
    
    # Show final stats
    stats = get_assignment_stats()
    logger.info(f"\nFinal assignment statistics:")
    logger.info(f"Config: {stats['config']}")
    logger.info(f"Role assignments: {stats['role_assignments']}")

def test_load_balancing_simulation():
    """Simulate a realistic load balancing scenario."""
    logger.info("\n=== Testing Load Balancing Simulation ===")
    
    reset_assignment_tracking()
    
    config = {
        'allow_multi_assign': True,
        'start_assign_count': 1
    }
    set_assignment_config(config)
    
    role_id = 2
    user_ids = [201, 202, 203, 204]  # Four users
    
    logger.info(f"Simulating realistic assignment pattern for role {role_id}")
    logger.info(f"Users: {user_ids}")
    
    # Simulate 20 episodes with load balancing
    for episode in range(1, 21):
        # Get least assigned users
        least_assigned = get_least_assigned_users(role_id, user_ids)
        
        # Select first user from least assigned (in real implementation, could be random)
        selected_user = least_assigned[0]
        
        # Track the assignment
        track_user_assignment(role_id, selected_user)
        
        current_count = get_user_assignment_count(role_id, selected_user)
        logger.info(f"Episode {episode:2d}: Assigned user {selected_user} (now has {current_count} assignments)")
        
        # Check if we need to increment threshold
        if should_increment_assign_count(role_id, user_ids):
            increment_assign_count()
            logger.info(f"    -> All users reached threshold, incremented to {get_current_assign_count()}")
    
    # Show final distribution
    logger.info(f"\nFinal assignment distribution:")
    for user_id in user_ids:
        count = get_user_assignment_count(role_id, user_id)
        logger.info(f"  User {user_id}: {count} assignments")
    
    total_assignments = sum(get_user_assignment_count(role_id, uid) for uid in user_ids)
    avg_assignments = total_assignments / len(user_ids)
    logger.info(f"  Average: {avg_assignments:.1f} assignments per user")

def main():
    """Main test function."""
    logger.info("Testing User Assignment Strategy Implementation")
    logger.info("=" * 60)
    
    test_single_assignment_mode()
    test_multi_assignment_mode()
    test_load_balancing_simulation()
    
    logger.info("\n" + "=" * 60)
    logger.info("Assignment strategy testing completed!")

if __name__ == "__main__":
    main() 