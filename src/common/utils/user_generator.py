"""
Utility functions for generating users using LLM.
"""

import logging
import sys
import json
import uuid
import random
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from sqlalchemy.orm import Session
from agir_db.models.user import User
from agir_db.db.session import get_db
from src.common.llm_provider import get_llm_model
from src.common.utils.memory_utils import create_user_memory, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

def generate_user_with_llm(
    db: Session, 
    role: str, 
    model_name: str,
    username: Optional[str] = None,
    scenario_id: Optional[Any] = None,
    scenario_description: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> Tuple[User, List[str]]:
    """
    Generate a user with LLM, including personal information and memories.
    
    Args:
        db: Database session
        role: Role of the user (e.g., 'student', 'teacher', etc.)
        model_name: LLM model name to use
        username: Optional username (will be generated if None)
        scenario_id: Optional scenario ID for context
        scenario_description: Optional scenario description for better user generation
        embedding_model: Optional embedding model name to use
        
    Returns:
        Tuple of (User, List[memories]) - the created user and list of memory IDs created
    """
    try:
        # Initialize LLM model
        llm = get_llm_model(model_name)
        
        # Generate unique username if not provided
        if not username:
            timestamp = int(time.time() * 1000) % 100000
            random_suffix = random.randint(100, 999)
            username = f"{role.lower()}_{timestamp:05d}_{random_suffix}"
        
        # Create prompt for LLM to generate user profile
        prompt = f"""
Generate a realistic profile for a user with the role of "{role}".
If provided, consider the following scenario context: {scenario_description or "No specific scenario"}.

Return the profile as a valid JSON object with the following fields:
{{
  "first_name": "First name of the user",
  "last_name": "Last name of the user",
  "email": "Email address or leave as null to be auto-generated",
  "gender": "Gender of the user: male, female, or other",
  "birth_date": "Birth date in YYYY-MM-DD format",
  "profession": "User's profession or occupation",
  "description": "A brief description/bio of the user",
  "avatar": "Leave null (will be generated separately if needed)",
  "is_active": true,
  "personality_traits": ["List", "of", "personality", "traits"],
  "background": "Background story or context about the user's life",
  "interests": ["List", "of", "user's", "interests"],
  "skills": ["List", "of", "user's", "skills"]
}}

Respond with ONLY the JSON object, nothing else.
"""
        
        # Generate user profile using LLM
        response = llm.invoke(prompt)
        
        # Extract content from response based on response type
        if hasattr(response, 'content'):
            user_data_str = response.content
        elif isinstance(response, dict) and 'text' in response:
            user_data_str = response['text']
        elif isinstance(response, dict) and 'content' in response:
            user_data_str = response['content']
        elif hasattr(response, 'text'):
            user_data_str = response.text
        else:
            user_data_str = str(response)
        
        # Clean up and parse the response
        user_data_str = user_data_str.strip()
        if user_data_str.startswith('```json'):
            user_data_str = user_data_str[7:]
        if user_data_str.endswith('```'):
            user_data_str = user_data_str[:-3]
        user_data_str = user_data_str.strip()
        
        # Parse JSON
        try:
            user_data = json.loads(user_data_str)
            logger.info(f"Successfully generated user profile with LLM for role: {role}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.debug(f"LLM response: {user_data_str}")
            # Fallback to basic user data
            user_data = {
                "first_name": "Auto",
                "last_name": "Generated",
                "gender": random.choice(["male", "female"]),
                "profession": role.capitalize(),
                "description": f"Auto-generated user for role: {role}"
            }
        
        # Process birth_date string to datetime if provided
        birth_date = None
        if user_data.get("birth_date"):
            try:
                birth_date = datetime.strptime(user_data["birth_date"], "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid birth_date format: {user_data['birth_date']}")
                
        # Set default or provided embedding model
        if not embedding_model:
            embedding_model = DEFAULT_EMBEDDING_MODEL
            
        # Set current time for timestamps
        now = datetime.now()
            
        # Create the user
        user = User(
            username=username,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            email=user_data.get("email") or f"{username}@agir.ai",
            gender=user_data.get("gender"),
            birth_date=birth_date,
            avatar=user_data.get("avatar"),
            description=user_data.get("description"),
            profession=user_data.get("profession"),
            personality_traits=user_data.get("personality_traits"),
            background=user_data.get("background"),
            interests=user_data.get("interests"),
            skills=user_data.get("skills"),
            is_active=user_data.get("is_active", True),
            llm_model=model_name,
            embedding_model=embedding_model,
            created_at=now,
            last_login_at=now
        )
        
        db.add(user)
        db.flush()  # Get ID without committing yet
        
        logger.info(f"Created new user: {username} with ID: {user.id}")
        
        # Generate memories for the user
        memory_ids = generate_user_memories(db, user.id, user_data, role, model_name, scenario_description)
        
        # Commit changes
        db.commit()
        db.refresh(user)
        
        return user, memory_ids
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate user with LLM: {str(e)}")
        raise

def generate_user_memories(
    db: Session, 
    user_id: Union[str, uuid.UUID], 
    user_data: Dict[str, Any],
    role: str,
    model_name: str,
    scenario_description: Optional[str] = None
) -> List[uuid.UUID]:
    """
    Generate memories for a user based on their profile data.
    
    Args:
        db: Database session
        user_id: ID of the user
        user_data: User profile data
        role: User's role
        model_name: LLM model to use
        scenario_description: Optional scenario description for context
        
    Returns:
        List[uuid.UUID]: List of generated memory IDs
    """
    memory_ids = []
    
    try:
        # Initialize LLM model
        llm = get_llm_model(model_name)
        
        # Extract relevant information for memory generation
        personality = ", ".join(user_data.get("personality_traits", []))
        interests = ", ".join(user_data.get("interests", []))
        skills = ", ".join(user_data.get("skills", []))
        background = user_data.get("background", "")
        
        # Generate prompt for memories
        prompt = f"""
Based on the following user profile, generate 3-5 distinct memories for this person that would influence their behavior and personality.
Each memory should be detailed and personal, covering various life stages.

User Profile:
- Role: {role}
- First Name: {user_data.get('first_name')}
- Last Name: {user_data.get('last_name')}
- Profession: {user_data.get('profession')}
- Personality Traits: {personality}
- Interests: {interests}
- Skills: {skills}
- Background: {background}

Scenario Context (if relevant): {scenario_description or "N/A"}

Format each memory as a paragraph describing a significant life event or experience.
Include emotions, lessons learned, and how it shaped the person. Make them realistic and detailed.

Return only the memories, each separated by three hyphens (---).
"""
        
        # Generate memories using LLM
        response = llm.invoke(prompt)
        
        # Extract content from response based on response type
        if hasattr(response, 'content'):
            memories_text = response.content
        elif isinstance(response, dict) and 'text' in response:
            memories_text = response['text']
        elif isinstance(response, dict) and 'content' in response:
            memories_text = response['content']
        elif hasattr(response, 'text'):
            memories_text = response.text
        else:
            memories_text = str(response)
        
        # Split into individual memories
        individual_memories = [m.strip() for m in memories_text.split('---') if m.strip()]
        
        # Create memory entries
        for i, memory_content in enumerate(individual_memories):
            # Context info for memory
            context_info = {
                "state_name": f"User {role} Memory",
                "task": f"Memory {i+1}",
                "content_type": "Personal Memory"
            }
            
            # Metadata for memory
            metadata = {
                "memory_type": "personal",
                "role": role,
                "generated": True,
                "importance_score": random.uniform(0.7, 1.0)  # Random high importance
            }
            
            # Create the memory
            memory_id = create_user_memory(
                db=db,
                user_id=user_id,
                context_info=context_info,
                original_content=memory_content,
                model_name=model_name,
                metadata=metadata,
                source="llm_generation",
                importance=metadata["importance_score"]
            )
            
            if memory_id:
                memory_ids.append(memory_id)
                logger.info(f"Created memory {i+1} for user {user_id}")
            
        logger.info(f"Generated {len(memory_ids)} memories for user {user_id}")
        return memory_ids
        
    except Exception as e:
        logger.error(f"Failed to generate memories for user {user_id}: {str(e)}")
        return memory_ids 