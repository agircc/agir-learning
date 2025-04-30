import logging
from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.process_role import ProcessRole
from agir_db.models.process import Process, ProcessNode, ProcessTransition
from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
from agir_db.models.process_instance_step import ProcessInstanceStep
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def check_database_tables() -> bool:
    """
    Check if required database tables exist.
    
    Returns:
        bool: True if all required tables exist, False otherwise
    """
    try:
        db = next(get_db())
        
        tables_to_check = [
            (User, "user"),
            (Process, "process"),
            (ProcessNode, "process_node"),
            (ProcessRole, "process_role"),
            (ProcessTransition, "process_transition"),
            (ProcessInstance, "process_instance"),
            (ProcessInstanceStep, "process_instance_step")
        ]
        
        for model, table_name in tables_to_check:
            try:
                db.query(model).limit(1).all()
                logger.debug(f"Table {table_name} exists")
            except SQLAlchemyError as e:
                logger.error(f"Table {table_name} check failed: {str(e)}")
                return False
                
        return True
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return False