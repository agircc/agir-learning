"""
Fast memory retrieval using FAISS for optimal performance.
Pre-loads user memories into vector store for fast similarity search.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import numpy as np
from datetime import datetime

from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from agir_db.db.session import get_db
from agir_db.models.user import User
from agir_db.models.memory import UserMemory
from src.common.utils.memory_utils import DEFAULT_EMBEDDING_MODEL

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler if none exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = True

# Log module loading
logger.info("FastMemoryRetriever module loaded successfully")

class FastMemoryRetriever:
    """
    Fast memory retriever using FAISS for efficient similarity search.
    Pre-loads all user memories into FAISS index for fast retrieval.
    """
    
    def __init__(self, user_id: str, embedding_model: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initialize the fast memory retriever
        
        Args:
            user_id: User ID to load memories for
            embedding_model: Name of the embedding model to use
        """
        self.user_id = user_id
        self.embedding_model = embedding_model
        self.embeddings = self._get_embedding_model(embedding_model)
        self.vector_store = None
        self.memories_metadata = {}  # Store memory metadata by ID
        
        # Load memories into FAISS
        self._load_memories()
    
    def _get_embedding_model(self, model_name: str):
        """Get embedding model instance"""
        if model_name.startswith("text-embedding"):
            return OpenAIEmbeddings(model=model_name)
        else:
            return HuggingFaceEmbeddings(model_name=model_name)
    
    def _load_memories(self):
        """Load all user memories into FAISS vector store"""
        try:
            db = next(get_db())
            
            # Get user to validate
            user = db.query(User).filter(User.id == self.user_id).first()
            if not user:
                logger.warning(f"User {self.user_id} not found, creating empty vector store")
                # Create empty vector store
                empty_doc = Document(
                    page_content="No memories available",
                    metadata={"id": "empty", "content": "No memories available"}
                )
                self.vector_store = FAISS.from_documents([empty_doc], self.embeddings)
                return
            
            # Get all memories for the user
            memories = db.query(UserMemory).filter(UserMemory.user_id == self.user_id).all()
            
            if not memories:
                logger.info(f"No memories found for user {self.user_id}, creating empty vector store")
                # Create empty vector store
                empty_doc = Document(
                    page_content="No memories available",
                    metadata={"id": "empty", "content": "No memories available"}
                )
                self.vector_store = FAISS.from_documents([empty_doc], self.embeddings)
                return
            
            # Prepare documents for FAISS
            documents = []
            
            for memory in memories:
                if memory.content and memory.content.strip():
                    metadata = {
                        "id": str(memory.id),
                        "content": memory.content,
                        "importance": getattr(memory, 'importance', 1.0),
                        "created_at": memory.created_at.isoformat() if memory.created_at else None,
                        "source": getattr(memory, 'source', 'unknown')
                    }
                    
                    doc = Document(
                        page_content=memory.content,
                        metadata=metadata
                    )
                    documents.append(doc)
                    self.memories_metadata[str(memory.id)] = metadata
            
            if not documents:
                logger.info(f"No valid memory content found for user {self.user_id}")
                # Create empty vector store
                empty_doc = Document(
                    page_content="No memories available",
                    metadata={"id": "empty", "content": "No memories available"}
                )
                self.vector_store = FAISS.from_documents([empty_doc], self.embeddings)
                return
            
            # Process documents in batches to avoid token limits
            # Calculate batch size based on average content length
            total_chars = sum(len(doc.page_content) for doc in documents)
            avg_chars_per_doc = total_chars / len(documents)
            
            # Estimate tokens (roughly 4 chars per token) and aim for ~40k tokens per batch
            # to stay well below 300k limit with safety margin
            target_tokens_per_batch = 40000
            estimated_tokens_per_doc = avg_chars_per_doc / 4
            batch_size = max(10, min(50, int(target_tokens_per_batch / estimated_tokens_per_doc)))
            
            total_docs = len(documents)
            logger.info(f"Processing {total_docs} documents in batches of {batch_size} (avg {avg_chars_per_doc:.0f} chars per doc)")
            
            # Create vector store with first batch
            first_batch = documents[:batch_size]
            try:
                self.vector_store = FAISS.from_documents(first_batch, self.embeddings)
                logger.info(f"Created FAISS vector store with first batch of {len(first_batch)} documents")
            except Exception as first_batch_error:
                logger.error(f"Error creating initial vector store: {str(first_batch_error)}")
                # If first batch fails, try with smaller batch size
                if batch_size > 10:
                    smaller_batch_size = max(5, batch_size // 2)
                    logger.info(f"Retrying with smaller batch size: {smaller_batch_size}")
                    first_batch = documents[:smaller_batch_size]
                    self.vector_store = FAISS.from_documents(first_batch, self.embeddings)
                    batch_size = smaller_batch_size
                else:
                    raise first_batch_error
            
            # Add remaining documents in batches
            for i in range(batch_size, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                try:
                    # Create temporary vector store for this batch
                    temp_vector_store = FAISS.from_documents(batch, self.embeddings)
                    # Merge with main vector store
                    self.vector_store.merge_from(temp_vector_store)
                    logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} documents")
                except Exception as batch_error:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {str(batch_error)}")
                    # If token limit error, try with smaller sub-batches
                    if "max_tokens_per_request" in str(batch_error) and len(batch) > 1:
                        logger.info(f"Splitting large batch into smaller sub-batches")
                        sub_batch_size = max(1, len(batch) // 2)
                        for j in range(0, len(batch), sub_batch_size):
                            sub_batch = batch[j:j + sub_batch_size]
                            try:
                                temp_sub_vector_store = FAISS.from_documents(sub_batch, self.embeddings)
                                self.vector_store.merge_from(temp_sub_vector_store)
                                logger.info(f"Added sub-batch: {len(sub_batch)} documents")
                            except Exception as sub_batch_error:
                                logger.error(f"Error processing sub-batch: {str(sub_batch_error)}")
                                continue
                    else:
                        # Continue with next batch instead of failing completely
                        continue
            
            logger.info(f"Successfully loaded {len(documents)} memories into FAISS vector store for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error loading memories into FAISS: {str(e)}")
            # Create fallback empty vector store
            error_doc = Document(
                page_content="Error loading memories",
                metadata={"id": "error", "content": "Error loading memories"}
            )
            self.vector_store = FAISS.from_documents([error_doc], self.embeddings)
        finally:
            if 'db' in locals():
                db.close()
    
    def search_memories(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using FAISS similarity search
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant memories with metadata
        """
        try:
            if not self.vector_store:
                logger.warning("Vector store not initialized")
                return []
            
            if not query or len(query.strip()) < 3:
                logger.info("Query too short, skipping search")
                return []
            
            # Perform similarity search
            docs = self.vector_store.similarity_search(query, k=k)
            
            # Extract memory IDs for database update
            memory_ids = []
            results = []
            for doc in docs:
                # Skip empty placeholder results
                if doc.metadata.get("id") in ["empty", "error"]:
                    continue
                    
                memory_id = doc.metadata.get("id")
                if memory_id:
                    memory_ids.append(memory_id)
                
                result = {
                    "id": memory_id,
                    "content": doc.page_content,
                    "importance": doc.metadata.get("importance", 1.0),
                    "created_at": doc.metadata.get("created_at"),
                    "source": doc.metadata.get("source", "unknown"),
                    "relevance_score": 1.0  # FAISS doesn't return scores by default
                }
                results.append(result)
            
            # Update access tracking in database
            if memory_ids:
                try:
                    db = next(get_db())
                    
                    # Fetch and update memory records
                    memories = db.query(UserMemory).filter(
                        UserMemory.id.in_(memory_ids),
                        UserMemory.user_id == self.user_id,
                        UserMemory.is_active == True
                    ).all()
                    
                    for memory in memories:
                        # Update access count and last_accessed (same as search_user_memories_vector)
                        memory.access_count += 1
                        memory.last_accessed = datetime.now()
                        db.add(memory)
                    
                    # Commit the access tracking updates
                    db.commit()
                    logger.debug(f"Updated access tracking for {len(memories)} memories")
                    
                except Exception as db_error:
                    logger.error(f"Error updating memory access tracking: {str(db_error)}")
                    # Don't fail the search if DB update fails
                finally:
                    if 'db' in locals():
                        db.close()
            
            logger.info(f"Found {len(results)} relevant memories for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            return []
    
    def get_memory_count(self) -> int:
        """Get the total number of memories loaded"""
        if not self.vector_store:
            return 0
        return len(self.memories_metadata)
    
    def refresh_memories(self):
        """Refresh the memory store by reloading from database"""
        logger.info(f"Refreshing memories for user {self.user_id}")
        self.memories_metadata.clear()
        self._load_memories()

# Global cache for memory retrievers to avoid reloading
_retriever_cache: Dict[str, FastMemoryRetriever] = {}
_cache_size_limit = 50  # Limit cache size to prevent memory issues

def get_fast_memory_retriever(user_id: str, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> FastMemoryRetriever:
    """
    Get a cached memory retriever for the user
    
    Args:
        user_id: User ID
        embedding_model: Embedding model name
        
    Returns:
        FastMemoryRetriever instance
    """
    cache_key = f"{user_id}:{embedding_model}"
    
    # Check cache
    if cache_key in _retriever_cache:
        return _retriever_cache[cache_key]
    
    # Create new retriever
    retriever = FastMemoryRetriever(user_id, embedding_model)
    
    # Cache with size limit
    if len(_retriever_cache) < _cache_size_limit:
        _retriever_cache[cache_key] = retriever
    else:
        # Remove oldest entry (simple FIFO)
        oldest_key = next(iter(_retriever_cache))
        del _retriever_cache[oldest_key]
        _retriever_cache[cache_key] = retriever
    
    return retriever

def clear_memory_cache():
    """Clear the memory retriever cache"""
    global _retriever_cache
    _retriever_cache.clear()
    logger.info("Memory retriever cache cleared") 