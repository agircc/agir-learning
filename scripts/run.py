"""
Command-line interface
"""
import os
import sys
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()

from src.common.utils.check_database_tables import check_database_tables
from src.construction.run_construction import run_construction
from src.evolution.run_evolution import run_evolution
from src.common.utils.log_config import configure_logging
from src.common.utils.yaml_validator import validate_yaml_file

# Replace the basic logging setup with our Rich-based colorized logging
configure_logging(level=logging.INFO)
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
        '--skip-yaml-validation',
        action='store_true',
        help='Skip YAML validation'
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
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colorized logging output'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to write logs to a file'
    )
    
    parser.add_argument(
        '--allow-multi-assign',
        action='store_true',
        default=False,
        help='Allow users to be assigned to multiple episodes (default: False)'
    )
    
    parser.add_argument(
        '--start-assign-count',
        type=int,
        default=1,
        help='Starting assignment count for multi-assign mode (default: 1)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging based on arguments
    log_level = logging.DEBUG if args.verbose else logging.INFO
    log_file = args.log_file if hasattr(args, 'log_file') and args.log_file else None
    use_rich = not args.no_color if hasattr(args, 'no_color') else True
    
    configure_logging(
        level=log_level,
        log_file=log_file,
        use_rich=use_rich
    )
    
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
        
        # Validate YAML structure unless skip flag is set
        if not args.skip_yaml_validation:
            logger.info(f"Validating scenario YAML structure: {args.scenario_file}")
            if not validate_yaml_file(args.scenario_file):
                logger.error(f"YAML validation failed for file: {args.scenario_file}")
                sys.exit(1)
            logger.info("YAML validation successful")
            
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
        
        # Prepare assignment configuration
        assignment_config = {
            'allow_multi_assign': args.allow_multi_assign,
            'start_assign_count': args.start_assign_count
        }
        
        success = run_evolution(scenario_id, num_episodes=args.episodes, assignment_config=assignment_config)
        
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