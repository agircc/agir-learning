"""
YAML Validator for scenario files
"""
import logging
import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator, field_validator
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class LearnerModel(BaseModel):
    username: str
    model: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    profession: Optional[str] = None
    skills: Optional[List[str]] = None
    evolution_objective: Optional[str] = None

class RoleModel(BaseModel):
    name: str
    model: str
    description: Optional[str] = None

class StateModel(BaseModel):
    name: str
    roles: Optional[List[str]] = None
    description: str
    
    @model_validator(mode='after')
    def validate_roles_field(self):
        """Ensure that 'roles' is provided"""
        if self.roles is None:
            raise ValueError("'roles' must be defined in state")
            
        return self

class TransitionModel(BaseModel):
    from_state_name: Optional[str] = None
    to_state_name: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    condition: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_from_to_fields(self):
        """Ensure that either from_state_name/to_state_name or from/to is provided"""
        # Handle from/to format
        if self.from_state_name is None and self.from_ is not None:
            self.from_state_name = self.from_
        
        if self.to_state_name is None and self.to is not None:
            self.to_state_name = self.to
            
        # Validate required fields
        if self.from_state_name is None:
            raise ValueError("Either 'from_state_name' or 'from' must be defined in transition")
            
        if self.to_state_name is None:
            raise ValueError("Either 'to_state_name' or 'to' must be defined in transition")
            
        return self

class ScenarioModel(BaseModel):
    name: str
    description: str
    learner_role: str
    learner: LearnerModel
    roles: List[RoleModel]
    states: List[StateModel]
    transitions: List[TransitionModel]

    @model_validator(mode='after')
    def validate_roles_and_states(self):
        """Validate that all roles in states exist in the roles list and learner_role exists."""
        roles = [role.name for role in self.roles]
        learner_role = self.learner_role
        
        # Check if learner_role exists in roles
        if learner_role not in roles:
            raise ValueError(f"learner_role '{learner_role}' not found in defined roles")
        
        # Check all roles used in states exist in role definitions
        for state in self.states:
            for role in state.roles:
                if role not in roles:
                    raise ValueError(f"Role '{role}' in state '{state.name}' not found in defined roles")
        
        # Validate transitions refer to existing states
        state_names = [state.name for state in self.states]
        for transition in self.transitions:
            if transition.from_state_name not in state_names:
                raise ValueError(f"Transition from state '{transition.from_state_name}' refers to non-existent state")
            if transition.to_state_name not in state_names:
                raise ValueError(f"Transition to state '{transition.to_state_name}' refers to non-existent state")
        
        return self

class YamlModel(BaseModel):
    scenario: ScenarioModel

def validate_yaml_file(file_path: str) -> bool:
    """
    Validates a YAML file against the required scenario structure.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    try:
        with open(file_path, 'r') as file:
            yaml_content = yaml.safe_load(file)
            
        # Validate with Pydantic
        YamlModel(**yaml_content)
        return True
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return False
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {file_path}: {str(e)}")
        return False
    except ValidationError as e:
        logger.error(f"Validation error in {file_path}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating {file_path}: {str(e)}")
        return False 