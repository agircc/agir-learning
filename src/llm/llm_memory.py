import logging
import os
from typing import List, Optional, Dict, Any, Union, Callable

from langchain.memory import VectorStoreRetrieverMemory
from langchain.schema import Document
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

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
    
    def _initialize_vector_store(self):
        """Initialize the vector store for the user."""
        try:
            # Create a directory for vector stores if it doesn't exist
            os.makedirs(f"./vector_stores/{self.user_id}", exist_ok=True)
            
            # Initialize FAISS vector store for the user
            self.vector_store = FAISS.from_documents(
                documents=[],  # Start with empty documents
                embedding=self.embedding_model
            )
            
            # Create retriever from vector store
            self.retriever = self.vector_store.as_retriever(
                search_kwargs={"k": 5}  # Return top 5 most relevant memories
            )
            
            # Initialize memory with the retriever
            self.memory = VectorStoreRetrieverMemory(
                retriever=self.retriever,
                memory_key=self.memory_key
            )
            
            logger.info(f"Initialized vector store for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
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
        
        Args:
            query: The query to search for
            k: Number of relevant documents to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            return self.retriever.get_relevant_documents(query, k=k)
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
            return self.memory.load_memory_variables({"input": query})
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
        # Initialize memory manager
        memory_manager = UserMemoryManager(user_id)
        
        # If no query provided, use the last human message
        if query is None:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    query = msg.content
                    break
            else:
                query = ""  # Fallback if no human message found
        
        # Get relevant memories
        memory_vars = memory_manager.get_memory_variables(query)
        relevant_memories = memory_vars.get(memory_manager.memory_key, "")
        
        if relevant_memories:
            # Insert memory context after system message if present
            for i, msg in enumerate(messages):
                if isinstance(msg, SystemMessage):
                    # Append memory to system message
                    updated_content = f"{msg.content}\n\nRelevant context from user memories:\n{relevant_memories}"
                    messages[i] = SystemMessage(content=updated_content)
                    break
            else:
                # No system message found, add a new one at the beginning
                memory_msg = SystemMessage(content=f"Relevant context from user memories:\n{relevant_memories}")
                messages.insert(0, memory_msg)
        
        return messages
    
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
