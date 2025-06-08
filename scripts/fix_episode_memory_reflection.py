"""
Fix episode memory reflection script.
This script creates reflection memories for completed episodes that don't have them yet.
"""

import logging
import uuid
import sys
import os
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.user import User
from agir_db.models.episode import Episode, EpisodeStatus
from agir_db.models.step import Step, StepStatus
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.state import State
from agir_db.models.memory import UserMemory

from src.llm.llm_provider import get_llm_model
from src.common.utils.memory_utils import create_user_memory

# Constants - modify these as needed
USER_ID = "258486ed-9f70-434b-97c6-24a44d092639"  # Replace with actual user ID
SCENARIO_ID = '2a09689d-cc52-4350-a8c3-55fa906b9313'  # Replace with actual scenario ID

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def extract_llm_response(response) -> str:
    """
    Extract content from LLM response based on its type.
    
    Args:
        response: LLM response object
        
    Returns:
        str: Extracted text content
    """
    if hasattr(response, 'content'):
        return response.content
    elif isinstance(response, dict) and 'text' in response:
        return response['text']
    elif isinstance(response, dict) and 'content' in response:
        return response['content']
    elif hasattr(response, 'text'):
        return response.text
    else:
        return str(response)

def collect_episode_content(db: Session, episode_id: uuid.UUID) -> List[Dict[str, Any]]:
    """
    Collect all content from an episode (steps and conversations).
    
    Args:
        db: Database session
        episode_id: ID of the episode
        
    Returns:
        List[Dict]: List of content items from the episode
    """
    all_content = []
    
    # Get all completed steps in the episode
    steps = db.query(Step).filter(
        Step.episode_id == episode_id,
        Step.status == StepStatus.COMPLETED
    ).all()
    
    # Get all step IDs for this episode
    step_ids = [step.id for step in steps]
    
    # Get conversations linked to these steps
    conversations = []
    if step_ids:
        conversations = db.query(ChatConversation).filter(
            ChatConversation.related_id.in_(step_ids)
        ).all()
    
    # Add step content
    for step in steps:
        if step.generated_text and len(step.generated_text.strip()) > 0:
            state = db.query(State).filter(State.id == step.state_id).first()
            if state:
                all_content.append({
                    "state_name": state.name,
                    "content": step.generated_text,
                    "type": "step"
                })
                
    # Add conversation content
    for conversation in conversations:
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation.id
        ).order_by(ChatMessage.created_at).all()
        
        if messages:
            conversation_text = ""
            for msg in messages:
                sender = db.query(User).filter(User.id == msg.sender_id).first()
                if sender:
                    conversation_text += f"{sender.username}: {msg.content}\n\n"
            
            if conversation_text:
                # Find the state through the step
                step = db.query(Step).filter(Step.id == conversation.related_id).first()
                if step:
                    state = db.query(State).filter(State.id == step.state_id).first()
                    if state:
                        all_content.append({
                            "state_name": state.name,
                            "content": conversation_text,
                            "type": "conversation"
                        })
    
    return all_content

