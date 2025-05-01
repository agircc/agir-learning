import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.chat_participant import ChatParticipant
from agir_db.models.process import ProcessNode
from agir_db.models.process_role import ProcessRole
from agir_db.models.user import User

logger = logging.getLogger(__name__)

def create_conversation(db: Session, node: ProcessNode, instance_id: int, role_users: List[Tuple[ProcessRole, User]]) -> Optional[ChatConversation]:
  """
  Create a conversation for a multi-role node.
  
  Args:
      db: Database session
      node: Process node
      instance_id: ID of the process instance
      role_users: List of tuples containing role and user instances
      
  Returns:
      Optional[ChatConversation]: Conversation if created, None otherwise
  """
  try:
      # Create conversation
      conversation = ChatConversation(
          title=f"Conversation for {node.name} - Instance {instance_id}",
          created_by=role_users[0][1].id  # Use first user as creator
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
      
      logger.info(f"Created conversation with ID: {conversation.id} for node: {node.name}")
      
      return conversation
      
  except Exception as e:
      db.rollback()
      logger.error(f"Failed to create conversation: {str(e)}")
      return None