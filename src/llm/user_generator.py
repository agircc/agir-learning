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
from src.llm.llm_provider import get_llm_model
from src.common.utils.memory_utils import create_user_memory, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

def generate_user_with_llm(
    db: Session, 
    role: str, 
    model_name: str,
    username: Optional[str] = None,
    scenario_id: Optional[Any] = None,
    scenario_description: Optional[str] = None,
    embedding_model: Optional[str] = None,
    existing_profile: Optional[Dict[str, Any]] = None
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
        existing_profile: Optional existing profile data to merge with LLM generation
        
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

IMPORTANT: Generate unique and diverse names. Avoid common combinations like "Alex Johnson" or other frequently used names.
Choose creative, distinctive, and culturally diverse first and last names that are not likely to be duplicated.

Return the profile as a valid JSON object with the following fields:
{{
  "first_name": "Unique first name of the user (avoid common names like Alex, John, etc.)",
  "last_name": "Unique last name of the user (avoid common names like Johnson, Smith, etc.)",
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

        # Merge with existing profile if provided
        if existing_profile:
            # For list fields, combine unique values
            list_fields = ["personality_traits", "interests", "skills"]
            for field in list_fields:
                if field in existing_profile and field in user_data:
                    existing_values = set(existing_profile[field])
                    new_values = set(user_data[field])
                    user_data[field] = list(existing_values.union(new_values))
                elif field in existing_profile:
                    user_data[field] = existing_profile[field]
            
            # For string fields, prefer existing values if they exist
            string_fields = ["first_name", "last_name", "gender", "birth_date", "profession", "description", "background"]
            for field in string_fields:
                if field in existing_profile and existing_profile[field]:
                    user_data[field] = existing_profile[field]
        
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
            email=f"{username}@agir.cc",  # Always use username@agir.cc format to avoid duplicates
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
        
        # Generate prompt for memories with comprehensive categories
        prompt = f"""
Based on the following user profile, generate an array of 12-15 distinct, highly detailed memories that would make this person feel like a real individual with a rich life history.
The memories should cover different aspects of their life and include specific details to make them realistic (exact locations, company names, names of people, etc.).

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

Include memories from the following categories:

1. Basic Life History (birthplace with specific city, childhood locations, relocations)
2. Family Background (siblings, parents, family dynamics, specific family events)
3. Education Journey (specific schools, teachers, classes, memorable experiences)
4. Career Path (first job with company name, career transitions, projects)
5. Relationships & Social Life (friendships, romantic relationships, community involvement)
6. Personal Events & Turning Points (milestones, challenges, travel experiences with actual locations)
7. Hobbies & Interests (childhood activities, current hobbies, skill development)
8. Digital & Tech Life (first devices, online communities, technology experiences)
9. Health & Lifestyle (health events, habit changes, fitness milestones)
10. Unexpected Moments (surprises, accidents, coincidences that impacted them)

Return the memories as a JSON array where each memory object has the following structure:
[
  {{
    "title": "Brief title for the memory",
    "content": "Highly detailed description of the memory including specific names, places, companies, emotions, impact, and lessons learned",
    "age": "Approximate age when this memory occurred",
    "life_stage": "childhood/adolescence/young_adult/adult",
    "importance": "A value from 0.7 to 1.0 indicating how important this memory is to the person",
    "emotions": ["list", "of", "emotions", "felt"],
    "category": "The category this memory belongs to (e.g., family_background, career_path)"
  }},
  ...more memories
]

Make the memories extremely specific and detailed - like entries in a personal journal. Include concrete details like:
- Exact locations (cities, countries, neighborhoods)
- Names of institutions (schools, companies, organizations)
- Names of people involved
- Sensory details (what they saw, heard, felt)
- The impact this memory had on their life choices or personality

Respond with ONLY the JSON array, nothing else.
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
        
        # Clean up response for JSON parsing
        memories_text = memories_text.strip()
        if memories_text.startswith('```json'):
            memories_text = memories_text[7:]
        if memories_text.endswith('```'):
            memories_text = memories_text[:-3]
        memories_text = memories_text.strip()
        
        # Parse JSON array of memories
        try:
            memories_array = json.loads(memories_text)
            if not isinstance(memories_array, list):
                logger.error("LLM did not return a list of memories")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse memories as JSON: {str(e)}")
            logger.debug(f"LLM response: {memories_text}")
            try:
                cleaned_text = memories_text.replace(",\n]", "\n]").replace(",]", "]")
                memories_array = json.loads(cleaned_text)
                logger.info("Successfully fixed JSON formatting issues")
            except:
                logger.error("Could not repair JSON, skipping memory generation")
                return []
        
        # Create memory entries for each memory in the array
        successful_memories = 0
        for i, memory_obj in enumerate(memories_array):
            try:
                if not isinstance(memory_obj, dict):
                    logger.error(f"Memory {i+1} is not a valid dictionary object, skipping")
                    continue
                    
                # Get memory content and metadata
                memory_content = memory_obj.get("content", "")
                if not memory_content:
                    logger.error(f"Memory {i+1} is missing content, skipping")
                    continue
                    
                # Validate required memory fields
                skip_memory = False
                required_fields = ["title", "age", "life_stage", "importance"]
                for field in required_fields:
                    if field not in memory_obj or not memory_obj[field]:
                        logger.error(f"Memory {i+1} is missing required field: {field}, skipping")
                        skip_memory = True
                        break
                
                if skip_memory:
                    continue
                
                try:
                    importance = float(memory_obj.get("importance", 0.8))
                    if importance < 0.1 or importance > 1.0:
                        importance = 0.8
                except (ValueError, TypeError):
                    importance = 0.8
                    
                # Context info for memory
                context_info = {
                    "state_name": f"User {role} Memory",
                    "task": memory_obj.get("title", "Memory"),
                    "content_type": "Personal Memory"
                }
                
                # Metadata for memory
                metadata = {
                    "memory_type": "personal",
                    "role": role,
                    "generated": True,
                    "title": memory_obj.get("title", "Untitled Memory"),
                    "age": memory_obj.get("age", "Unknown"),
                    "life_stage": memory_obj.get("life_stage", "adult"),
                    "emotions": memory_obj.get("emotions", []),
                    "importance_score": importance,
                    "category": memory_obj.get("category", "general")
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
                    successful_memories += 1
                    logger.info(f"Created memory {i+1} ({metadata['category']}: {metadata['life_stage']}) for user {user_id}")
            except Exception as mem_error:
                logger.error(f"Error processing memory {i+1}: {str(mem_error)}")
                continue
            
        logger.info(f"Generated {successful_memories} detailed memories for user {user_id}")
        return memory_ids
        
    except Exception as e:
        logger.error(f"Failed to generate memories for user {user_id}: {str(e)}")
        return memory_ids 