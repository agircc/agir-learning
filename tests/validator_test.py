"""
Test script for YAML validator
"""
import sys
import os
import logging

# Add the project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.common.utils.yaml_validator import validate_yaml_file
from src.common.utils.log_config import configure_logging

# Configure logging for testing
configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_all_scenarios():
    """Test validation on all scenario files in the scenarios directory."""
    scenarios_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scenarios")
    
    if not os.path.exists(scenarios_dir):
        logger.error(f"Scenarios directory not found: {scenarios_dir}")
        return False
    
    all_valid = True
    
    # Find all YAML files in the scenarios directory
    yaml_files = [f for f in os.listdir(scenarios_dir) if f.endswith(('.yml', '.yaml'))]
    
    if not yaml_files:
        logger.warning(f"No YAML files found in {scenarios_dir}")
        return False
    
    logger.info(f"Found {len(yaml_files)} scenario files to validate")
    
    # Validate each file
    for yaml_file in yaml_files:
        file_path = os.path.join(scenarios_dir, yaml_file)
        logger.info(f"Validating: {yaml_file}")
        
        if validate_yaml_file(file_path):
            logger.info(f"✅ {yaml_file} is valid")
        else:
            logger.error(f"❌ {yaml_file} has validation errors")
            all_valid = False
    
    return all_valid

if __name__ == "__main__":
    result = test_all_scenarios()
    if result:
        logger.info("All scenario files passed validation")
        sys.exit(0)
    else:
        logger.error("One or more scenario files failed validation")
        sys.exit(1) 