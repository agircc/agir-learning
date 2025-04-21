"""
Role model for AGIR Learning
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid


class Role(BaseModel):
    """
    Represents a role that can be assigned to agents in the process.
    """
    id: str
    name: str
    description: str
    system_prompt_template: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    knowledge_sources: List[str] = Field(default_factory=list)
    
    def format_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """
        Format the system prompt template with context variables.
        
        Args:
            context: Dictionary of context variables
            
        Returns:
            Formatted system prompt
        """
        if not self.system_prompt_template:
            # Default system prompt if not provided
            base_prompt = f"You are a {self.name}. {self.description}"
            
            # Add required skills if present
            if self.required_skills:
                skills_str = ", ".join(self.required_skills)
                base_prompt += f"\n\nYour skills include: {skills_str}."
                
            # Add knowledge sources if present
            if self.knowledge_sources:
                sources_str = ", ".join(self.knowledge_sources)
                base_prompt += f"\n\nYou have knowledge from: {sources_str}."
                
            return base_prompt
            
        # Use template if provided
        if not context:
            context = {}
            
        # Add role info to context
        context.update({
            "role_name": self.name,
            "role_description": self.description,
            "role_skills": self.required_skills,
            "role_knowledge_sources": self.knowledge_sources
        })
        
        try:
            return self.system_prompt_template.format(**context)
        except KeyError as e:
            # Fall back to default if template has missing keys
            return f"Template error ({str(e)}). You are a {self.name}. {self.description}" 