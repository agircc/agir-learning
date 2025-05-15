#!/usr/bin/env python
"""
Database clearing utility for AGIR Learning
"""

import sys
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.construction.clear_database import clear_database_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Clear database tables')
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm database clearing without prompt'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the database clearing utility."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Confirm action unless --confirm flag is provided
    if not args.confirm:
        confirmation = input("WARNING: This will delete all data from the database. Are you sure? (y/N): ")
        if confirmation.lower() != 'y':
            logger.info("Database clearing cancelled")
            return 0
    
    logger.info("Clearing database tables...")
    if clear_database_tables():
        logger.info("Database tables cleared successfully")
        return 0
    else:
        logger.error("Failed to clear database tables")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 