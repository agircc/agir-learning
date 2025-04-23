#!/usr/bin/env python
"""
Test script for multiple LLM providers
"""

import os
import logging
import sys
from dotenv import load_dotenv

from src.cli import LLMProviderManager, DummyProvider
from src.evolution import EvolutionEngine
from src.process_manager import ProcessManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Test multiple LLM providers with a process."""
    if len(sys.argv) < 2:
        logger.error("Please provide a YAML process file path as argument")
        sys.exit(1)
        
    process_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(process_file):
        logger.error(f"Process file not found: {process_file}")
        sys.exit(1)
    
    # Create process from YAML file
    logger.info(f"Creating process from file: {process_file}")
    process_id = ProcessManager.create_process_from_yaml(process_file)
    
    if not process_id:
        logger.error("Failed to create process from YAML file")
        sys.exit(1)
    
    logger.info(f"Process created with ID: {process_id}")
    
    # Create LLM provider manager
    llm_provider_manager = LLMProviderManager(
        default_provider_type='dummy',  # Use dummy for testing
        default_model_name=None,
        skip_llm=True
    )
    
    # Add some dummy providers for different models to test
    llm_provider_manager.providers = {
        "gpt-4": DummyProvider(model_name="gpt-4"),
        "phi": DummyProvider(model_name="phi"),
        "claude-3": DummyProvider(model_name="claude-3")
    }
    
    # Create evolution engine with the provider manager
    engine = EvolutionEngine(llm_provider_manager=llm_provider_manager)
    
    # Run evolution process
    logger.info(f"Running evolution process with ID: {process_id}")
    success = engine.run_evolution_with_id(process_id)
    
    if success:
        logger.info("Evolution process completed successfully")
        sys.exit(0)
    else:
        logger.error("Evolution process failed")
        sys.exit(1)

if __name__ == '__main__':
    main() 