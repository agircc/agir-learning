"""
Logging configuration with rich colorized output
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Define log format constants
FULL_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(message)s"

def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    use_rich: bool = True,
) -> None:
    """
    Configure the logging system with rich colorized output
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs to
        use_rich: Whether to use Rich for console output (default: True)
    """
    handlers = []
    
    # Configure rich console handler
    if use_rich:
        console = Console(highlight=True)
        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=True,
            show_path=True,
        )
        rich_handler.setLevel(level)
        rich_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        handlers.append(rich_handler)
    else:
        # Standard console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(FULL_FORMAT))
        handlers.append(console_handler)
        
    # File handler (optional)
    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(FULL_FORMAT))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format=SIMPLE_FORMAT if use_rich else FULL_FORMAT,
    )

def get_logger(name: str):
    """Get a logger with the given name"""
    return logging.getLogger(name) 