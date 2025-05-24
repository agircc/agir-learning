"""
Fast completion functionality without conversation history.
Uses FAISS-based memory retrieval for optimal performance.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.user import User
from src.llm.llm_provider import get_llm_model
from src.completions.fast_memory_retriever import get_fast_memory_retriever
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Simple user cache for fast lookups
_user_cache: Dict[str, User] = {}
_user_cache_limit = 100

def _get_cached_user(user_id: str) -> Optional[User]:
    """Get user from cache or database"""
    if user_id in _user_cache:
        return _user_cache[user_id]
    
    try:
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        
        # Cache the result (with size limit)
        if user and len(_user_cache) < _user_cache_limit:
            _user_cache[user_id] = user
        
        return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return None
    finally:
        if 'db' in locals():
            db.close()

class FastCompletion:
    """
    Fast completion class without conversation history.
    Optimized for speed with FAISS-based memory retrieval.
    """
    
    def __init__(self, user_id: str, temperature: float = 0.7, max_tokens: Optional[int] = None, model: Optional[str] = None):
        """
        Initialize fast completion
        
        Args:
            user_id: User ID for context
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
            model: Optional model name to override user's default model
        """
        self.user_id = user_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Get user info
        self.user = _get_cached_user(user_id)
        if not self.user:
            raise ValueError(f"User {user_id} not found")
        
        # Determine which model to use - prioritize passed-in model over user's model
        model_to_use = model or self.user.llm_model
        if not model_to_use:
            raise ValueError(f"No model specified and user {self.user.username} has no default LLM model")
        
        self.model_name = model_to_use
        
        # Initialize LLM
        self.llm = get_llm_model(
            model_to_use, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        # Initialize memory retriever
        self.memory_retriever = get_fast_memory_retriever(user_id)
        
        logger.info(f"Initialized fast completion for user {self.user.username} with {self.memory_retriever.get_memory_count()} memories")
    
    def _format_memories_for_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for LLM context"""
        if not memories:
            return "No specific memories available."
        
        formatted = "Relevant knowledge and memories:\n\n"
        for i, memory in enumerate(memories[:3]):  # Limit to top 3 for performance
            formatted += f"{i+1}. {memory['content']}\n\n"
        
        return formatted
    
    def complete(self, prompt: str) -> str:
        """
        Generate completion for the given prompt with enhanced thinking process
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated completion
        """
        try:
            relevant_memories = self.memory_retriever.search_memories(prompt, k=5)

 # Format memories for context
            memory_context = self._format_memories_for_context(relevant_memories)
            
            # Create system prompt with user context and memories
            system_prompt = f"""You are {self.user.first_name} {self.user.last_name}.
Respond based on your knowledge and the provided context.

{memory_context}

Provide a helpful, accurate response based on the above context."""
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            
            # Generate response
            response = self.llm.invoke(messages)
            
            # Extract content
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            return f"Error: {str(e)}"
    
        
    def complete_cot(self, prompt: str) -> str:
        """
        Generate completion for the given prompt with enhanced thinking process
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated completion
        """
        try:
            # Step 1: Search for initial relevant memories
            initial_memories = self.memory_retriever.search_memories(prompt, k=5)
            
            # Step 2: Analyze what knowledge is needed based on existing memories
            thinking_response = self._analyze_knowledge_needs(prompt, initial_memories)
            
            # Step 3: Search for additional memories based on analysis
            relevant_memories = self._search_memories_with_analysis(prompt, thinking_response, initial_memories)
            
            # Step 4: Generate final response with comprehensive context
            return self._generate_final_response(prompt, relevant_memories, thinking_response)
                
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            return f"Error: {str(e)}"
    
    def _analyze_knowledge_needs(self, prompt: str, existing_memories: List[Dict[str, Any]] = None) -> str:
        """
        Analyze what professional knowledge is needed to answer the prompt
        Based on user's existing memories and identify knowledge gaps
        
        Args:
            prompt: Input prompt
            existing_memories: Already found memories (optional)
            
        Returns:
            Analysis of knowledge requirements based on user's memories
        """
        try:
            # Use provided memories or search for new ones
            if existing_memories is None:
                existing_memories = self.memory_retriever.search_memories(prompt, k=5)
            
            # Format existing knowledge
            existing_knowledge = self._format_existing_knowledge(existing_memories)
            
            # Analyze what additional knowledge is needed
            analysis_prompt = f"""Based on the following question and your existing knowledge/experience, analyze what additional professional knowledge might be needed to provide a comprehensive answer.

QUESTION: {prompt}

YOUR EXISTING RELEVANT KNOWLEDGE/EXPERIENCE:
{existing_knowledge}

ANALYSIS TASK:
1. What specific professional domains or fields are most relevant to this question?
2. Based on your existing knowledge above, what additional concepts, theories, or principles would be helpful?
3. What practical experience or examples beyond what you already know would strengthen the answer?
4. Are there any technical terms, methodologies, or specialized knowledge areas not covered in your existing knowledge?

Provide a structured analysis in 2-3 sentences that identifies:
- Key knowledge domains that are relevant
- Specific gaps or additional perspectives that would be valuable
- How your existing knowledge can be enhanced or supplemented"""

            messages = [
                SystemMessage(content=f"You are {self.user.first_name} {self.user.last_name}, analyzing what additional knowledge you need to comprehensively answer a question based on your existing knowledge and experience."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = self.llm.invoke(messages)
            analysis = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Knowledge analysis completed based on {len(existing_memories)} existing memories for prompt: {prompt[:50]}...")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in knowledge analysis: {str(e)}")
            return "General knowledge and experience would be helpful for answering this question."
    
    def _format_existing_knowledge(self, memories: List[Dict[str, Any]]) -> str:
        """Format existing memories for knowledge analysis"""
        if not memories:
            return "No specific relevant knowledge or experience found in your memory."
        
        formatted = ""
        for i, memory in enumerate(memories, 1):
            content = memory.get('content', '')
            # Limit each memory to avoid overwhelming the analysis
            if len(content) > 200:
                content = content[:200] + "..."
            formatted += f"Knowledge {i}: {content}\n\n"
        
        return formatted.strip()
    
    def _search_memories_with_analysis(self, prompt: str, analysis: str, initial_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Search for additional memories using knowledge analysis, combining with initial memories
        
        Args:
            prompt: Original prompt
            analysis: Knowledge analysis result
            initial_memories: Already found memories from initial search
            
        Returns:
            List of comprehensive relevant memories
        """
        try:
            # Extract key terms from analysis for targeted search
            analysis_search_terms = self._extract_search_terms_from_analysis(analysis)
            
            # Search for additional memories using analysis terms
            additional_memories = []
            if analysis_search_terms:
                additional_memories = self.memory_retriever.search_memories(analysis_search_terms, k=3)
            
            # Combine all memories and deduplicate
            all_memories = []
            seen_ids = set()
            
            # Add initial memories first (they're most relevant to original prompt)
            for memory in initial_memories:
                if memory.get('id') not in seen_ids:
                    all_memories.append(memory)
                    seen_ids.add(memory.get('id'))
            
            # Add additional memories from analysis
            for memory in additional_memories:
                if memory.get('id') not in seen_ids:
                    all_memories.append(memory)
                    seen_ids.add(memory.get('id'))
            
            # Sort by relevance/importance and limit to top 5
            all_memories = sorted(all_memories, 
                                key=lambda x: x.get('importance', 1.0), 
                                reverse=True)[:5]
            
            logger.info(f"Combined {len(initial_memories)} initial + {len(additional_memories)} analysis-based memories = {len(all_memories)} total unique memories")
            return all_memories
            
        except Exception as e:
            logger.error(f"Error in enhanced memory search: {str(e)}")
            # Fallback to initial memories
            return initial_memories[:4]
    
    def _extract_search_terms_from_analysis(self, analysis: str) -> str:
        """
        Extract key search terms from knowledge analysis
        
        Args:
            analysis: Knowledge analysis text
            
        Returns:
            Extracted key terms for searching
        """
        try:
            # Simple extraction of important terms - could be enhanced with NLP
            important_words = []
            
            # Look for domain-specific terms, methodologies, etc.
            words = analysis.lower().split()
            
            # Skip common words and focus on substantive terms
            skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'would', 'could', 'should', 'need', 'needs', 'knowledge', 'experience', 'understanding'}
            
            for word in words:
                # Clean the word
                clean_word = word.strip('.,!?();:"')
                if len(clean_word) > 3 and clean_word not in skip_words:
                    important_words.append(clean_word)
            
            # Take up to 5 most relevant terms
            search_terms = ' '.join(important_words[:5])
            
            logger.debug(f"Extracted search terms from analysis: {search_terms}")
            return search_terms
            
        except Exception as e:
            logger.error(f"Error extracting search terms: {str(e)}")
            return ""
    
    def _generate_final_response(self, prompt: str, memories: List[Dict[str, Any]], analysis: str) -> str:
        """
        Generate the final response using comprehensive context
        
        Args:
            prompt: Original prompt
            memories: Relevant memories
            analysis: Knowledge analysis
            
        Returns:
            Final response
        """
        try:
            # Format memories for context
            memory_context = self._format_memories_for_context(memories)
            
            # Create enhanced system prompt
            system_prompt = f"""You are {self.user.first_name} {self.user.last_name}, an expert with deep knowledge and experience.

KNOWLEDGE ANALYSIS:
{analysis}

RELEVANT KNOWLEDGE AND EXPERIENCE:
{memory_context}

INSTRUCTIONS:
1. Draw upon the relevant knowledge and experience provided above
2. Consider the professional domains and concepts identified in the analysis
3. Provide a comprehensive, well-structured answer that demonstrates expertise
4. Include specific details, examples, or practical insights where relevant
5. Ensure the response directly addresses the question asked

Respond as the expert you are, using your knowledge to provide valuable insights."""

            # Create messages for final response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Based on your expertise and the relevant knowledge provided, please answer this question comprehensively:\n\n{prompt}")
            ]
            
            # Generate final response
            response = self.llm.invoke(messages)
            final_answer = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Generated comprehensive response for prompt: {prompt[:50]}...")
            return final_answer
            
        except Exception as e:
            logger.error(f"Error generating final response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "user_id": self.user_id,
            "username": self.user.username,
            "memory_count": self.memory_retriever.get_memory_count(),
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

def create_fast_completion(user_id: str, temperature: float = 0.7, max_tokens: Optional[int] = None, model: Optional[str] = None) -> Optional[FastCompletion]:
    """
    Create a fast completion instance
    
    Args:
        user_id: User ID
        temperature: LLM temperature
        max_tokens: Maximum tokens to generate
        model: Optional model name to override user's default model
        
    Returns:
        FastCompletion instance or None if failed
    """
    try:
        return FastCompletion(user_id, temperature, max_tokens, model)
    except Exception as e:
        logger.error(f"Failed to create fast completion: {str(e)}")
        return None 