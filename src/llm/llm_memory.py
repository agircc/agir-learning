import logging
import os
from typing import List, Optional, Dict, Any, Union, Callable
import uuid

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from sqlalchemy.orm import Session
from agir_db.db.session import get_db
from agir_db.models.memory import UserMemory
from src.common.utils.memory_utils import get_user_memories, search_user_memories_vector

logger = logging.getLogger(__name__)

class UserMemoryManager:
    """Manages user memories with vector store for semantic search and retrieval."""
    
    def __init__(self, user_id: str, embedding_model: Optional[Any] = None):
        """
        Initialize the UserMemoryManager.
        
        Args:
            user_id: Unique identifier for the user
            embedding_model: Model to use for embeddings, defaults to OpenAIEmbeddings
        """
        self.user_id = user_id
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.memory_key = "relevant_memories"
        self._initialize_vector_store()
        # Load existing memories from database
        self._load_memories_from_db()
    
    def _initialize_vector_store(self):
        """Initialize the vector store for the user."""
        try:
            # Create a directory for vector stores if it doesn't exist
            os.makedirs(f"./vector_stores/{self.user_id}", exist_ok=True)
            
            # Create a dummy document to initialize FAISS
            # This avoids the list index out of range error when starting with empty docs
            dummy_doc = Document(
                page_content="Initialization document - can be ignored",
                metadata={"user_id": self.user_id, "is_dummy": True}
            )
            
            # Initialize FAISS vector store for the user with dummy document
            self.vector_store = FAISS.from_documents(
                documents=[dummy_doc],  # Use dummy doc instead of empty list
                embedding=self.embedding_model
            )
            
            # Create retriever from vector store
            self.retriever = self.vector_store.as_retriever(
                search_kwargs={"k": 5}  # Return top 5 most relevant memories
            )
            
            logger.info(f"Initialized vector store for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def _load_memories_from_db(self, limit: int = 100):
        """
        Load memories from database into the vector store.
        
        Args:
            limit: Maximum number of memories to load
        """
        try:
            # Get memories from database
            memories = get_user_memories(self.user_id, limit=limit)
            logger.info(f"Loaded {len(memories)} memories from database for user {self.user_id}")
            
            if not memories:
                logger.warning(f"No memories found in database for user {self.user_id}")
                return
            
            # Convert memories to documents and add to vector store
            documents = []
            for memory in memories:
                doc = Document(
                    page_content=memory['content'],
                    metadata={
                        "user_id": self.user_id,
                        "memory_id": memory.get('id', str(uuid.uuid4())),
                        "source": memory.get('source', 'database'),
                        "importance": memory.get('importance', 1.0)
                    }
                )
                documents.append(doc)
            
            # Add documents to vector store if there are any
            if documents:
                self.vector_store.add_documents(documents)
                logger.info(f"Added {len(documents)} documents to vector store from database")
        except Exception as e:
            logger.error(f"Failed to load memories from database: {str(e)}")
    
    def add_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a memory to the vector store.
        
        Args:
            text: The text content of the memory
            metadata: Optional metadata associated with the memory
        """
        try:
            metadata = metadata or {}
            metadata["user_id"] = self.user_id
            
            # Create document and add to vector store
            doc = Document(page_content=text, metadata=metadata)
            self.vector_store.add_documents([doc])
            
            logger.info(f"Added memory for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to add memory: {str(e)}")
    
    def add_conversation_memory(self, message: BaseMessage, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a conversation message as memory.
        
        Args:
            message: The message to add as memory
            metadata: Optional metadata associated with the memory
        """
        try:
            metadata = metadata or {}
            metadata["type"] = message.__class__.__name__
            self.add_memory(message.content, metadata)
        except Exception as e:
            logger.error(f"Failed to add conversation memory: {str(e)}")
    
    def retrieve_relevant_memories(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve relevant memories based on a query.
        Uses both vector store and database search to ensure comprehensive results.
        
        Args:
            query: The query to search for
            k: Number of relevant documents to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            if not query:
                logger.warning("Empty query provided to retrieve_relevant_memories")
                return []
            
            logger.info(f"Retrieving memories for query: '{query}'")
            
            # First, try to use the vector store
            vector_docs = []
            try:
                vector_docs = self.retriever.invoke(query)
                # Filter out initialization documents
                vector_docs = [doc for doc in vector_docs if not doc.metadata.get("is_dummy", False)]
                logger.info(f"Retrieved {len(vector_docs)} documents from vector store")
            except Exception as ve:
                logger.warning(f"Vector search failed: {str(ve)}")
            
            # If vector search returns few results, supplement with database search
            if len(vector_docs) < k:
                try:
                    # Use the utility function from memory_utils to search
                    db_memories = search_user_memories_vector(self.user_id, query, limit=k)
                    logger.info(f"Retrieved {len(db_memories)} memories from database")
                    
                    # Convert to Document objects
                    db_docs = []
                    for memory in db_memories:
                        doc = Document(
                            page_content=memory['content'],
                            metadata={
                                "user_id": self.user_id,
                                "memory_id": memory.get('id', str(uuid.uuid4())),
                                "source": memory.get('source', 'database'),
                                "importance": memory.get('importance', 1.0)
                            }
                        )
                        db_docs.append(doc)
                    
                    # Merge results, prioritizing vector store results
                    memory_ids = {doc.metadata.get("memory_id") for doc in vector_docs if "memory_id" in doc.metadata}
                    unique_db_docs = [doc for doc in db_docs if doc.metadata.get("memory_id") not in memory_ids]
                    
                    # Combine and limit to k results
                    combined_docs = vector_docs + unique_db_docs
                    if len(combined_docs) > k:
                        combined_docs = combined_docs[:k]
                    
                    logger.info(f"Combined {len(vector_docs)} vector docs and {len(unique_db_docs)} unique DB docs")
                    return combined_docs
                except Exception as dbe:
                    logger.warning(f"Database search failed: {str(dbe)}")
                    # Return vector docs if they exist
                    if vector_docs:
                        return vector_docs
                    return []
            
            return vector_docs
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            return []
    
    def get_memory_variables(self, query: str) -> Dict[str, str]:
        """
        Get memory variables for LLM context.
        
        Args:
            query: The query to search relevant memories for
            
        Returns:
            Dictionary with memory_key and relevant memories as string
        """
        try:
            if not query:
                logger.warning("Empty query provided to get_memory_variables")
                return {self.memory_key: ""}
                
            # Retrieve relevant documents
            docs = self.retrieve_relevant_memories(query)
            
            # Format documents into a string with better structure
            if docs:
                memories_formatted = []
                for i, doc in enumerate(docs):
                    # Extract importance if available
                    importance = doc.metadata.get("importance", 1.0)
                    importance_str = f" (Importance: {importance:.1f})" if importance != 1.0 else ""
                    
                    # Add formatted memory
                    memories_formatted.append(f"Memory {i+1}{importance_str}: {doc.page_content}")
                
                memories_string = "\n\n".join(memories_formatted)
                logger.info(f"Returning {len(docs)} formatted memories for context")
                return {self.memory_key: memories_string}
            else:
                logger.info("No relevant memories found for query")
                return {self.memory_key: ""}
        except Exception as e:
            logger.error(f"Failed to load memory variables: {str(e)}")
            return {self.memory_key: ""}


def enhance_messages_with_memories(
    messages: List[BaseMessage], 
    user_id: str,
    query: Optional[str] = None
) -> List[BaseMessage]:
    """
    Enhance message list with relevant user memories.
    
    Args:
        messages: Original messages list
        user_id: User ID to retrieve memories for
        query: Query to use for memory retrieval, defaults to last message content
        
    Returns:
        Enhanced messages with memory context
    """
    try:
        # Validate input
        if not messages or not isinstance(messages, list):
            logger.warning("No messages provided to enhance_messages_with_memories")
            return messages  # Return original messages if empty or invalid
            
        # Initialize memory manager
        memory_manager = UserMemoryManager(user_id)
        
        # If no query provided, use the last human message
        if query is None:
            query = ""  # Default empty query
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    query = msg.content
                    break
        
        if not query:
            logger.warning("No query found for memory retrieval")
            return messages  # Return original messages if no query found
        
        # Get relevant memories
        memory_vars = memory_manager.get_memory_variables(query)
        relevant_memories = memory_vars.get(memory_manager.memory_key, "")
        
        # Debug log to verify we're getting memories
        if relevant_memories:
            logger.info(f"Retrieved memories for integration: {relevant_memories[:100]}...")
        else:
            logger.info("No relevant memories found to enhance messages")
            return messages  # Return original messages if no memories
        
        # Make a copy of the messages list to avoid modifying the original
        enhanced_messages = messages.copy()
        
        # Find system message if present
        system_msg_index = None
        for i, msg in enumerate(enhanced_messages):
            if isinstance(msg, SystemMessage):
                system_msg_index = i
                break
        
        # Format the memory context with clear separation
        memory_content = f"""

RELEVANT USER MEMORIES:
{relevant_memories}

"""
        
        # Integrate memories into messages
        if system_msg_index is not None:
            # Update existing system message
            current_content = enhanced_messages[system_msg_index].content
            enhanced_content = current_content + memory_content
            enhanced_messages[system_msg_index] = SystemMessage(content=enhanced_content)
            logger.info("Enhanced existing system message with memories")
        else:
            # Create a new system message with memories at the beginning
            memory_msg = SystemMessage(content=f"Use the following user memories as context for your response:{memory_content}")
            enhanced_messages.insert(0, memory_msg)
            logger.info("Added new system message with memories")
        
        return enhanced_messages
    
    except Exception as e:
        logger.error(f"Failed to enhance messages with memories: {str(e)}")
        return messages  # Return original messages on error


def store_conversation_as_memory(user_id: str, messages: List[BaseMessage]):
    """
    Store conversation messages as memories.
    
    Args:
        user_id: User ID to store memories for
        messages: Messages to store as memories
    """
    try:
        memory_manager = UserMemoryManager(user_id)
        
        for message in messages:
            if not isinstance(message, SystemMessage):  # Don't store system messages
                memory_manager.add_conversation_memory(message)
                
        logger.info(f"Stored {len(messages)} messages as memories for user {user_id}")
    
    except Exception as e:
        logger.error(f"Failed to store conversation as memory: {str(e)}")


def invoke_llm_with_memory(
    llm_model: BaseChatModel,
    messages: List[BaseMessage],
    user_id: str,
    query: Optional[str] = None,
    store_result: bool = True
) -> Any:
    """
    Centralized function to invoke LLM with memory integration.
    
    This wrapper function handles:
    1. Enhancing messages with user memories
    2. Invoking the LLM
    3. Storing the conversation as memory
    
    Args:
        llm_model: The LangChain LLM model
        messages: List of messages for context
        user_id: User ID for memory lookup
        query: Optional query for memory retrieval
        store_result: Whether to store the result in memory
        
    Returns:
        The LLM response
    """
    try:
        # Enhance messages with memories
        enhanced_messages = enhance_messages_with_memories(messages, user_id, query)
        
        # Check which method the model implements
        if hasattr(llm_model, 'invoke') and callable(llm_model.invoke):
            response = llm_model.invoke(enhanced_messages)
        elif hasattr(llm_model, '__call__') and callable(llm_model.__call__):
            response = llm_model(enhanced_messages)
        elif hasattr(llm_model, 'generate') and callable(llm_model.generate):
            response = llm_model.generate(enhanced_messages)
        else:
            logger.error("The LLM model doesn't have expected methods: invoke, __call__, or generate")
            # Try a last resort approach
            response = llm_model._call(enhanced_messages)
        
        # Store conversation if needed
        if store_result:
            store_conversation_as_memory(user_id, messages + [response])
            
        return response
    
    except Exception as e:
        logger.error(f"Failed to invoke LLM with memory: {str(e)}")
        # Fall back to direct call without memory
        try:
            if hasattr(llm_model, 'invoke') and callable(llm_model.invoke):
                return llm_model.invoke(messages)
            elif hasattr(llm_model, '__call__') and callable(llm_model.__call__):
                return llm_model(messages)
            elif hasattr(llm_model, 'generate') and callable(llm_model.generate):
                return llm_model.generate(messages)
            else:
                return llm_model._call(messages)
        except Exception as inner_e:
            logger.error(f"Failed to call LLM directly: {str(inner_e)}")
            # Return a mock response as last resort
            return AIMessage(content="Sorry, I encountered an error processing your request.")


def with_memory(
    func: Callable,
    user_id_arg: str = 'user_id',
    messages_arg: str = 'messages',
    query_arg: Optional[str] = None,
    llm_model_arg: str = 'llm_model'
):
    """
    Decorator to add memory capabilities to any function that uses LLM.
    
    Usage:
        @with_memory(user_id_arg='user.id', messages_arg='messages', llm_model_arg='llm')
        def my_llm_function(user, messages, llm, ...):
            # Function will automatically use memory
            pass
    
    Args:
        func: The function to decorate
        user_id_arg: Argument name that contains user ID
        messages_arg: Argument name that contains messages
        query_arg: Optional argument name for query
        llm_model_arg: Argument name for LLM model
        
    Returns:
        Decorated function with memory capabilities
    """
    def wrapper(*args, **kwargs):
        # Extract arguments
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        
        # Map positional arguments to names
        all_args = dict(zip(arg_names, args))
        all_args.update(kwargs)
        
        # Extract needed parameters
        user_id = str(all_args.get(user_id_arg)) if user_id_arg in all_args else None
        messages = all_args.get(messages_arg) if messages_arg in all_args else []
        llm_model = all_args.get(llm_model_arg) if llm_model_arg in all_args else None
        query = all_args.get(query_arg) if query_arg and query_arg in all_args else None
        
        # Check if we have all necessary parameters
        if not user_id or not llm_model or not messages:
            logger.warning("Missing parameters for memory enhancement, calling original function")
            return func(*args, **kwargs)
        
        # Replace LLM invoke with memory-enhanced version
        original_invoke = None
        original_call = None
        
        # Save original methods based on what's available
        if hasattr(llm_model, 'invoke') and callable(llm_model.invoke):
            original_invoke = llm_model.invoke
            def memory_invoke(input_messages):
                return invoke_llm_with_memory(llm_model, input_messages, user_id, query)
            llm_model.invoke = memory_invoke
        elif hasattr(llm_model, '__call__') and callable(llm_model.__call__):
            original_call = llm_model.__call__
            def memory_call(input_messages):
                return invoke_llm_with_memory(llm_model, input_messages, user_id, query)
            llm_model.__call__ = memory_call
        
        try:
            # Call the original function
            result = func(*args, **kwargs)
            return result
        finally:
            # Restore original methods
            if original_invoke:
                llm_model.invoke = original_invoke
            if original_call:
                llm_model.__call__ = original_call
    
    return wrapper
