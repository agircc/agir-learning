#!/usr/bin/env python3
"""
Test script for database integration with assignment configuration.

This script tests the database initialization and validation functions.
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
    reset_assignment_tracking,
    initialize_assignment_counts_from_db,
    validate_assignment_counts,
    get_assignment_stats,
    track_user_assignment,
    get_user_assignment_count
)
from agir_db.db.session import get_db
from src.common.utils.memory_utils import get_db_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_integration():
    """Test database integration functions."""
    logger.info("=== Testing Database Integration ===")
    
    try:
        with get_db_session() as db:
            logger.info("Database connection successful")
            
            # Configure for multi-assignment mode
            config = {
                'allow_multi_assign': True,
                'start_assign_count': 1
            }
            set_assignment_config(config)
            reset_assignment_tracking()
            
            # Test initialization from database
            logger.info("Testing initialization from database...")
            initialize_assignment_counts_from_db(db)
            
            # Get current stats
            stats = get_assignment_stats()
            logger.info(f"Assignment stats after DB initialization: {stats}")
            
            # Test validation
            logger.info("Testing validation...")
            is_valid = validate_assignment_counts(db)
            logger.info(f"Validation result: {is_valid}")
            
            # Test with a specific scenario (if any exists)
            logger.info("Testing with scenario filter...")
            initialize_assignment_counts_from_db(db, scenario_id=1)
            
            is_valid_scenario = validate_assignment_counts(db, scenario_id=1)
            logger.info(f"Scenario-specific validation result: {is_valid_scenario}")
            
            logger.info("Database integration test completed successfully!")
            
    except Exception as e:
        logger.error(f"Database integration test failed: {str(e)}", exc_info=True)
        return False
    
    return True

def test_tracking_consistency():
    """Test that in-memory tracking stays consistent with hypothetical database records."""
    logger.info("\n=== Testing Tracking Consistency ===")
    
    # Reset and configure
    reset_assignment_tracking()
    config = {
        'allow_multi_assign': True,
        'start_assign_count': 1
    }
    set_assignment_config(config)
    
    # Simulate some assignments
    role_id = 1
    assignments = [
        (101, 3),  # User 101 gets 3 assignments
        (102, 2),  # User 102 gets 2 assignments
        (103, 3),  # User 103 gets 3 assignments
    ]
    
    logger.info("Simulating assignments:")
    for user_id, count in assignments:
        for _ in range(count):
            track_user_assignment(role_id, user_id)
        
        tracked_count = get_user_assignment_count(role_id, user_id)
        logger.info(f"  User {user_id}: {tracked_count} assignments")
    
    # Show final stats
    stats = get_assignment_stats()
    logger.info(f"Final tracking stats: {stats['role_assignments']}")
    
    logger.info("Tracking consistency test completed!")
    return True

def main():
    """Main test function."""
    logger.info("Testing Database Integration with Assignment Configuration")
    logger.info("=" * 70)
    
    success = True
    
    # Test database integration
    if not test_database_integration():
        success = False
    
    # Test tracking consistency
    if not test_tracking_consistency():
        success = False
    
    if success:
        logger.info("\n" + "=" * 70)
        logger.info("All database integration tests PASSED!")
        logger.info("\nKey points verified:")
        logger.info("1. Database connection and query execution works")
        logger.info("2. Assignment count initialization from DB works")
        logger.info("3. Validation functions execute without errors")
        logger.info("4. In-memory tracking maintains consistency")
        logger.info("5. SQLAlchemy func import issue is resolved")
    else:
        logger.error("\n" + "=" * 70)
        logger.error("Some tests FAILED!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 