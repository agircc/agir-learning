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
from src.llms.llm_langchain import BaseLangChainProvider

# LangChain imports updated to use langchain_community where appropriate
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

def conduct_multi_turn_conversation(
  db: Session, 
  conversation: ChatConversation, 
  state: State, 
  role_users: List[Tuple[AgentRole, User]], 
  max_turns: int = 10
) -> Optional[str]:
  """
  Conduct a multi-turn conversation between multiple roles using LangChain.
  
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
      # Initialize LLM provider manager with LangChain support
      llm_provider_manager = LLMProviderManager(use_langchain=True)
      
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
      
      # Initialize conversation chains for each role
      role_chains = {}
      
      # Create a conversation chain for each role
      for role, user in role_users:
          # Get the appropriate model for this user
          model_name = user.llm_model
          
          # Create a system prompt for this role
          system_prompt = f"""You are roleplaying as {user.username}.

State Context: {state.name}
Task: {state.description}

IMPORTANT INSTRUCTIONS:
1. Respond ONLY as {user.username}
2. Generate ONLY ONE message as a response
3. DO NOT include messages from other participants
4. Stay in character as {user.username}
5. If the conversation seems complete, include "I THINK WE'VE REACHED A CONCLUSION" at the end
"""
          
          # Get LangChain provider for this model
          langchain_provider = llm_provider_manager.get_provider(model_name)
          
          # Create conversation chain with memory
          role_chains[user.id] = langchain_provider.create_chain(
              system_prompt=system_prompt,
              memory=True
          )
      
      # Conduct conversation
      conversation_complete = False
      turn_count = 0
      
      while not conversation_complete and turn_count < max_turns:
          # For each role, generate a response in round-robin fashion
          for i, (role, user) in enumerate(role_users):
              # Skip the first role in the first turn as they already sent the initial message
              if turn_count == 0 and i == 0:
                  continue
              
              # Get the conversation chain for this role
              chain = role_chains[user.id]
              
              # Prepare conversation history for input
              conversation_history = ""
              for msg in messages:
                  sender = db.query(User).filter(User.id == msg.sender_id).first()
                  conversation_history += f"{sender.username}: {msg.content}\n\n"
              
              # Generate response using the chain
              response = chain.predict(input=conversation_history)
              
              # Create and save message
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
      
      # Generate summary of the conversation using LangChain
      conversation_history = ""
      for msg in messages:
          sender = db.query(User).filter(User.id == msg.sender_id).first()
          conversation_history += f"{sender.username}: {msg.content}\n\n"
      
      # Use the first user's model to generate a summary
      model_name = role_users[0][1].llm_model
      langchain_provider = llm_provider_manager.get_provider(model_name)
      
      # Create a simple chain for summarization
      summary_prompt = PromptTemplate(
          input_variables=["conversation"],
          template="""Summarize the following conversation in a concise paragraph:

{conversation}

Provide a summary that captures the key points discussed and any conclusions reached."""
      )
      
      summary_chain = LLMChain(
          llm=langchain_provider.get_chat_model(),
          prompt=summary_prompt
      )
      
      summary = summary_chain.run(conversation=conversation_history)
      
      logger.info(f"Completed multi-turn conversation for state: {state.name}")
      
      return f"Conversation summary: {summary}\n\nFull conversation:\n{conversation_history}"
      
  except Exception as e:
      logger.error(f"Failed to conduct multi-turn conversation: {str(e)}")
      sys.exit(1)