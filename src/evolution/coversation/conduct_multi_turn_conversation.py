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

# LangChain imports
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

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
      
      # Initialize LangChain memories for each participant
      chat_memories = {}
      
      for role, user in role_users:
          # Create a conversation memory for each participant
          chat_memories[user.id] = ConversationBufferMemory(
              return_messages=True,
              memory_key="chat_history"
          )
          
          # Add initial system message with role instructions
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
          chat_memories[user.id].chat_memory.add_message(SystemMessage(content=system_prompt))
      
      # Conduct conversation
      conversation_complete = False
      turn_count = 0
      
      while not conversation_complete and turn_count < max_turns:
          # For each role, generate a response in round-robin fashion
          for i, (role, user) in enumerate(role_users):
              # Skip the first role in the first turn as they already sent the initial message
              if turn_count == 0 and i == 0:
                  continue
              
              # Get the model for this role
              model_name = user.llm_model
              provider = llm_provider_manager.get_provider(model_name)
              
              # Update conversation history in memory
              conversation_history = ""
              for msg in messages:
                  sender = db.query(User).filter(User.id == msg.sender_id).first()
                  conversation_history += f"{sender.username}: {msg.content}\n\n"
              
              # Set up LangChain model
              # Try to get LangChain model from provider, or create a default one
              try:
                  llm = provider.get_langchain_model()
              except (AttributeError, NotImplementedError):
                  llm = ChatOpenAI(model_name=model_name, temperature=0.7)
              
              # Create chat prompt template
              chat_prompt = ChatPromptTemplate.from_messages([
                  SystemMessagePromptTemplate.from_template(
                      "You are roleplaying as {character}. Current discussion: {state}. {task}"
                  ),
                  HumanMessagePromptTemplate.from_template(
                      "Previous conversation:\n{conversation_history}\n\nRespond as {character}:"
                  )
              ])
              
              # Create LangChain chain
              chain = LLMChain(
                  llm=llm,
                  prompt=chat_prompt,
                  verbose=False
              )
              
              # Execute chain to get response
              response = chain.run(
                  character=user.username,
                  state=state.name,
                  task=state.description,
                  conversation_history=conversation_history
              )
              
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
      provider = llm_provider_manager.get_provider(model_name)
      
      # Try to use LangChain for summary if possible
      try:
          llm = provider.get_langchain_model()
      except (AttributeError, NotImplementedError):
          llm = ChatOpenAI(model_name=model_name, temperature=0.3)
          
      summary_prompt = PromptTemplate(
          input_variables=["conversation"],
          template="""Summarize the following conversation in a concise paragraph:

{conversation}

Provide a summary that captures the key points discussed and any conclusions reached."""
      )
      
      summary_chain = LLMChain(llm=llm, prompt=summary_prompt)
      summary = summary_chain.run(conversation=conversation_history)
      
      logger.info(f"Completed multi-turn conversation for state: {state.name}")
      
      return f"Conversation summary: {summary}\n\nFull conversation:\n{conversation_history}"
      
  except Exception as e:
      logger.error(f"Failed to conduct multi-turn conversation: {str(e)}")
      sys.exit(1)