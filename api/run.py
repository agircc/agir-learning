#!/usr/bin/env python3
"""
Run the AGIR API server
"""

import uvicorn
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logging format
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific loggers levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    print(f"Logging level set to: {log_level.upper()}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AGIR API Server")
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Set logging level (default: INFO, can also be set via LOG_LEVEL env var)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("API_PORT", 8000)),
        help="Port to run the server on (default: 8000, can also be set via API_PORT env var)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("API_HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0, can also be set via API_HOST env var)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.environ.get("API_RELOAD", "true").lower() in ["true", "1", "yes"],
        help="Enable auto-reload for development (default: true, can be set via API_RELOAD env var)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Starting AGIR API server...")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Reload: {args.reload}")
    logger.info(f"Log Level: {args.log_level}")
    
    print(f"Starting AGIR API server on {args.host}:{args.port}...")
    print(f"Log level: {args.log_level}")
    print(f"To see memory retrieval logs, make sure LOG_LEVEL=INFO or --log-level INFO")
    
    uvicorn.run(
        "api.main:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload,
        log_level=args.log_level.lower()
    ) 