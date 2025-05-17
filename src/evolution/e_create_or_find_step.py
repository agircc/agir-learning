
import logging
import sys
from typing import Optional
from sqlalchemy.orm import Session
from agir_db.models.step import Step, StepStatus

logger = logging.getLogger(__name__)

def e_create_or_find_step(
    db: Session, 
    episode_id: int, 
    state_id: int, 
    user_id: Optional[int] = None,
    generated_text: Optional[str] = None
) -> Optional[int]:
    """
    Create a step.
    
    Args:
        db: Database session
        episode_id: ID of the episode
        state_id: ID of the state
        user_id: ID of the user (optional)
        generated_text: Comment/data from LLM (optional)
        
    Returns:
        Optional[int]: ID of the step if successful, None otherwise
    """
    try:
        # Check for unfinished or failed steps in the current state
        unfinished_step = db.query(Step).filter(
            Step.episode_id == episode_id,
            Step.state_id == state_id,
            Step.user_id == user_id,
            Step.status.in_([StepStatus.PENDING, StepStatus.RUNNING, StepStatus.FAILED])
        ).first()

        if unfinished_step:
            logger.info(f"Found unfinished step: {unfinished_step.id}")
            return unfinished_step.id

        step = Step(
            episode_id=episode_id,
            state_id=state_id,
            user_id=user_id,
            status=StepStatus.RUNNING,
            action="process",
            generated_text=generated_text
        )
        
        db.add(step)
        db.commit()
        db.refresh(step)
        
        logger.info(f"Created step with ID: {step.id}")
        
        return step.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create step: {str(e)}")
        sys.exit(1)