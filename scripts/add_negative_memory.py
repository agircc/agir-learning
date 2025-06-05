#!/usr/bin/env python3
"""
Script to add negative memories for all users in the database.
This script generates realistic negative memories based on each user's existing memories.
"""

import sys
import os
import argparse
import logging
import uuid
from typing import List, Dict, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from agir_db.db.session import get_db
from agir_db.models.user import User
from src.common.utils.memory_utils import get_user_memories, create_user_memory
from src.completions.fast_memory_retriever import get_fast_memory_retriever
from src.llm.llm_provider import get_llm_model

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def search_user_memories_with_query(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search user memories using cached FastMemoryRetriever.
    
    Args:
        user_id: User ID to search memories for
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of memory dictionaries
    """
    try:
        memory_retriever = get_fast_memory_retriever(user_id)
        memories = memory_retriever.search_memories(query, k=limit)
        
        # Convert to expected format
        result = []
        for memory in memories:
            result.append({
                'id': memory.get('id'),
                'content': memory.get('content'),
                'importance': memory.get('importance', 1.0),
                'created_at': memory.get('created_at'),
                'source': memory.get('source', 'unknown')
            })
        
        return result
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        return []

def find_memories_needing_negative_examples(user: User) -> List[Dict[str, Any]]:
    """
    Find memories that might benefit from negative examples.
    
    Args:
        user: User object
        
    Returns:
        List of memory dictionaries that might need negative examples
    """
    try:
        # Search for memories related to different topics
        queries = [
            "business strategy advice",
            "investment recommendations", 
            "financial advice",
            "career guidance",
            "health recommendations",
            "technical solutions",
            "marketing strategies"
        ]
        
        all_memories = []
        seen_ids = set()
        
        for query in queries:
            memories = search_user_memories_with_query(str(user.id), query, limit=5)
            for memory in memories:
                if memory['id'] not in seen_ids:
                    all_memories.append(memory)
                    seen_ids.add(memory['id'])
        
        return all_memories[:10]  # Return top 10 unique memories
        
    except Exception as e:
        logger.error(f"Error finding memories: {str(e)}")
        return []

def generate_negative_memory_prompt(user: User, existing_memories: List[Dict[str, Any]]) -> str:
    """
    Generate a prompt for creating a negative memory based on user profile and existing memories.
    
    Args:
        user: User object from database
        existing_memories: List of existing user memories (from vector search)
        
    Returns:
        str: Formatted prompt for LLM
    """
    # Extract key information from existing memories (these are already relevant from vector search)
    memory_contexts = []
    for memory in existing_memories[:5]:  # Use top 5 most relevant memories
        content = memory.get('content', '')
        if content:
            # Include score if available to show relevance
            score_info = f" (relevance: {memory.get('score', 'N/A')})" if 'score' in memory else ""
            memory_contexts.append(f"- {content[:200]}...{score_info}")  # Truncate for context
    
    existing_context = "\n".join(memory_contexts) if memory_contexts else "No existing memories available."
    
    prompt = f"""You are {user.first_name} {user.last_name}, a real person recalling a painful or uncomfortable memory from your past.

Based on your most relevant existing life experiences and memories:
{existing_context}

Please describe a realistic negative memory that fits with your life story. This memory can come from any part of life—such as illness, the loss of a loved one, failure, rejection, loneliness, conflict, shame, fear, or any other experience that left a lasting emotional impact.

Please describe:
- What happened?
- How old were you and where did it take place?
- What was the environment like? Any specific details or dialogue?
- How did you feel at the time?
- How did this experience affect you later in life?

Requirements:
- Be as specific and realistic as possible—not vague or overly abstract
- Make it consistent with your existing memories and life experiences shown above
- Focus on a different type of negative experience than what's already in your memories
- Avoid repetitive formats or stories
- Do not include a positive takeaway or emotional resolution
- Write in first person as if you are recalling this memory
- Keep it between 150-300 words

Return only the memory description, nothing else."""

    return prompt

def generate_negative_memory_for_user(
    db: Session, 
    user: User, 
    model_name: str = "gpt-4.1-nano"
) -> Optional[str]:
    """
    Generate and add a negative memory for a specific user.
    
    Args:
        db: Database session
        user: User object
        model_name: LLM model to use
        
    Returns:
        Optional[str]: Memory ID if successful, None otherwise
    """
    try:
        # Use vector search to get relevant memories for context
        # Search query focused on finding memories related to personal experiences, emotions, and life events
        search_queries = [
            "personal experiences emotions feelings life events",
            "childhood memories family relationships challenges",
            "important life moments emotional experiences"
        ]
        
        existing_memories = []
        for query in search_queries:
            memories = search_user_memories_with_query(str(user.id), query, limit=5)
            existing_memories.extend(memories)
        
        # Remove duplicates based on memory ID
        seen_ids = set()
        unique_memories = []
        for memory in existing_memories:
            if memory['id'] not in seen_ids:
                unique_memories.append(memory)
                seen_ids.add(memory['id'])
        
        # Sort by relevance score (lower score = more relevant in FAISS distance)
        unique_memories.sort(key=lambda x: x.get('score', float('inf')))
        
        # Take top 10 most relevant memories
        existing_memories = unique_memories[:10]
        
        if not existing_memories:
            logger.warning(f"No relevant memories found for user {user.username} ({user.id})")
            # Fallback to basic get_user_memories if vector search fails
            existing_memories = get_user_memories(str(user.id), limit=5)
        else:
            logger.info(f"Found {len(existing_memories)} relevant memories for user {user.username} using vector search")
        
        # Generate prompt
        prompt = generate_negative_memory_prompt(user, existing_memories)
        
        # Get LLM model
        llm = get_llm_model(model_name)
        
        # Generate the negative memory
        logger.info(f"Generating negative memory for user {user.username}...")
        response = llm.invoke(prompt)
        
        # Extract content from response
        if hasattr(response, 'content'):
            memory_content = response.content
        elif isinstance(response, dict) and 'text' in response:
            memory_content = response['text']
        elif isinstance(response, dict) and 'content' in response:
            memory_content = response['content']
        elif hasattr(response, 'text'):
            memory_content = response.text
        else:
            memory_content = str(response)
        
        memory_content = memory_content.strip()
        
        if not memory_content:
            logger.error(f"Empty memory content generated for user {user.username}")
            return None
        
        # Context info for memory creation
        context_info = {
            "state_name": "Negative Memory Addition",
            "task": "Generate negative personal memory",
            "content_type": "Personal Traumatic Memory"
        }
        
        # Metadata for the memory
        metadata = {
            "memory_type": "personal_negative",
            "generated": True,
            "source_script": "add_negative_memory.py",
            "memory_category": "traumatic_experience",
            "emotional_valence": "negative"
        }
        
        # Create the memory in database
        memory_id = create_user_memory(
            db=db,
            user_id=user.id,
            context_info=context_info,
            original_content=memory_content,
            model_name=model_name,
            metadata=metadata,
            source="script_generation",
            importance=0.9  # High importance for negative memories
        )
        
        if memory_id:
            logger.info(f"Successfully created negative memory {memory_id} for user {user.username}")
            return str(memory_id)
        else:
            logger.error(f"Failed to create memory for user {user.username}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating negative memory for user {user.username}: {str(e)}")
        return None

def add_negative_memories_to_all_users(
    model_name: str = "gpt-4.1-nano",
    limit: Optional[int] = None,
    skip_existing: bool = True
):
    """
    Add negative memories to all users in the database.
    
    Args:
        model_name: LLM model to use
        limit: Optional limit on number of users to process
        skip_existing: Whether to skip users who already have negative memories
    """
    try:
        db = next(get_db())
        
        # Get all active users
        query = db.query(User).filter(User.is_active == True)
        if limit:
            query = query.limit(limit)
        
        users = query.all()
        logger.info(f"Found {len(users)} active users to process")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, user in enumerate(users, 1):
            logger.info(f"Processing user {i}/{len(users)}: {user.username} ({user.id})")
            
            # Check if user already has negative memories
            if skip_existing:
                existing_memories = get_user_memories(str(user.id), limit=50)
                has_negative = any(
                    mem.get('meta_data', {}).get('memory_type') == 'personal_negative' 
                    for mem in existing_memories
                )
                if has_negative:
                    logger.info(f"User {user.username} already has negative memories, skipping")
                    skip_count += 1
                    continue
            
            # Generate negative memory
            memory_id = generate_negative_memory_for_user(db, user, model_name)
            
            if memory_id:
                success_count += 1
                logger.info(f"✓ Successfully added negative memory for {user.username}")
            else:
                error_count += 1
                logger.error(f"✗ Failed to add negative memory for {user.username}")
        
        # Summary
        logger.info(f"\n=== SUMMARY ===")
        logger.info(f"Total users processed: {len(users)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Skipped (already have negative memories): {skip_count}")
        logger.info(f"Errors: {error_count}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        if 'db' in locals():
            db.close()

def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(description="Add negative memories for all users")
    parser.add_argument(
        "--model", 
        default="gpt-4.1-nano", 
        help="LLM model to use (default: gpt-4.1-nano)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        help="Limit number of users to process"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Process all users even if they already have negative memories"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting negative memory addition process...")
    logger.info(f"Model: {args.model}")
    logger.info(f"Limit: {args.limit or 'No limit'}")
    logger.info(f"Force mode: {args.force}")
    
    add_negative_memories_to_all_users(
        model_name=args.model,
        limit=args.limit,
        skip_existing=not args.force
    )
    
    logger.info("Process completed!")

if __name__ == "__main__":
    main()