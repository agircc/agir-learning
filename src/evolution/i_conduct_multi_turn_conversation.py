import logging
import sys
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.common.llm_provider import LLMProviderManager, get_llm_model

from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

def i_conduct_multi_turn_conversation(
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
      chat_histories = {}
      
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
          

          # Create prompt template using modern approach
          prompt = ChatPromptTemplate.from_messages([
              SystemMessagePromptTemplate.from_template(system_prompt),
              MessagesPlaceholder(variable_name="chat_history"),
              HumanMessagePromptTemplate.from_template("{input}")
          ])
          
          # Create the chain using pipe operator (|) for RunnableSequence
          role_chains[user.id] = prompt | get_llm_model(model_name)
          
          # Initialize empty chat history for each role
          chat_histories[user.id] = []
      
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
              
              # Convert previous messages to LangChain message format
              lc_messages = []
              for msg in messages:
                  sender = db.query(User).filter(User.id == msg.sender_id).first()
                  if sender.id == user.id:
                      lc_messages.append(AIMessage(content=msg.content))
                  else:
                      lc_messages.append(HumanMessage(content=f"{sender.username}: {msg.content}"))
              
              # Generate response using the chain with invoke() instead of run()
              response = chain.invoke({
                  "input": conversation_history,
                  "chat_history": lc_messages[-10:] if lc_messages else []
              })
              
              # Extract content from response
              if hasattr(response, 'content'):
                  response_text = response.content
              else:
                  response_text = str(response)
              
              # Create and save message
              message = ChatMessage(
                  conversation_id=conversation.id,
                  sender_id=user.id,
                  content=response_text
              )
              
              db.add(message)
              db.commit()
              messages.append(message)
              
              # Check if conversation is complete
              if "I THINK WE'VE REACHED A CONCLUSION" in response_text:
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
      
      logger.info(f"Completed multi-turn conversation for state: {state.name}")
      
      return f"Completed multi-turn conversation for state: {state.name}"
      
  except Exception as e:
      logger.error(f"Failed to conduct multi-turn conversation: {str(e)}")
      sys.exit(1)