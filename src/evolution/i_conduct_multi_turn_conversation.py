import logging
import sys
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.llm.llm_provider import get_llm_model, call_llm_with_memory
from src.llm.llm_memory import enhance_messages_with_memories, store_conversation_as_memory

from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables.base import RunnableSequence

logger = logging.getLogger(__name__)

# End of conversation marker
OUR_CONVERSATION_HAS_ENDED_MARKER = "OUR CONVERSATION HAS ENDED"

def i_conduct_multi_turn_conversation(
  db: Session, 
  conversation: ChatConversation, 
  state: State, 
  role_users: List[Tuple[AgentRole, User]], 
  max_turns: int = 20
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
      # Keep track of messages
      messages = []
      
      # Initialize conversation chains for each role
      role_chains = {}
      chat_histories = {}
      
      # Create a conversation chain for each role
      for role, user in role_users:
          # Get the appropriate model for this user
          model_name = user.llm_model
          
          # Create a system prompt for this role
          system_prompt = f"""You are roleplaying as {role.name}. Your name is {user.first_name} {user.last_name}.

State Context: {state.name}
Task: {state.description}

IMPORTANT INSTRUCTIONS:
1. Respond ONLY as {user.first_name} {user.last_name}
2. Generate ONLY ONE message as a response
3. If you feel the conversation has naturally concluded and all goals are met, INSTEAD of a normal response, 
   reply ONLY with exactly these words: "{OUR_CONVERSATION_HAS_ENDED_MARKER}"
"""
          
          # Create prompt template using modern approach
          prompt = ChatPromptTemplate.from_messages([
              SystemMessagePromptTemplate.from_template(system_prompt),
              MessagesPlaceholder(variable_name="chat_history"),
              HumanMessagePromptTemplate.from_template("{input}")
          ])
          
          # Get the llm but don't enable memory yet (we'll handle it manually)
          user_id = str(user.id)
          llm = get_llm_model(model_name)
          
          # Create the chain using pipe operator (|) for RunnableSequence
          role_chains[user.id] = prompt | llm
          
          # Log the details for debugging
          logger.info(f"Created chain for user {user_id}, model: {model_name}, chain type: {type(role_chains[user.id])}")
          
          # Initialize empty chat history for each role
          chat_histories[user.id] = []
      
      # Conduct conversation
      conversation_complete = False
      turn_count = 0
      
      # Get the first role for completion checks
      first_role, first_user = role_users[0]
      
      while not conversation_complete and turn_count < max_turns:
          # For each role, generate a response in round-robin fashion
          for i, (role, user) in enumerate(role_users):
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
              
              # Prepare the input data for the chain
              input_data = {
                  "input": conversation_history,
                  "chat_history": lc_messages[-10:] if lc_messages else []
              }
              
              logger.info(f"Calling chain for user {user.id}, chain type: {type(chain)}")
              
              # Try to run the chain with memory enhancement
              try:
                  # First try using RunnableSequence APIs with robust error handling
                  try:
                      response = chain.invoke(input_data)
                      logger.info(f"Chain invocation successful, response type: {type(response)}")
                  except Exception as e:
                      logger.error(f"Error calling chain.invoke: {str(e)}")
                      # If that fails, try the direct call
                      try:
                          response = chain(input_data)
                          logger.info(f"Chain direct call successful, response type: {type(response)}")
                      except Exception as e2:
                          logger.error(f"Error with direct chain call: {str(e2)}")
                          # As a last resort, try to call the LLM directly with memory integration
                          logger.info("Attempting to call LLM directly with memory integration")
                          llm = get_llm_model(user.llm_model)
                          
                          # Prepare a simplified set of messages for direct LLM call
                          direct_messages = [SystemMessage(content=system_prompt)]
                          direct_messages.extend(input_data["chat_history"])
                          
                          # Call LLM with memory integration
                          response = call_llm_with_memory(
                              llm, 
                              direct_messages, 
                              str(user.id), 
                              query=conversation_history
                          )
              except Exception as e:
                  logger.error(f"All methods failed, creating error response: {str(e)}")
                  # Create a simulated error response as last resort
                  response = AIMessage(content=f"I apologize, but I'm experiencing technical difficulties.")
              
              # Extract content from response
              if hasattr(response, 'content'):
                  response_text = response.content
              else:
                  response_text = str(response)
                  
              # Check if this is the end marker message (case insensitive)
              if OUR_CONVERSATION_HAS_ENDED_MARKER.lower() in response_text.strip().lower():
                  # Don't save this message to the database
                  conversation_complete = True
                  logger.info(f"Conversation for state {state.name} concluded naturally")
                  break
              
              # Create and save normal message
              message = ChatMessage(
                  conversation_id=conversation.id,
                  sender_id=user.id,
                  content=response_text
              )
              
              db.add(message)
              db.commit()
              messages.append(message)
          
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
      return f"Error conducting conversation: {str(e)}"