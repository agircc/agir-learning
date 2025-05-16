"""
Update step with response message
"""

import logging
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from agir_db.models.step import Step, StepStatus

logger = logging.getLogger(__name__)

def update_step(
    db: Session,
    step_id: int,
    response_message: str = None,
    status: StepStatus = None
) -> Optional[int]:
    """
    Updates a step with the response message and/or status.
    
    Args:
        db: Database session
        step_id: ID of the step
        response_message: Message to add to the step (optional)
        status: New status for the step (optional)
        
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
        if response_message is not None:
            step.response = response_message
            
        if status is not None:
            step.status = status
        
        db.commit()
        logger.info(f"Updated step {step_id} with status: {status} and response message: {'Yes' if response_message else 'No'}")
        
        return step_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update step: {str(e)}")
        return None