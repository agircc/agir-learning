import logging
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple, Set
from agir_db.db.session import get_db

logger = logging.getLogger(__name__)

def check_database_tables() -> bool:
    """
    Check if all required database tables exist.
    
    Args:
        db: Database session
        
    Returns:
        bool: True if all tables exist, False otherwise
    """
    try:

        db = next(get_db())
        print("Database connection successful:  ")
        print(db)

        # Get engine inspector
        inspector = inspect(db.get_bind())
        
        # Get existing tables
        existing_tables = set(inspector.get_table_names())
        
        print("Existing tables: ")
        print(existing_tables)

        # Required tables
        required_tables = {
            'users',
            'scenarios',
            'states',
            'state_transitions',
            'episodes',
            'steps',
            'state_roles',
            'agent_roles',
            'agent_assignments',
            'chat_conversations',
            'chat_messages',
            'chat_participants',
            'custom_fields'
        }
        
        # Check if all required tables exist
        missing_tables = required_tables - existing_tables
        
        if missing_tables:
            logger.error(f"Missing required tables: {missing_tables}")
            return False
        
        logger.info("All required database tables exist")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error while checking tables: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while checking tables: {str(e)}")
        return False