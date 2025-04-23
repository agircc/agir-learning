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
from .llms import OpenAIProvider, AnthropicProvider, OllamaProvider
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
        choices=['openai', 'anthropic', 'ollama', 'dummy'],
        default='openai',
        help='Default LLM provider to use (default: openai)'
    )
    
    parser.add_argument(
        '--model-name',
        help='Specific model name to use with the default provider'
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


class LLMProviderManager:
    """Manages multiple LLM providers based on model names"""
    
    def __init__(self, default_provider_type='openai', default_model_name=None, skip_llm=False):
        """Initialize the LLM provider manager
        
        Args:
            default_provider_type: Default provider type to use
            default_model_name: Default model name for the default provider
            skip_llm: Whether to skip LLM initialization
        """
        self.providers = {}  # Cache of initialized providers
        self.default_provider_type = default_provider_type
        self.default_model_name = default_model_name
        self.skip_llm = skip_llm
        
        # Initialize default provider
        self.default_provider = self._create_provider(default_provider_type, default_model_name)
    
    def _create_provider(self, provider_type, model_name=None):
        """Create a new LLM provider
        
        Args:
            provider_type: Type of provider (openai, anthropic, ollama, dummy)
            model_name: Name of the model to use
            
        Returns:
            LLM provider instance
        """
        # Use dummy provider if skip_llm is True
        if self.skip_llm:
            return DummyProvider()
            
        if provider_type == 'dummy':
            return DummyProvider()
        elif provider_type == 'openai':
            model = model_name or 'gpt-4'
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment")
                logger.info("Falling back to dummy provider for debugging")
                return DummyProvider()
            try:
                return OpenAIProvider(model_name=model)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {str(e)}")
                logger.info("Falling back to dummy provider for debugging")
                return DummyProvider()
        elif provider_type == 'anthropic':
            model = model_name or 'claude-3-opus-20240229'
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not found in environment")
                logger.info("Falling back to dummy provider for debugging")
                return DummyProvider()
            try:
                return AnthropicProvider(model_name=model)
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic provider: {str(e)}")
                logger.info("Falling back to dummy provider for debugging")
                return DummyProvider()
        elif provider_type == 'ollama':
            model = model_name or 'phi'
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
            try:
                # Set the OLLAMA_URL environment variable for the provider
                os.environ['OLLAMA_URL'] = ollama_url
                logger.info(f"Using Ollama provider with model {model} at {ollama_url}")
                return OllamaProvider(model_name=model)
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {str(e)}")
                logger.info("Falling back to dummy provider for debugging")
                return DummyProvider()
        else:
            logger.error(f"Unknown provider type: {provider_type}")
            return DummyProvider()
    
    def get_provider(self, model_name=None):
        """Get a provider for the specified model
        
        Args:
            model_name: Name of the model (e.g., "gpt-4", "claude-3", "phi")
            
        Returns:
            LLM provider instance
        """
        if not model_name:
            return self.default_provider
            
        # If we already have a provider for this model, return it
        if model_name in self.providers:
            return self.providers[model_name]
            
        # Determine provider type from model name
        provider_type = self._detect_provider_type(model_name)
        
        # Create and cache the provider
        provider = self._create_provider(provider_type, model_name)
        self.providers[model_name] = provider
        return provider
    
    def _detect_provider_type(self, model_name):
        """Detect provider type from model name
        
        Args:
            model_name: Name of the model
            
        Returns:
            Provider type string
        """
        model_name = model_name.lower()
        if model_name in ["gpt-3", "gpt-3.5", "gpt-4", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"] or model_name.startswith("gpt-"):
            return "openai"
        elif model_name in ["claude", "claude-3", "claude-3-opus", "claude-3-sonnet"] or model_name.startswith("claude-"):
            return "anthropic"
        elif model_name in ["llama", "phi", "mixtral", "mistral"] or model_name.startswith("llama-") or model_name.startswith("phi-"):
            return "ollama"
        else:
            # Default to default provider type
            return self.default_provider_type


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
    
    # Create LLM provider manager
    llm_provider_manager = LLMProviderManager(
        default_provider_type=args.model,
        default_model_name=args.model_name,
        skip_llm=args.skip_llm
    )
    
    # Create evolution engine with the provider manager
    engine = EvolutionEngine(llm_provider_manager=llm_provider_manager)
    
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