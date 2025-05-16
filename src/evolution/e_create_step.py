
import logging
from typing import Optional
from sqlalchemy.orm import Session
from agir_db.models.step import Step, StepStatus

logger = logging.getLogger(__name__)

def e_create_step(
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
        step = Step(
            episode_id=episode_id,
            state_id=state_id,
            user_id=user_id,
            action="scenario",
            status=StepStatus.RUNNING,
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
        return None