"""
Agent model for AGIR Learning
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid


class Agent(BaseModel):
    """
    Represents an LLM-powered agent in the AGIR Learning system.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    knowledge_base: Dict[str, Any] = Field(default_factory=dict)
    memory: List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    
    def build_system_prompt(self) -> str:
        """
        Build a system prompt for the agent based on its role, description, skills, etc.
        
        Returns:
            A formatted system prompt string
        """
        prompt_parts = []
        
        prompt_parts.append(f"You are {self.name}, a {self.role}.")
        
        if self.description:
            prompt_parts.append(self.description)
            
        if self.skills:
            skills_str = ", ".join(self.skills)
            prompt_parts.append(f"Your skills include: {skills_str}.")
            
        if self.system_prompt:
            prompt_parts.append(self.system_prompt)
            
        if self.memory:
            prompt_parts.append("Relevant past experiences:")
            for i, memory in enumerate(self.memory[-5:], 1):  # Include last 5 memories
                prompt_parts.append(f"{i}. {memory['content']}")
                
        return "\n\n".join(prompt_parts)
    
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new memory to the agent's memory storage.
        
        Args:
            content: The content of the memory
            metadata: Optional metadata about the memory
        """
        if metadata is None:
            metadata = {}
            
        self.memory.append({
            "content": content,
            "metadata": metadata
        })
        
    def update_knowledge(self, key: str, value: Any) -> None:
        """
        Update the agent's knowledge base.
        
        Args:
            key: The knowledge key
            value: The knowledge value
        """
        self.knowledge_base[key] = value 