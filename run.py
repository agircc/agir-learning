"""
Command-line interface
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.construction.check_database_tables import check_database_tables
from src.construction.construction import construction
from src.evolution.run_evolution_with_id import run_evolution_with_id

from src.evolution.evolution import EvolutionEngine
from src.evolution.process_instance_manager import ProcessManager  # Import the new ProcessManager
from src.llms import OpenAIProvider, AnthropicProvider, OllamaProvider
from src.construction import check_database
from src.llms.llm_provider_manager import LLMProviderManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Evolution Process')
    
    parser.add_argument(
        'process_file',
        help='Path to the YAML process file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--skip-db-check',
        action='store_true',
        help='Skip database check (not recommended)'
    )
    
    parser.add_argument(
        '--skip-llm',
        action='store_true',
        help='Skip LLM initialization for debugging'
    )
    
    parser.add_argument(
        '--setup-only',
        action='store_true',
        help='Only setup the process in the database without executing it'
    )
    
    parser.add_argument(
        '--mode',
        choices=['init', 'run', 'all'],
        default='all',
        help='Execution mode: init (only initialize process), run (only run evolution), all (both)'
    )
    
    parser.add_argument(
        '--process-id',
        type=int,
        help='Process ID for run mode (required when mode=run)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check database tables using the ProcessManager
    if not args.skip_db_check:
        logger.info("Checking database tables...")
        if not check_database_tables():
            logger.error("Database tables check failed. Please ensure database migrations have been run.")
            sys.exit(1)
        logger.info("Database tables check passed")
    
    process_id = None
    
    # Handle different execution modes
    if args.mode in ['init', 'all']:
        # Check if process file exists
        if not os.path.exists(args.process_file):
            logger.error(f"Process file not found: {args.process_file}")
            sys.exit(1)
            
        # Create process from YAML file
        logger.info(f"Creating process from file: {args.process_file}")
        process_id = construction(args.process_file)
        
        if not process_id:
            logger.error("Failed to create process from YAML file")
            sys.exit(1)
        
        logger.info(f"Process created with ID: {process_id}")
    
    # For run mode, use the provided process_id
    if args.mode == 'run':
        if args.process_id is None:
            logger.error("Process ID is required for run mode. Use --process-id to specify.")
            sys.exit(1)
        process_id = args.process_id
        logger.info(f"Using provided process ID: {process_id}")
    
    # Skip evolution if in init-only mode or setup-only flag is set
    if args.mode == 'init' or args.setup_only:
        logger.info("Setup-only flag set or init mode selected, exiting without executing process")
        sys.exit(0)
    
    try:        
        # Run evolution process, now using the ID rather than loading from file again
        logger.info(f"Running evolution process with ID: {process_id}")
        success = run_evolution_with_id(process_id)
        
        if success:
            logger.info("Evolution process completed successfully")
            sys.exit(0)
        else:
            logger.error("Evolution process failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"CLI Error in evolution process: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main()) 