def create_episode_reflection(db: Session, user_id: str, episode: Episode, scenario: Scenario) -> Optional[uuid.UUID]:
    """
    Create a reflection memory for an episode.
    
    Args:
        db: Database session
        user_id: ID of the user to create memory for
        episode: Episode object
        scenario: Scenario object
        
    Returns:
        Optional[uuid.UUID]: Created memory ID if successful, None otherwise
    """
    try:
        # Get user and validate
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return None
            
        if not user.llm_model:
            logger.error(f"User {user_id} has no LLM model specified")
            return None
        
        # Collect episode content
        all_content = collect_episode_content(db, episode.id)
        
        if not all_content:
            logger.warning(f"No content found for episode {episode.id}")
            return None
        
        # Prepare episode summary
        episode_summary = f"Episode {episode.id} Summary:\n\n"
        for item in all_content:
            episode_summary += f"=== {item['state_name']} ({item['type']}) ===\n"
            episode_summary += item['content']
            episode_summary += "\n\n"
        
        # Get user's profession for personalized reflection
        user_profession = user.profession if user.profession else "professional"
        
        # Create profession-specific reflection prompt
        reflection_prompt = f"""You've just participated in an episode of the scenario "{scenario.name}" as a {user_profession}.

Here's what you experienced in your role:
{episode_summary}

As a {user_profession}, please reflect on your performance and learning from this experience:

**What I Did Well:**
- Which of my {user_profession} skills and techniques worked effectively in this scenario?
- What professional behaviors or approaches did I handle successfully?
- What decisions or actions am I proud of as a {user_profession} in this experience?
- How did I demonstrate competence in my professional role?

**What I Need to Improve:**
- What aspects of my {user_profession} practice could have been better in this scenario?
- Where did I struggle or feel uncertain in my professional role?
- What mistakes or missed opportunities did I identify?
- What professional habits or approaches need refinement?

**New Skills, Knowledge & Lessons Learned:**
- What new {user_profession} skills or techniques did I learn or develop?
- What fresh knowledge or insights did I gain relevant to my profession?
- What important lessons will I carry forward from this experience?
- How has this experience expanded my understanding as a {user_profession}?

Be honest and specific about your strengths, weaknesses, and learning outcomes. Focus on concrete examples from your experience as a {user_profession}."""
        
        # Generate reflection using LLM
        llm = get_llm_model(user.llm_model)
        response = llm.invoke(reflection_prompt)
        reflection_content = extract_llm_response(response)
        
        # Prepare context info for memory creation
        context_info = {
            "state_name": f"Reflecting on Episode {episode.id}",
            "task": f"Reflection on episode for scenario '{scenario.name}'",
            "content_type": "Episode Reflection"
        }
        
        # Prepare metadata
        metadata = {
            "memory_type": "episode_reflection",
            "episode_id": str(episode.id),
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "importance_score": 0.68
        }
        
        # Create the reflection memory
        memory_id = create_user_memory(
            db=db,
            user_id=user.id,
            context_info=context_info,
            original_content=reflection_content,
            model_name=user.llm_model,
            metadata=metadata,
            source="episode_reflection",
            source_id=episode.id,
            importance=0.68
        )
        
        if memory_id:
            logger.info(f"Created reflection memory {memory_id} for episode {episode.id}")
            return memory_id
        else:
            logger.error(f"Failed to create reflection memory for episode {episode.id}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating episode reflection: {str(e)}")
        return None

def check_existing_reflection(db: Session, user_id: str, episode_id: uuid.UUID) -> bool:
    """
    Check if a reflection memory already exists for this episode and user.
    
    Args:
        db: Database session
        user_id: User ID
        episode_id: Episode ID
        
    Returns:
        bool: True if reflection already exists, False otherwise
    """
    existing_memory = db.query(UserMemory).filter(
        UserMemory.user_id == user_id,
        UserMemory.source == "episode_reflection",
        UserMemory.source_id == episode_id
    ).first()
    
    return existing_memory is not None

def fix_episode_reflections():
    """
    Main function to fix missing episode reflections.
    """
    try:
        db = next(get_db())
        
        # Validate user exists
        user = db.query(User).filter(User.id == USER_ID).first()
        if not user:
            logger.error(f"User with ID {USER_ID} not found")
            return
        
        # Validate scenario exists
        scenario = db.query(Scenario).filter(Scenario.id == SCENARIO_ID).first()
        if not scenario:
            logger.error(f"Scenario with ID {SCENARIO_ID} not found")
            return
        
        logger.info(f"Processing reflections for user {user.username} and scenario '{scenario.name}'")
        
        # Get all completed episodes for this scenario
        completed_episodes = db.query(Episode).filter(
            Episode.scenario_id == SCENARIO_ID,
            Episode.status == EpisodeStatus.COMPLETED
        ).all()
        
        logger.info(f"Found {len(completed_episodes)} completed episodes")
        
        created_count = 0
        skipped_count = 0
        
        for episode in completed_episodes:
            # Check if reflection already exists
            if check_existing_reflection(db, USER_ID, episode.id):
                logger.info(f"Reflection already exists for episode {episode.id}, skipping")
                skipped_count += 1
                continue
            
            # Create reflection for this episode
            memory_id = create_episode_reflection(db, USER_ID, episode, scenario)
            
            if memory_id:
                created_count += 1
                logger.info(f"Successfully created reflection for episode {episode.id}")
            else:
                logger.error(f"Failed to create reflection for episode {episode.id}")
        
        logger.info(f"Completed: {created_count} reflections created, {skipped_count} skipped (already exist)")
        
    except Exception as e:
        logger.error(f"Error in fix_episode_reflections: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    logger.info("Starting episode reflection fix script...")
    fix_episode_reflections()
    logger.info("Episode reflection fix script completed.")
