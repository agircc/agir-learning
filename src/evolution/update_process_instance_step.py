"""
Update process instance step with response message
"""

import logging
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from agir_db.models.step import Step

logger = logging.getLogger(__name__)

def update_process_instance_step(
    db: Session,
    step_id: int,
    response_message: str
) -> Optional[int]:
    """
    Updates a process instance step with the response message.
    
    Args:
        db: Database session
        step_id: ID of the ProcessInstanceStep
        response_message: Message to add to the step
        
    Returns:
        Optional[int]: ID of the updated step if successful, None otherwise
    """
    try:
        # Get the step
        step = db.query(Step).filter(Step.id == step_id).first()
        if not step:
            logger.error(f"Step not found with ID: {step_id}")
            return None
        
        # Update the step
        step.response = response_message
        
        db.commit()
        logger.info(f"Updated step {step_id} with response message")
        
        return step_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update step: {str(e)}")
        return None