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
from src.construction.run_construction import run_construction
from src.evolution.run_evolution import run_evolution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Evolution Scenario')
    
    parser.add_argument(
        'scenario_file',
        help='Path to the YAML scenario file'
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
        help='Only setup the scenario in the database without executing it'
    )
    
    parser.add_argument(
        '--mode',
        choices=['init', 'run', 'all'],
        default='all',
        help='Execution mode: init (only initialize scenario), run (only run evolution), all (both)'
    )
    
    parser.add_argument(
        '--scenario-id',
        type=int,
        help='Scenario ID for run mode (required when mode=run)'
    )
    
    parser.add_argument(
        '--episodes', '-e',
        type=int,
        default=1,
        help='Number of episodes to run (default: 1)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.skip_db_check:
        logger.info("Checking database tables...")
        if not check_database_tables():
            logger.error("Database tables check failed. Please ensure database migrations have been run.")
            sys.exit(1)
        logger.info("Database tables check passed")
    
    scenario_id = None
    
    # Handle different execution modes
    if args.mode in ['init', 'all']:
        # Check if scenario file exists
        if not os.path.exists(args.scenario_file):
            logger.error(f"Scenario file not found: {args.scenario_file}")
            sys.exit(1)
            
        # Create scenario from YAML file
        logger.info(f"Creating scenario from file: {args.scenario_file}")
        scenario_id = run_construction(args.scenario_file)
        
        if not scenario_id:
            logger.error("Failed to create scenario from YAML file")
            sys.exit(1)
        
        logger.info(f"Scenario created with ID: {scenario_id}")
    
    # For run mode, use the provided scenario_id
    if args.mode == 'run':
        if args.scenario_id is None:
            logger.error("Scenario ID is required for run mode. Use --scenario-id to specify.")
            sys.exit(1)
        scenario_id = args.scenario_id
        logger.info(f"Using provided scenario ID: {scenario_id}")
    
    # Skip evolution if in init-only mode or setup-only flag is set
    if args.mode == 'init' or args.setup_only:
        logger.info("Setup-only flag set or init mode selected, exiting without executing scenario")
        sys.exit(0)
    
    try:        
        # Run evolution scenario, now using the ID rather than loading from file again
        logger.info(f"Running evolution scenario with ID: {scenario_id}, episodes: {args.episodes}")
        success = run_evolution(scenario_id, num_episodes=args.episodes)
        
        if success:
            logger.info("Evolution scenario completed successfully")
            sys.exit(0)
        else:
            logger.error("Evolution scenario failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"CLI Error in evolution scenario: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main()) 