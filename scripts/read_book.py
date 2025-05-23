#!/usr/bin/env python
"""
Read a book and create memories for a user.
"""

import os
import sys
import logging
import argparse
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import Session
from agir_db.db.session import get_db

sys.path.append(os.getcwd())  # Add current directory to path for importing
from src.reading.book_reader import process_book_for_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(description='Read a book and create memories for a user')
    parser.add_argument('username', help='Username of the user to create memories for')
    parser.add_argument('book_path', help='Path to the book file')
    parser.add_argument('--start-chunk', type=int, default=0, help='Index of the chunk to start processing from (default: 0)')
    
    args = parser.parse_args()
    
    logger.info(f"Starting book reading for user {args.username} from {args.book_path} at chunk {args.start_chunk}")
    
    # Process the book
    memory_ids = process_book_for_user(args.username, args.book_path, args.start_chunk)
    
    if memory_ids:
        logger.info(f"Successfully created {len(memory_ids)} memories for user {args.username}")
        sys.exit(0)
    else:
        logger.error(f"Failed to process book for user {args.username}")
        sys.exit(1)

if __name__ == "__main__":
    main() 