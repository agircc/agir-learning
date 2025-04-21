"""
YAML loading utilities
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from ..models.process import Process

logger = logging.getLogger(__name__)


def load_process_from_file(file_path: str) -> Optional[Process]:
    """
    Load a process from a YAML file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Process instance or None if loading fails
    """
    if not os.path.exists(file_path):
        logger.error(f"Process file not found: {file_path}")
        return None
        
    try:
        with open(file_path, 'r') as f:
            yaml_content = f.read()
            
        process = Process.from_yaml(yaml_content)
        
        # Validate the process
        is_valid, errors = process.validate_graph()
        if not is_valid:
            logger.warning(f"Process validation warnings: {', '.join(errors)}")
            
        return process
    except Exception as e:
        logger.error(f"Failed to load process from {file_path}: {str(e)}")
        return None 