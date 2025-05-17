import logging
import sys
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from agir_db.models.user import User
from agir_db.models.agent_role import AgentRole
from agir_db.models.state import State
from agir_db.models.chat_message import ChatMessage
from agir_db.models.chat_conversation import ChatConversation

from src.common.llm_provider import get_llm_model

from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

# 结束对话的标记
CONVERSATION_END_MARKER = "Our conversation has ended"

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
3. DO NOT include messages from other participants
4. Stay in character as {user.first_name} {user.last_name}
5. If you feel the conversation has naturally concluded and all goals are met, INSTEAD of a normal response, 
   reply ONLY with exactly these words: "{CONVERSATION_END_MARKER}"
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
                  
              # Check if this is the end marker message
              if response_text.strip() == CONVERSATION_END_MARKER:
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
      sys.exit(1)