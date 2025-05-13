import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_participant import ChatParticipant
from agir_db.models.scenario import State
from agir_db.models.agent_role import AgentRole
from agir_db.models.user import User
from agir_db.models.step import Step

logger = logging.getLogger(__name__)

def create_conversation(db: Session, state: State, episode_id: int, role_users: List[Tuple[AgentRole, User]], step_id: int) -> Optional[ChatConversation]:
  """
  Create a conversation for a multi-role state.
  
  Args:
      db: Database session
      state: State in the scenario
      episode_id: ID of the episode
      role_users: List of tuples containing agent role and user instances
      step_id: ID of the existing step to link the conversation to
      
  Returns:
      Optional[ChatConversation]: Conversation if created, None otherwise
  """
  try:
      # Check if the step exists
      step = db.query(Step).filter(Step.id == step_id).first()
      if not step:
          logger.error(f"Step with ID {step_id} not found")
          return None
      
      # Create conversation and link to the step
      conversation = ChatConversation(
          title=f"Conversation for {state.name} - Episode {episode_id}",
          created_by=role_users[0][1].id,  # Use first user as creator
          related_id=step_id,
          related_type="step"  # Linking to the Step model
      )
      
      db.add(conversation)
      db.flush()
      
      # Add all users as participants
      for role, user in role_users:
          participant = ChatParticipant(
              conversation_id=conversation.id,
              user_id=user.id
          )
          db.add(participant)
      
      db.commit()
      db.refresh(conversation)
      
      logger.info(f"Created conversation with ID: {conversation.id} for state: {state.name}, linked to step ID: {step_id}")
      
      return conversation
      
  except Exception as e:
      db.rollback()
      logger.error(f"Failed to create conversation: {str(e)}")
      return None