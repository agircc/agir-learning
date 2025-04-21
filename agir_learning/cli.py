"""
Command-line interface for AGIR Learning
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

from .evolution import EvolutionEngine
from .llms import OpenAIProvider, AnthropicProvider

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='AGIR Learning Evolution Process')
    
    parser.add_argument(
        'process_file',
        help='Path to the YAML process file'
    )
    
    parser.add_argument(
        '--model',
        choices=['openai', 'anthropic'],
        default='openai',
        help='LLM provider to use (default: openai)'
    )
    
    parser.add_argument(
        '--model-name',
        help='Specific model name to use with the provider'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if process file exists
    if not os.path.exists(args.process_file):
        logger.error(f"Process file not found: {args.process_file}")
        sys.exit(1)
    
    # Create LLM provider
    llm_provider = None
    if args.model == 'openai':
        model_name = args.model_name or 'gpt-4'
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            sys.exit(1)
        llm_provider = OpenAIProvider(model_name=model_name)
    elif args.model == 'anthropic':
        model_name = args.model_name or 'claude-3-opus-20240229'
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment")
            sys.exit(1)
        llm_provider = AnthropicProvider(model_name=model_name)
    
    # Create evolution engine
    engine = EvolutionEngine(llm_provider=llm_provider)
    
    # Run evolution process
    logger.info(f"Running evolution process from file: {args.process_file}")
    success = engine.run_evolution_from_file(args.process_file)
    
    if success:
        logger.info("Evolution process completed successfully")
        sys.exit(0)
    else:
        logger.error("Evolution process failed")
        sys.exit(1)


if __name__ == '__main__':
    main() 