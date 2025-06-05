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

logger = logging.getLogger(__name__)

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
                self.vector_store = FAISS.from_texts(
                    ["No memories available"], 
                    self.embeddings,
                    metadatas=[{"id": "empty", "content": "No memories available"}]
                )
                return
            
            # Get all memories for the user
            memories = db.query(UserMemory).filter(UserMemory.user_id == self.user_id).all()
            
            if not memories:
                logger.info(f"No memories found for user {self.user_id}, creating empty vector store")
                # Create empty vector store
                self.vector_store = FAISS.from_texts(
                    ["No memories available"], 
                    self.embeddings,
                    metadatas=[{"id": "empty", "content": "No memories available"}]
                )
                return
            
            # Prepare documents for FAISS
            texts = []
            metadatas = []
            
            for memory in memories:
                if memory.content and memory.content.strip():
                    texts.append(memory.content)
                    metadata = {
                        "id": str(memory.id),
                        "content": memory.content,
                        "importance": getattr(memory, 'importance', 1.0),
                        "created_at": memory.created_at.isoformat() if memory.created_at else None,
                        "source": getattr(memory, 'source', 'unknown')
                    }
                    metadatas.append(metadata)
                    self.memories_metadata[str(memory.id)] = metadata
            
            if not texts:
                logger.info(f"No valid memory content found for user {self.user_id}")
                # Create empty vector store
                self.vector_store = FAISS.from_texts(
                    ["No memories available"], 
                    self.embeddings,
                    metadatas=[{"id": "empty", "content": "No memories available"}]
                )
                return
            
            # Create FAISS vector store
            self.vector_store = FAISS.from_texts(
                texts, 
                self.embeddings, 
                metadatas=metadatas
            )
            
            logger.info(f"Loaded {len(texts)} memories into FAISS vector store for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error loading memories into FAISS: {str(e)}")
            # Create fallback empty vector store
            self.vector_store = FAISS.from_texts(
                ["Error loading memories"], 
                self.embeddings,
                metadatas=[{"id": "error", "content": "Error loading memories"}]
            )
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
            
            results = []
            for doc in docs:
                # Skip empty placeholder results
                if doc.metadata.get("id") in ["empty", "error"]:
                    continue
                    
                result = {
                    "id": doc.metadata.get("id"),
                    "content": doc.page_content,
                    "importance": doc.metadata.get("importance", 1.0),
                    "created_at": doc.metadata.get("created_at"),
                    "source": doc.metadata.get("source", "unknown"),
                    "relevance_score": 1.0  # FAISS doesn't return scores by default
                }
                results.append(result)
            
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