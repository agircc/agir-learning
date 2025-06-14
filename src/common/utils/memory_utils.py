"""
Utility functions for working with user memories
"""

import logging
import sys
from typing import Dict, Any, List, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, Column, Float, String
from agir_db.models.user import User
from agir_db.models.memory import UserMemory
from agir_db.models.state import State
from agir_db.db.session import get_db
import uuid
import datetime
import numpy as np
import json
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from contextlib import contextmanager

# Import FAISS - exit if not available
try:
    import faiss
    from langchain_community.vectorstores import FAISS
    from langchain.docstore.document import Document
except ImportError as e:
    logging.error(f"FAISS library is required but not found: {str(e)}")
    logging.error("To install FAISS: conda install -c conda-forge faiss-cpu")
    sys.exit(1)
    
logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
# Default embedding dimension
DEFAULT_EMBEDDING_DIM = 1536  # OpenAI embedding dimension

@contextmanager
def get_db_session():
    """Get a database session and ensure it's properly closed"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def get_embedding_model(model_name: Optional[str] = None):
    """
    Get embedding model based on model name.
    
    Args:
        model_name: Name of the embedding model to use
        
    Returns:
        Embedding model instance
    """
    if not model_name:
        model_name = DEFAULT_EMBEDDING_MODEL
    
    # Check if it's an OpenAI model
    if model_name.startswith("text-embedding"):
        return OpenAIEmbeddings(model=model_name)
    else:
        # Default to HuggingFace for other models
        return HuggingFaceEmbeddings(model_name=model_name)

def generate_embedding(text: str, model_name: Optional[str] = None) -> List[float]:
    """
    Generate embedding vector for text.
    
    Args:
        text: Text to generate embedding for
        model_name: Name of the embedding model to use
        
    Returns:
        List[float]: Embedding vector
    """
    try:
        embedding_model = get_embedding_model(model_name)
        embedding = embedding_model.embed_query(text)
        return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        # Return empty vector in case of error
        return []

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        float: Cosine similarity (-1 to 1)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    # Convert to numpy arrays
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    # Calculate cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm_1 = np.linalg.norm(vec1)
    norm_2 = np.linalg.norm(vec2)
    
    # Avoid division by zero
    if norm_1 == 0 or norm_2 == 0:
        return 0.0
        
    return dot_product / (norm_1 * norm_2)

def python_vector_search(query_vector: List[float], memories: List[UserMemory], 
                         limit: int = 10, threshold: float = 0.0) -> List[Tuple[UserMemory, float]]:
    """
    Pure Python implementation of vector search using cosine similarity.
    This is used as a fallback when FAISS search returns no results.
    
    Args:
        query_vector: Query embedding vector
        memories: List of UserMemory objects
        limit: Maximum number of results to return
        threshold: Minimum similarity threshold
        
    Returns:
        List of (memory, similarity_score) tuples, sorted by descending similarity
    """
    results = []
    
    for memory in memories:
        if memory.embedding and len(memory.embedding) > 0:
            similarity = cosine_similarity(query_vector, memory.embedding)
            if similarity > threshold:
                results.append((memory, similarity))
    
    # Sort by similarity (descending)
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Return top k results
    return results[:limit]

def extract_knowledge_from_content(content: str, model_name: str) -> str:
    """
    Extract knowledge from content using LLM.
    
    Args:
        content: Original content to extract knowledge from
        model_name: LLM model to use
        
    Returns:
        Extracted knowledge string
    """
    if not content.strip():
        logger.warning("Empty content provided for knowledge extraction")
        return ""
    
    from src.llm.llm_provider import get_llm_model
    
    # Get LLM model without memory (not needed for simple extraction)
    llm_model = get_llm_model(model_name)
    
    # Create prompt for knowledge extraction
    prompt = f"""
Extract the most important information from the following content. 
Focus on facts, relationships, key events, and information that would be valuable to remember.
Format the knowledge in clear, concise statements. Exclude any opinions or subjective interpretations.

CONTENT:
{content}

