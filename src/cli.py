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
    
    def __init__(self, skip_llm=False):
        """Initialize the LLM provider manager
        
        Args:
            skip_llm: Whether to skip LLM initialization for testing purposes only
        """
        self.providers = {}  # Cache of initialized providers
        self.skip_llm = skip_llm
        
        # No default provider - will be determined by the database values
        self.default_provider = None
    
    def _create_provider(self, provider_type, model_name):
        """Create a new LLM provider
        
        Args:
            provider_type: Type of provider (openai, anthropic, ollama)
            model_name: Name of the model to use
            
        Returns:
            LLM provider instance
        
        Raises:
            ValueError: If provider cannot be initialized
        """
        # Skip LLM is only for testing
        if self.skip_llm:
            logger.info("Skip LLM flag is set, using dummy provider")
            return DummyProvider(model_name=model_name)
            
        if provider_type == 'openai':
            model = model_name or 'gpt-4'
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(f"OPENAI_API_KEY not found in environment. Required for model: {model}")
            
            logger.info(f"Initializing OpenAI provider with model: {model}")
            return OpenAIProvider(model_name=model)
            
        elif provider_type == 'anthropic':
            model = model_name or 'claude-3-opus-20240229'
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError(f"ANTHROPIC_API_KEY not found in environment. Required for model: {model}")
            
            logger.info(f"Initializing Anthropic provider with model: {model}")
            return AnthropicProvider(model_name=model)
            
        elif provider_type == 'ollama':
            model = model_name  # Must be specified
            if not model:
                raise ValueError("Model name must be specified for Ollama provider")
                
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
            
            # Set the OLLAMA_URL environment variable for the provider
            os.environ['OLLAMA_URL'] = ollama_url
            logger.info(f"Initializing Ollama provider with model {model} at {ollama_url}")
            
            # Verify Ollama is running and model is available
            self._verify_ollama_model(model)
            
            return OllamaProvider(model_name=model)
            
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    def _verify_ollama_model(self, model_name):
        """Verify that Ollama is running and the specified model is available
        
        Args:
            model_name: Name of the model to verify
            
        Raises:
            ValueError: If Ollama is not available or model is not found
        """
        try:
            import requests
            base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434').split('/api')[0]
            
            try:
                # Check if Ollama server is running
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    raise ValueError(f"Ollama server returned status code {response.status_code}")
                
                # Check if model is available
                models_data = response.json()
                models = models_data.get('models', [])
                model_names = [m.get('name') for m in models]
                
                if model_name not in model_names:
                    available_models = ", ".join(model_names) if model_names else "none"
                    raise ValueError(
                        f"Model '{model_name}' not found in Ollama. Available models: {available_models}. "
                        f"You may need to run: ollama pull {model_name}"
                    )
                
                logger.info(f"Verified Ollama model '{model_name}' is available")
                
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Failed to connect to Ollama server: {str(e)}")
                
        except ImportError:
            raise ValueError("Requests library not available, cannot verify Ollama model")
        
    def get_provider(self, model_name):
        """Get a provider for the specified model
        
        Args:
            model_name: Name of the model (e.g., "gpt-4", "claude-3", "phi")
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider cannot be initialized
        """
        if not model_name:
            raise ValueError("Model name must be specified")
            
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
            
        Raises:
            ValueError: If provider type cannot be determined
        """
        if not model_name:
            raise ValueError("Model name must be specified")
            
        model_name = model_name.lower()
        if model_name in ["gpt-3", "gpt-3.5", "gpt-4", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"] or model_name.startswith("gpt-"):
            return "openai"
        elif model_name in ["claude", "claude-3", "claude-3-opus", "claude-3-sonnet"] or model_name.startswith("claude-"):
            return "anthropic"
        elif model_name in ["llama", "phi", "mixtral", "mistral"] or model_name.startswith("llama-") or model_name.startswith("phi-"):
            return "ollama"
        else:
            raise ValueError(f"Could not determine provider type for model: {model_name}")


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
    
    try:
        # Create LLM provider manager - no default settings
        logger.info("Initializing LLM provider manager")
        llm_provider_manager = LLMProviderManager(
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
            
    except Exception as e:
        logger.error(f"Error in evolution process: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main() 