"""
Command-line interface
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

from .evolution import EvolutionEngine
from .process_manager import ProcessManager  # Import the new ProcessManager
from .llms import OpenAIProvider, AnthropicProvider
from .db import check_database

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
    parser = argparse.ArgumentParser(description='Evolution Process')
    
    parser.add_argument(
        'process_file',
        help='Path to the YAML process file'
    )
    
    parser.add_argument(
        '--model',
        choices=['openai', 'anthropic', 'dummy'],
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
    
    return parser.parse_args()


# 定义一个更完整的DummyProvider类
class DummyProvider:
    """用于调试的模拟LLM提供者"""
    
    def __init__(self, model_name="dummy", **kwargs):
        self.model_name = model_name
        
    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
        """生成文本响应"""
        logger.info(f"[DUMMY] Prompt: {prompt}")
        return "This is a dummy response for debugging purposes."
        
    def generate_json(self, prompt, system_prompt=None, response_model=None, temperature=0.7, max_tokens=1000):
        """生成JSON响应"""
        logger.info(f"[DUMMY] JSON Prompt: {prompt}")
        return {"response": "This is a dummy JSON response", "status": "success"}


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
    
    # Check database tables using the ProcessManager
    if not args.skip_db_check:
        logger.info("Checking database tables...")
        if not ProcessManager.check_database_tables():
            logger.error("Database tables check failed. Please ensure database migrations have been run.")
            sys.exit(1)
        logger.info("Database tables check passed")
    
    # Create process from YAML file
    logger.info(f"Creating process from file: {args.process_file}")
    process_id = ProcessManager.create_process_from_yaml(args.process_file)
    
    if not process_id:
        logger.error("Failed to create process from YAML file")
        sys.exit(1)
    
    logger.info(f"Process created with ID: {process_id}")
    
    # If setup-only flag is set, exit here
    if args.setup_only:
        logger.info("Setup-only flag set, exiting without executing process")
        sys.exit(0)
    
    # Create LLM provider
    llm_provider = None
    
    # 如果跳过LLM初始化或使用dummy模型，使用模拟提供者
    if args.skip_llm or args.model == 'dummy':
        llm_provider = DummyProvider()
        logger.info(f"Using dummy LLM provider for {'debugging' if args.skip_llm else 'testing'}")
    elif args.model == 'openai':
        model_name = args.model_name or 'gpt-4'
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            sys.exit(1)
        try:
            llm_provider = OpenAIProvider(model_name=model_name)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {str(e)}")
            logger.info("Falling back to dummy provider for debugging")
            llm_provider = DummyProvider()
    elif args.model == 'anthropic':
        model_name = args.model_name or 'claude-3-opus-20240229'
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment")
            sys.exit(1)
        try:
            llm_provider = AnthropicProvider(model_name=model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic provider: {str(e)}")
            logger.info("Falling back to dummy provider for debugging")
            llm_provider = DummyProvider()
    
    # Create evolution engine with the process ID
    engine = EvolutionEngine(llm_provider=llm_provider)
    
    # Run evolution process, now using the ID rather than loading from file again
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