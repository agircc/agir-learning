#!/usr/bin/env python3
"""
Demo script showing the performance and behavior differences between assignment strategies.

This script simulates the assignment process and shows timing and distribution metrics.
"""

import os
import sys
import time
import logging
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.assignment_config import (
    set_assignment_config, 
    reset_assignment_tracking,
    track_user_assignment,
    get_user_assignment_count,
    get_least_assigned_users,
    should_increment_assign_count,
    increment_assign_count,
    get_assignment_stats
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_single_assignment(num_episodes, users_per_role=10):
    """
    Simulate single assignment strategy.
    In this mode, we create new users for each episode.
    """
    logger.info(f"Simulating single assignment with {num_episodes} episodes")
    
    # Reset configuration
    config = {
        'allow_multi_assign': False,
        'start_assign_count': 1
    }
    set_assignment_config(config)
    reset_assignment_tracking()
    
    start_time = time.time()
    
    # Simulate user creation for each episode
    user_assignments = defaultdict(list)
    user_counter = 1
    
    for episode in range(1, num_episodes + 1):
        # In single assignment, we'd typically create new users or reuse from other scenarios
        # For demo purposes, we simulate creating new users
        for role_id in [1, 2, 3]:  # 3 roles
            user_id = user_counter
            user_assignments[role_id].append(user_id)
            user_counter += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate statistics
    total_users = user_counter - 1
    unique_users_per_role = {role_id: len(users) for role_id, users in user_assignments.items()}
    
    logger.info(f"Single assignment completed in {duration:.4f} seconds")
    logger.info(f"Total users created: {total_users}")
    logger.info(f"Users per role: {unique_users_per_role}")
    logger.info(f"Average users per role: {sum(unique_users_per_role.values()) / len(unique_users_per_role):.1f}")
    
    return {
        'duration': duration,
        'total_users': total_users,
        'users_per_role': unique_users_per_role,
        'assignment_distribution': {}
    }

def simulate_multi_assignment(num_episodes, users_per_role=3, start_assign_count=1):
    """
    Simulate multi assignment strategy with load balancing.
    """
    logger.info(f"Simulating multi assignment with {num_episodes} episodes, {users_per_role} users per role")
    
    # Reset configuration
    config = {
        'allow_multi_assign': True,
        'start_assign_count': start_assign_count
    }
    set_assignment_config(config)
    reset_assignment_tracking()
    
    start_time = time.time()
    
    # Pre-create users for each role
    role_users = {}
    for role_id in [1, 2, 3]:  # 3 roles
        role_users[role_id] = list(range(role_id * 100 + 1, role_id * 100 + users_per_role + 1))
    
    assignment_distribution = defaultdict(lambda: defaultdict(int))
    
    for episode in range(1, num_episodes + 1):
        for role_id in [1, 2, 3]:
            # Get least assigned users
            available_users = role_users[role_id]
            least_assigned = get_least_assigned_users(role_id, available_users)
            
            # Select user (first from least assigned for consistency)
            selected_user = least_assigned[0]
            
            # Track assignment
            track_user_assignment(role_id, selected_user)
            assignment_distribution[role_id][selected_user] += 1
            
            # Check if we need to increment threshold
            if should_increment_assign_count(role_id, available_users):
                increment_assign_count()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate statistics
    total_users = sum(len(users) for users in role_users.values())
    assignments_per_user = {}
    
    for role_id in [1, 2, 3]:
        assignments_per_user[role_id] = {}
        for user_id in role_users[role_id]:
            count = get_user_assignment_count(role_id, user_id)
            assignments_per_user[role_id][user_id] = count
    
    logger.info(f"Multi assignment completed in {duration:.4f} seconds")
    logger.info(f"Total users used: {total_users}")
    logger.info(f"Users per role: {users_per_role}")
    
    # Show assignment distribution
    for role_id in [1, 2, 3]:
        counts = [assignments_per_user[role_id][uid] for uid in role_users[role_id]]
        logger.info(f"Role {role_id} distribution: {counts} (avg: {sum(counts)/len(counts):.1f})")
    
    final_stats = get_assignment_stats()
    logger.info(f"Final assignment count threshold: {final_stats['config']['current_assign_count']}")
    
    return {
        'duration': duration,
        'total_users': total_users,
        'users_per_role': {role_id: users_per_role for role_id in [1, 2, 3]},
        'assignment_distribution': dict(assignment_distribution),
        'final_threshold': final_stats['config']['current_assign_count']
    }

def compare_strategies():
    """
    Compare both strategies with different episode counts.
    """
    logger.info("=" * 80)
    logger.info("USER ASSIGNMENT STRATEGY PERFORMANCE COMPARISON")
    logger.info("=" * 80)
    
    test_cases = [
        {'episodes': 10, 'users_per_role': 3},
        {'episodes': 50, 'users_per_role': 5},
        {'episodes': 100, 'users_per_role': 4}
    ]
    
    for i, case in enumerate(test_cases, 1):
        episodes = case['episodes']
        users_per_role = case['users_per_role']
        
        logger.info(f"\nTest Case {i}: {episodes} episodes")
        logger.info("-" * 40)
        
        # Test single assignment
        logger.info("\n--- Single Assignment Strategy ---")
        single_result = simulate_single_assignment(episodes, users_per_role)
        
        # Test multi assignment
        logger.info("\n--- Multi Assignment Strategy ---")
        multi_result = simulate_multi_assignment(episodes, users_per_role)
        
        # Compare results
        logger.info("\n--- Comparison ---")
        logger.info(f"User count - Single: {single_result['total_users']}, Multi: {multi_result['total_users']}")
        logger.info(f"Performance - Single: {single_result['duration']:.4f}s, Multi: {multi_result['duration']:.4f}s")
        
        user_reduction = ((single_result['total_users'] - multi_result['total_users']) / 
                         single_result['total_users']) * 100
        logger.info(f"User reduction with multi-assignment: {user_reduction:.1f}%")
        
        if 'final_threshold' in multi_result:
            logger.info(f"Final assignment threshold: {multi_result['final_threshold']}")
        
        logger.info("-" * 40)

def demonstrate_load_balancing():
    """
    Demonstrate load balancing with detailed step-by-step output.
    """
    logger.info("\n" + "=" * 80)
    logger.info("LOAD BALANCING DEMONSTRATION")
    logger.info("=" * 80)
    
    # Setup
    config = {
        'allow_multi_assign': True,
        'start_assign_count': 1
    }
    set_assignment_config(config)
    reset_assignment_tracking()
    
    role_id = 1
    users = [101, 102, 103]  # 3 users
    
    logger.info(f"Role {role_id} with users: {users}")
    logger.info("Demonstrating perfect load balancing...")
    logger.info("")
    
    for episode in range(1, 13):  # 12 episodes
        # Get least assigned users
        least_assigned = get_least_assigned_users(role_id, users)
        selected_user = least_assigned[0]
        
        # Track assignment
        track_user_assignment(role_id, selected_user)
        new_count = get_user_assignment_count(role_id, selected_user)
        
        # Show current state
        all_counts = [get_user_assignment_count(role_id, uid) for uid in users]
        threshold = get_assignment_stats()['config']['current_assign_count']
        
        logger.info(f"Episode {episode:2d}: User {selected_user} -> {new_count} assignments "
                   f"| Distribution: {dict(zip(users, all_counts))} | Threshold: {threshold}")
        
        # Check threshold increment
        if should_increment_assign_count(role_id, users):
            increment_assign_count()
            new_threshold = get_assignment_stats()['config']['current_assign_count']
            logger.info(f"          Threshold incremented to {new_threshold}")

def main():
    """Main demo function."""
    try:
        compare_strategies()
        demonstrate_load_balancing()
        
        logger.info("\n" + "=" * 80)
        logger.info("DEMONSTRATION COMPLETED")
        logger.info("=" * 80)
        logger.info("\nKey Benefits of Multi-Assignment Strategy:")
        logger.info("1. Significantly reduces the number of users needed")
        logger.info("2. Provides perfect load balancing across users")
        logger.info("3. Maintains user context and learning across episodes")
        logger.info("4. Automatic threshold management for fair distribution")
        logger.info("5. Configurable starting points for different use cases")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 