#!/usr/bin/env python
"""
Test YAML loader with model field handling
"""

import logging
import sys
import json
from src.utils.yaml_loader import load_scenario_from_file

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_yaml_loader(file_path):
    """Test YAML loader with a specific file."""
    process = load_scenario_from_file(file_path)
    if not process:
        logger.error(f"Failed to load process from {file_path}")
        return False
    
    # Check learner model field
    learner = process.learner
    logger.info(f"Target user: {json.dumps(learner, indent=2)}")
    logger.info(f"Target user model: {learner.get('model', 'None')}")
    
    # Check roles model field
    for role in process.roles:
        logger.info(f"Role: {role.name}, model: {getattr(role, 'model', None)}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Please provide a YAML file path")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if test_yaml_loader(file_path):
        logger.info("YAML loader test passed!")
    else:
        logger.error("YAML loader test failed!")
        sys.exit(1) 