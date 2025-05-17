"""
Clear database tables functionality
"""

import logging
from sqlalchemy import text
from agir_db.db.session import get_db

logger = logging.getLogger(__name__)

def clear_database_tables():
    """
    Clear specific database tables in the correct order to avoid foreign key constraint issues.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = next(get_db())
        
        # Tables to clear in the correct order to respect foreign key constraints
        tables = [
            "chat_messages",
            "chat_participants",
            "chat_conversations",
            "steps",
            "agent_assignments",
            "episodes",
            "state_roles",
            "state_transitions",
            "states",
            "scenarios",
            "user_memories",
            "users"
        ]
        
        for table in tables:
            logger.info(f"Clearing table: {table}")
            db.execute(text(f"DELETE FROM {table}"))
        
        # Commit the transaction
        db.commit()
        logger.info("Database tables cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear database tables: {str(e)}")
        if 'db' in locals():
            db.rollback()
        return False 