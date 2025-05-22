#!/usr/bin/env python
"""
Simple script to validate a scenario YAML file
"""
import sys
import os
import logging
from src.common.utils.yaml_validator import validate_yaml_file
from src.common.utils.log_config import configure_logging

# Configure logging
configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_yaml.py <path_to_yaml_file>")
        return 1
        
    yaml_file = sys.argv[1]
    
    if not os.path.exists(yaml_file):
        logger.error(f"File not found: {yaml_file}")
        return 1
    
    logger.info(f"Validating YAML file: {yaml_file}")
    
    if validate_yaml_file(yaml_file):
        logger.info(f"✅ YAML validation successful: {yaml_file}")
        return 0
    else:
        logger.error(f"❌ YAML validation failed: {yaml_file}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 