EXTRACTED KNOWLEDGE:
"""
    
    # Call the LLM with the prompt and handle different response types
    try:
        # Use invoke method which is safer for different LLM providers
        response = llm_model.invoke(prompt)
        
        logger.info(f"LLM Memory Extraction Response type: {type(response)}")
        
        # Extract content from different possible response formats
        if hasattr(response, 'content'):
            # LangChain AIMessage format
            knowledge = response.content
        elif isinstance(response, dict) and 'text' in response:
            # Some models return dict with 'text' key
            knowledge = response['text']
        elif isinstance(response, dict) and 'content' in response:
            # Some models return dict with 'content' key
            knowledge = response['content']
        elif hasattr(response, 'text'):
            # Some models return object with text attribute
            knowledge = response.text
        else:
            # Fallback to string conversion
            knowledge = str(response)
        
        # Truncate if too long
        if len(knowledge) > 2000:
            knowledge = knowledge[:2000] + "..."
            
        return knowledge
        
    except Exception as e:
        logger.error(f"Failed to extract knowledge with LLM: {str(e)}")
        return content[:500] + "..."  # Return truncated original content on error

def create_user_memory(
    db: Session,
    user_id: Union[str, uuid.UUID],
    context_info: Dict[str, str],
    original_content: str,
    model_name: str,
    metadata: Dict[str, Any] = None,
    source: str = "auto",
    source_id: Union[str, uuid.UUID, int] = None,
    importance: float = 1.0
) -> Optional[uuid.UUID]:
    """
    Extract knowledge from content and create a memory for the user.
    
    Args:
        db: Database session
        user_id: User ID for whom to create the memory
        context_info: Dict containing context info like {"state_name": "...", "task": "..."}
        original_content: Original content to extract knowledge from
        model_name: LLM model name to use for extraction
        metadata: Additional metadata to store with the memory
        source: Source type (e.g., "conversation", "step", etc.)
        source_id: ID of the source object
        importance: Importance score for the memory
        
    Returns:
        Optional[uuid.UUID]: ID of the created memory if successful, None otherwise
    """
    try:
        # Validate input
        if not user_id or not original_content or not model_name:
            logger.error("Missing required parameters for memory creation")
            return None
            
        # Prepare extraction context
        state_name = context_info.get("state_name", "")
        task = context_info.get("task", "")
        content_type = context_info.get("content_type", "Content")
        
        extraction_context = f"State: {state_name}\nTask: {task}\n\n{content_type}:\n{original_content}"
        
        # Extract knowledge
        knowledge = extract_knowledge_from_content(extraction_context, model_name)
        
        # Generate embedding for the knowledge
        embedding = generate_embedding(knowledge)
        
        # Ensure metadata is a dict and values are serializable
        if metadata is None:
            metadata = {}
        
        # Convert any UUID or non-serializable values to strings
        serializable_metadata = {}
        for key, value in metadata.items():
            if hasattr(value, 'hex') or isinstance(value, (uuid.UUID, int)):
                serializable_metadata[key] = str(value)
            else:
                serializable_metadata[key] = value
        
        # Create memory
        memory = UserMemory(
            user_id=user_id,
            content=knowledge,
            meta_data=serializable_metadata,
            importance=importance,
            source=source,
            source_id=source_id,
            embedding=embedding  # Use the dedicated embedding field
        )
        
        db.add(memory)
        db.commit()
        db.refresh(memory)
        
        logger.info(f"Created new memory for user {user_id} from {source}")
        return memory.id
        
    except Exception as e:
        logger.error(f"Failed to create user memory: {str(e)}")
        db.rollback()
        return None

def get_user_memories(user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get memories for a specific user.
    
    Args:
        user_id: ID of the user
        limit: Maximum number of memories to return
        offset: Offset for pagination
        
    Returns:
        List[Dict[str, Any]]: List of memories as dictionaries
    """
    try:
        # Use context manager to ensure the session is properly closed
        with get_db_session() as db:
            # Get memories for the user, ordered by importance and creation date
            memories = db.query(UserMemory).filter(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True
            ).order_by(
                UserMemory.importance.desc(),
                UserMemory.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            # Convert to dictionaries
            result = []
            for memory in memories:
                result.append({
                    "id": str(memory.id),
                    "content": memory.content,
                    "meta_data": memory.meta_data,
                    "importance": memory.importance,
                    "source": memory.source,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
                    "access_count": memory.access_count,
                    "embedding": memory.embedding  # Include embedding in the result
                })
                
                # Update access count and last_accessed
                memory.access_count += 1
                memory.last_accessed = datetime.datetime.now()
            
            db.commit()
            
            return result
            
    except Exception as e:
        logger.error(f"Failed to get user memories: {str(e)}")
        return []

def build_langchain_faiss_index(memories: List[UserMemory], embedding_model):
    """
    Build a FAISS index using LangChain's FAISS vectorstore.
    
    Args:
        memories: List of UserMemory objects
        embedding_model: LangChain embedding model
        
    Returns:
        FAISS: LangChain FAISS vectorstore or None if no valid memories
    """
    # Only include memories that have content
    documents = []
    memory_map = {}  # To map Document IDs back to original memories
    
    for memory in memories:
        if memory.content:
            # Create a Document for each memory
            doc = Document(
                page_content=memory.content,
                metadata={
                    "id": str(memory.id),
                    "importance": memory.importance,
                    "source": memory.source,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "access_count": memory.access_count,
                    "user_meta_data": memory.meta_data
                }
            )
            documents.append(doc)
            memory_map[str(memory.id)] = memory
    
    # If no documents, return None
    if not documents:
        return None, {}
    
    # Create FAISS index using standard parameters
    try:
        # Use default parameters as LangChain doesn't expose all FAISS parameters directly
        vectorstore = FAISS.from_documents(documents, embedding_model)
        
        logger.info(f"Built FAISS index with {len(documents)} vectors")
        return vectorstore, memory_map
    except Exception as e:
        logger.error(f"Error building FAISS index: {str(e)}")
        return None, {}

def search_user_memories_vector(user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for memories based on vector similarity using FAISS.
    
    **DEPRECATED**: This function rebuilds FAISS index on every call.
    Use search_user_memories_cached() instead for better performance.
    
    Args:
        user_id: ID of the user
        query: Search query
        limit: Maximum number of memories to return
        
    Returns:
        List[Dict[str, Any]]: List of matching memories as dictionaries
    """
    logger.warning("search_user_memories_vector() is deprecated and rebuilds FAISS index on every call. "
                   "Use search_user_memories_cached() for better performance.")
    
    try:
        # Use context manager to ensure the session is properly closed
        with get_db_session() as db:
            # Generate query embedding
            query_embedding = generate_embedding(query)
            if not query_embedding or len(query_embedding) == 0:
                logger.error("Failed to generate embedding for query")
                return []
            
            # Retrieve memories with content
            memories = db.query(UserMemory).filter(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True,
                UserMemory.content != None
            ).all()
            
            if not memories:
                logger.warning(f"No memories found for user {user_id}")
                return []
            
            # Get embedding model
            embedding_model = get_embedding_model()
            
            # Build FAISS index
            vectorstore, memory_map = build_langchain_faiss_index(memories, embedding_model)
            
            if not vectorstore:
                logger.warning("Failed to build FAISS index")
                return []
                    
            # Search with a larger k and filter later to ensure we get enough results
            search_k = max(limit * 2, 20)
            try:
                # Perform search with vectorstore's similarity_search_with_score method
                search_results = vectorstore.similarity_search_with_score(query, k=search_k)
            except Exception as e:
                logger.error(f"Error during FAISS search: {str(e)}")
                return []
            
            # Process results
            result = []
            for doc, score in search_results:
                # Get memory ID from document metadata
                memory_id = doc.metadata.get("id")
                if memory_id in memory_map:
                    memory = memory_map[memory_id]
                    
                    # Update access count and last_accessed
                    memory.access_count += 1
                    memory.last_accessed = datetime.datetime.now()
                    db.add(memory)
                    
                    # Add to results
                    result.append({
                        "id": str(memory.id),
                        "content": memory.content,
                        "meta_data": memory.meta_data,
                        "importance": memory.importance,
                        "source": memory.source,
                        "created_at": memory.created_at.isoformat() if memory.created_at else None,
                        "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
                        "access_count": memory.access_count,
                        "embedding": memory.embedding,
                        "score": float(score)
                    })
            
            db.commit()
            
            # Sort by score (FAISS returns distance, convert to similarity by inverting)
            result.sort(key=lambda x: x["score"], reverse=False)
            
            # Limit to requested number
            result = result[:limit]
            
            if result:
                logger.info(f"Found {len(result)} memories using FAISS vector search")
            return result
            
    except Exception as e:
        logger.error(f"Failed to search user memories with vector: {str(e)}")
        return []

def search_user_memories_cached(user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for memories using cached FAISS retriever for optimal performance.
    
    **RECOMMENDED**: This function uses cached FastMemoryRetriever to avoid rebuilding
    FAISS index on every call, resulting in much better performance.
    
    Args:
        user_id: ID of the user
        query: Search query
        limit: Maximum number of memories to return
        
    Returns:
        List[Dict[str, Any]]: List of matching memories as dictionaries
    """
    try:
        from src.completions.fast_memory_retriever import get_fast_memory_retriever
        
        # Get cached memory retriever
        memory_retriever = get_fast_memory_retriever(user_id)
        
        # Search memories
        memories = memory_retriever.search_memories(query, k=limit)
        
        if not memories:
            return []
        
        # Extract memory IDs to fetch full records from database
        memory_ids = [memory.get('id') for memory in memories if memory.get('id')]
        
        if not memory_ids:
            return []
        
        # Use context manager to ensure the session is properly closed
        with get_db_session() as db:
            # Fetch full memory records from database
            db_memories = db.query(UserMemory).filter(
                UserMemory.id.in_(memory_ids),
                UserMemory.user_id == user_id,
                UserMemory.is_active == True
            ).all()
            
            # Create a mapping from ID to database memory objects
            db_memory_map = {str(memory.id): memory for memory in db_memories}
            
            # Process results and update access tracking
            result = []
            for cached_memory in memories:
                memory_id = cached_memory.get('id')
                if memory_id and memory_id in db_memory_map:
                    db_memory = db_memory_map[memory_id]
                    
                    # Update access count and last_accessed (same as search_user_memories_vector)
                    db_memory.access_count += 1
                    db_memory.last_accessed = datetime.datetime.now()
                    db.add(db_memory)
                    
                    # Add to results with full data from database
                    result.append({
                        "id": str(db_memory.id),
                        "content": db_memory.content,
                        "meta_data": db_memory.meta_data,  # Full metadata from database
                        "importance": db_memory.importance,
                        "source": db_memory.source,
                        "created_at": db_memory.created_at.isoformat() if db_memory.created_at else None,
                        "last_accessed": db_memory.last_accessed.isoformat() if db_memory.last_accessed else None,
                        "access_count": db_memory.access_count,
                        "embedding": db_memory.embedding,  # Full embedding from database
                        "score": cached_memory.get('relevance_score', 1.0)
                    })
            
            # Commit the access tracking updates
            db.commit()
        
        logger.info(f"Found {len(result)} memories using cached retriever for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to search user memories with cached retriever: {str(e)}")
        return []

def search_user_memories(user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for memories based on a text query using cached FAISS retriever.
    
    Args:
        user_id: ID of the user
        query: Search query
        limit: Maximum number of memories to return
        
    Returns:
        List[Dict[str, Any]]: List of matching memories as dictionaries
    """
    try:
        # Use cached version for better performance
        return search_user_memories_cached(user_id, query, limit)
    except Exception as e:
        logger.error(f"Failed to search user memories: {str(e)}")
        return []

def add_user_memory(user_id: str, content: str, meta_data: Dict[str, Any] = None, 
                   importance: float = 1.0, source: str = "manual") -> Optional[str]:
    """
    Add a new memory for a user.
    
    Args:
        user_id: ID of the user
        content: Memory content
        meta_data: Additional metadata about the memory
        importance: Importance score (higher = more important)
        source: Source of the memory
        
    Returns:
        Optional[str]: ID of the created memory if successful, None otherwise
    """
    try:
        # Use context manager to ensure the session is properly closed
        with get_db_session() as db:
            # Generate embedding for the content
            embedding = generate_embedding(content)
            
            # Ensure metadata is a dict and values are serializable
            if meta_data is None:
                meta_data = {}
            
            # Convert any UUID or non-serializable values to strings
            serializable_metadata = {}
            for key, value in meta_data.items():
                if hasattr(value, 'hex') or isinstance(value, (uuid.UUID, int)):
                    serializable_metadata[key] = str(value)
                else:
                    serializable_metadata[key] = value
            
            # Create memory
            memory = UserMemory(
                user_id=user_id,
                content=content,
                meta_data=serializable_metadata,
                importance=importance,
                source=source,
                embedding=embedding
            )
            
            db.add(memory)
            db.commit()
            db.refresh(memory)
            
            logger.info(f"Created new memory for user {user_id} from {source}")
            return str(memory.id)
            
    except Exception as e:
        logger.error(f"Failed to add user memory: {str(e)}")
        return None 