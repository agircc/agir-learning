"""
Command-line interface
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

from .evolution import EvolutionEngine
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
    
    # 检查数据库
    if not args.skip_db_check:
        logger.info("Checking database...")
        if not check_database():
            logger.error("Database check failed. Please ensure the database is configured correctly.")
            sys.exit(1)
        logger.info("Database check passed")
    
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