"""
Database utilities
"""

import os
import sys
import logging
from dotenv import load_dotenv
import importlib
from agir_db.db.session import get_db, SessionLocal
from agir_db.models import User, Scenario
from agir_db.db.base_class import Base
from ..evolution.episode_manager import EpisodeManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from agir_db.db.session import engine
    # Try to import migration module
    try:
        # import agir_db.alembic.env as alembic_env
        has_alembic = False
        has_alembic = True
    except ImportError:
        logger.warning("Alembic migrations not available, will use SQLAlchemy create_all instead")
        has_alembic = False
except ImportError:
    logger.error("agir_db package not found. Please install it using pip install -e git+https://github.com/agircc/agir-db.git")
    sys.exit(1)

def check_database() -> bool:
    """
    Check if database is configured correctly.
    
    Returns:
        bool: True if database is configured correctly, False otherwise
    """
    try:
        # Use EpisodeManager to check database tables
        return EpisodeManager.check_database_tables()
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return False

def run_migrations():
    """Run database migrations"""
    try:
        # Use Alembic for migrations or SQLAlchemy to create tables
        if has_alembic:
            try:
                # Try to use alembic for migrations
                from alembic import command
                from alembic.config import Config
                
                # Get alembic configuration file path
                alembic_cfg_path = os.path.join(os.path.dirname(importlib.util.find_spec("agir_db").origin), "alembic.ini")
                
                if os.path.exists(alembic_cfg_path):
                    alembic_cfg = Config(alembic_cfg_path)
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Alembic migrations completed successfully")
                else:
                    logger.warning(f"Alembic config not found at {alembic_cfg_path}, falling back to SQLAlchemy create_all")
                    Base.metadata.create_all(bind=engine)
                    logger.info("SQLAlchemy tables created successfully")
            except Exception as e:
                logger.error(f"Alembic migration failed: {str(e)}")
                logger.info("Falling back to SQLAlchemy create_all")
                Base.metadata.create_all(bind=engine)
                logger.info("SQLAlchemy tables created successfully")
        else:
            # Use SQLAlchemy to create all tables
            Base.metadata.create_all(bind=engine)
            logger.info("SQLAlchemy tables created successfully")
            
        return True
    except Exception as e:
        logger.error(f"Database migration failed: {str(e)}")
        return False

__all__ = ["get_db", "SessionLocal", "User", "Scenario", "check_database", "run_migrations"] 