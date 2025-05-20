"""
Book reader module for AGIR Learning.
"""

import os
import sys
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
import json

from sqlalchemy.orm import Session
from agir_db.db.session import get_db
from agir_db.models.user import User

from src.llm.llm_provider import get_llm_model
from src.common.utils.memory_utils import create_user_memory

logger = logging.getLogger(__name__)

def read_book_file(book_path: str) -> Optional[str]:
    """
    Read a book from a file.
    
    Args:
        book_path: Path to the book file
        
    Returns:
        Optional[str]: Book content if successful, None otherwise
    """
    try:
        # Make sure the path exists
        if not os.path.exists(book_path):
            # Try prepending workspace path if it's a relative path
            workspace_path = os.getcwd()
            full_path = os.path.join(workspace_path, book_path)
            if not os.path.exists(full_path):
                logger.error(f"Book file not found at {book_path} or {full_path}")
                return None
            book_path = full_path
        
        with open(book_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Failed to read book file: {str(e)}")
        return None

def chunk_book_content(content: str, chunk_size: int = 2000) -> List[str]:
    """
    Split book content into manageable chunks.
    
    Args:
        content: Book content
        chunk_size: Approximate size of each chunk
        
    Returns:
        List[str]: List of content chunks
    """
    # Simple chunking by paragraphs while respecting the chunk size
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def process_book_for_user(username: str, book_path: str) -> Optional[List[uuid.UUID]]:
    """
    Process a book and create memories for a user.
    
    Args:
        username: Username to find user
        book_path: Path to the book file
        
    Returns:
        Optional[List[uuid.UUID]]: List of created memory IDs if successful, None otherwise
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Find the user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.error(f"User with username {username} not found")
            return None
        
        # Get the user's LLM model
        model_name = user.llm_model
        if not model_name:
            logger.warning(f"User {username} has no LLM model specified, using default")
            sys.exit(1)
        
        # Read the book
        content = read_book_file(book_path)
        if not content:
            return None
        
        # Get book title from filename
        book_title = os.path.basename(book_path)
        book_title = os.path.splitext(book_title)[0]
        
        # Process content in chunks
        chunks = chunk_book_content(content)
        logger.info(f"Processing book '{book_title}' with {len(chunks)} chunks")
        
        memory_ids = []
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            # Create context info
            context_info = {
                "state_name": f"Reading {book_title}",
                "task": f"Reading and reflecting on part {i+1} of {len(chunks)}",
                "content_type": "Book Content"
            }
            
            # Metadata for the memory
            metadata = {
                "memory_type": "book_knowledge",
                "book_title": book_title,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_path": book_path,
                "importance_score": 0.8  # Default importance
            }
            
            # Use LLM to extract knowledge and create memory
            memory_id = create_user_memory(
                db=db,
                user_id=user.id,
                context_info=context_info,
                original_content=chunk,
                model_name=model_name,
                metadata=metadata,
                source="book_reading",
                importance=0.8
            )
            
            if memory_id:
                memory_ids.append(memory_id)
                logger.info(f"Created memory from chunk {i+1} for user {username}")
            
        # Create a reflection for the entire book
        if memory_ids:
            # Prepare a prompt for reflecting on the book
            llm = get_llm_model(model_name)
            
            reflection_prompt = f"""
You've just finished reading the book "{book_title}".
Please reflect on the main themes, key insights, and how this book has impacted your understanding.
Summarize what you've learned and how it might influence your thinking or actions in the future.
"""
            
            # Generate reflection
            response = llm.invoke(reflection_prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                reflection = response.content
            elif isinstance(response, dict) and 'text' in response:
                reflection = response['text']
            elif isinstance(response, dict) and 'content' in response:
                reflection = response['content']
            elif hasattr(response, 'text'):
                reflection = response.text
            else:
                reflection = str(response)
            
            # Create reflection memory
            context_info = {
                "state_name": f"Reflecting on {book_title}",
                "task": "Overall reflection on the book",
                "content_type": "Book Reflection"
            }
            
            metadata = {
                "memory_type": "book_reflection",
                "book_title": book_title,
                "source_path": book_path,
                "importance_score": 0.9  # Higher importance for reflection
            }
            
            reflection_memory_id = create_user_memory(
                db=db,
                user_id=user.id,
                context_info=context_info,
                original_content=reflection,
                model_name=model_name,
                metadata=metadata,
                source="book_reflection",
                importance=0.9
            )
            
            if reflection_memory_id:
                memory_ids.append(reflection_memory_id)
                logger.info(f"Created book reflection memory for user {username}")
        
        logger.info(f"Completed processing book '{book_title}' for user {username}")
        return memory_ids
        
    except Exception as e:
        logger.error(f"Failed to process book for user: {str(e)}")
        return None
    finally:
        if 'db' in locals():
            db.close() 