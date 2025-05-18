#!/usr/bin/env python
"""
Create database tables directly using SQLAlchemy
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_tables():
    """Create database tables using SQLAlchemy"""
    try:
        # Get database URI from environment variables
        database_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
        if not database_uri:
            database_uri = os.environ.get('DATABASE_URL')
            
        if not database_uri:
            logger.error("Database URI not found. Please set SQLALCHEMY_DATABASE_URI or DATABASE_URL environment variable")
            return False
            
        logger.info(f"Using database URI: {database_uri}")
        
        # Import SQLAlchemy and agir_db
        from sqlalchemy import create_engine, inspect
        from agir_db.db.base import Base
        import agir_db.models  # Import all models to ensure they're registered
        
        # Create engine
        engine = create_engine(database_uri)
        
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables
        logger.info("Creating all tables...")
        Base.metadata.create_all(engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        new_tables = set(inspector.get_table_names())
        created_tables = new_tables - existing_tables
        
        logger.info(f"Created {len(created_tables)} new tables: {created_tables}")
        logger.info(f"Total tables in database: {len(new_tables)}")
        
        # Verify all required tables exist
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
        
        missing_tables = required_tables - new_tables
        
        if missing_tables:
            logger.error(f"Missing required tables: {missing_tables}")
            return False
            
        logger.info("All required tables have been created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

if __name__ == '__main__':
    if create_tables():
        logger.info("Database tables created successfully")
        sys.exit(0)
    else:
        logger.error("Failed to create database tables")
        sys.exit(1) 