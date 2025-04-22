#!/usr/bin/env python
"""
Test script for the ProcessManager
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import ProcessManager
from src.process_manager import ProcessManager

def main():
    """Test the ProcessManager implementation"""
    # Check database tables
    logger.info("Checking database tables...")
    if not ProcessManager.check_database_tables():
        logger.error("Database tables check failed. Please run database migrations.")
        sys.exit(1)
    logger.info("Database tables check passed")
    
    # Process file to test
    process_file = "examples/doctor.yml"
    if not os.path.exists(process_file):
        logger.error(f"Process file not found: {process_file}")
        sys.exit(1)
    
    # Create process from YAML
    logger.info(f"Creating process from file: {process_file}")
    process_id = ProcessManager.create_process_from_yaml(process_file)
    
    if not process_id:
        logger.error("Failed to create process from YAML file")
        sys.exit(1)
    
    logger.info(f"Process created with ID: {process_id}")
    
    # Get the database session to find a user
    from agir_db.db.session import get_db
    from agir_db.models.user import User
    
    db = next(get_db())
    user = db.query(User).first()
    
    if not user:
        logger.error("No users found in the database")
        sys.exit(1)
    
    logger.info(f"Found user: {user.username} with ID: {user.id}")
    
    # Execute the process
    logger.info(f"Executing process with ID: {process_id}")
    instance_id = ProcessManager.execute_process(process_id, user.id)
    
    if not instance_id:
        logger.error("Failed to execute process")
        sys.exit(1)
    
    logger.info(f"Process instance created with ID: {instance_id}")
    
    # Advance the process
    logger.info("Advancing the process to the next node")
    step_id = ProcessManager.advance_process(instance_id)
    
    if not step_id:
        logger.error("Failed to advance process")
        sys.exit(1)
    
    logger.info(f"Process advanced, new step ID: {step_id}")
    
    # Complete the process
    logger.info("Completing the process")
    if not ProcessManager.complete_process(instance_id, success=True):
        logger.error("Failed to complete process")
        sys.exit(1)
    
    logger.info("Process completed successfully")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 