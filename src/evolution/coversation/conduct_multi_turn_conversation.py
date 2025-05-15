import logging
import sys
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.scenario import State
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.llms.llm_provider_manager import LLMProviderManager

logger = logging.getLogger(__name__)

def conduct_multi_turn_conversation(
  db: Session, 
  conversation: ChatConversation, 
  state: State, 
  role_users: List[Tuple[AgentRole, User]], 
  max_turns: int = 10
) -> Optional[str]:
  """
  Conduct a multi-turn conversation between multiple roles.
  
  Args:
      db: Database session
      conversation: Chat conversation
      state: State in the scenario
      role_users: List of tuples containing agent role and user instances
      max_turns: Maximum number of conversation turns
      
  Returns:
      Optional[str]: Summary of the conversation if successful, None otherwise
  """
  try:
      # Initialize LLM provider manager
      llm_provider_manager = LLMProviderManager()
      
      # Start conversation with a message from the first role
      first_role, first_user = role_users[0]
      
      # Start with state description as first message
      initial_message = ChatMessage(
          conversation_id=conversation.id,
          sender_id=first_user.id,
          content=f"Let's start our discussion about: {state.description}. As {first_user.username}, I'll begin."
      )
      
      db.add(initial_message)
      db.commit()
      
      # Keep track of messages
      messages = [initial_message]
      
      # Conduct conversation
      conversation_complete = False
      turn_count = 0
      
      while not conversation_complete and turn_count < max_turns:
          # For each role, generate a response in a round-robin fashion
          for i, (role, user) in enumerate(role_users):
              # Skip the first role in the first turn as they already sent the initial message
              if turn_count == 0 and i == 0:
                  continue
              
              # Get the model for this role
              model_name = user.llm_model
              provider = llm_provider_manager.get_provider(model_name)
              
              # Build context from previous messages
              conversation_history = ""
              for msg in messages:
                  sender = db.query(User).filter(User.id == msg.sender_id).first()
                  conversation_history += f"{sender.username}: {msg.content}\n\n"
              
              # Build prompt - explicitly instruct to only generate a single response
              prompt = f"""You are an AI assistant playing the role of {user.username} in a conversation.

State: {state.name}
Task: {state.description}

Previous conversation:
{conversation_history}

IMPORTANT INSTRUCTIONS:
1. Respond ONLY as {user.username}
2. Generate ONLY ONE single message as a response
3. DO NOT include messages from other participants
4. DO NOT roleplay as multiple people
5. Stay in character as {user.username} only

If the conversation seems complete or if there's a natural stopping point, include the phrase "I THINK WE'VE REACHED A CONCLUSION" at the end of your message.
"""
              
              # Generate response
              response = provider.generate(prompt)
              
              # Add message to conversation
              message = ChatMessage(
                  conversation_id=conversation.id,
                  sender_id=user.id,
                  content=response
              )
              
              db.add(message)
              db.commit()
              messages.append(message)
              
              # Check if conversation is complete
              if "I THINK WE'VE REACHED A CONCLUSION" in response:
                  conversation_complete = True
                  break
          
          turn_count += 1
          
          # If we've reached max turns, conclude the conversation
          if turn_count >= max_turns:
              logger.warning(f"Conversation for state {state.name} reached maximum turns ({max_turns})")
              final_message = ChatMessage(
                  conversation_id=conversation.id,
                  sender_id=first_user.id,
                  content="We've had an extensive discussion. Let's conclude this conversation."
              )
              
              db.add(final_message)
              db.commit()
              messages.append(final_message)
      
      # Generate summary of the conversation
      conversation_history = ""
      for msg in messages:
          sender = db.query(User).filter(User.id == msg.sender_id).first()
          conversation_history += f"{sender.username}: {msg.content}\n\n"
      
      # Use the first user's model to generate a summary
      model_name = role_users[0][1].llm_model
      provider = llm_provider_manager.get_provider(model_name)
      
      summary_prompt = f"""Summarize the following conversation in a concise paragraph:

{conversation_history}

Provide a summary that captures the key points discussed and any conclusions reached.
"""
      
      summary = provider.generate(summary_prompt)
      
      logger.info(f"Completed multi-turn conversation for state: {state.name}")
      
      return f"Conversation summary: {summary}\n\nFull conversation:\n{conversation_history}"
      
  except Exception as e:
      logger.error(f"Failed to conduct multi-turn conversation: {str(e)}")
      sys.exit(1)