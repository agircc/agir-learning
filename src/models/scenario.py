"""
Scenario model
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class State(BaseModel):
    """
    Represents a state in the scenario graph.
    
    Attributes:
        id: Unique identifier for the state
        name: Name of the state
        description: Description of the state
        roles: List of roles that can participate in this state
        assigned_to: Role that this state is assigned to
    """
    id: str
    name: str
    description: str
    roles: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None


class StateTransition(BaseModel):
    """
    Represents a transition between states in the scenario graph.
    
    Attributes:
        from_state: ID of the source state
        to_state: ID of the target state
        condition: Optional condition for the transition
    """
    from_state_name: str
    to_state_name: str
    condition: str = ""


class Scenario(BaseModel):
    """
    Represents a scenario definition with states and transitions.
    
    Attributes:
        name: Name of the scenario
        description: Description of the scenario
        states: List of states in the scenario
        transitions: List of transitions between states
        roles: List of roles in the scenario
        learner: Dictionary containing learner information
        learner_role: Role of the learner
        evolution: Dictionary containing evolution information
    """
    name: str
    description: Optional[str] = None
    states: List[State] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)
    roles: List[Any] = Field(default_factory=list)
    learner: Dict[str, Any] = Field(default_factory=dict)
    learner_role: Optional[str] = None
    evolution: Dict[str, Any] = Field(default_factory=dict)
    
    def get_state(self, state_id: str) -> Optional[State]:
        """
        Get a state by ID.
        
        Args:
            state_id: ID of the state to find
            
        Returns:
            State if found, None otherwise
        """
        for state in self.states:
            if state.id == state_id:
                return state
        return None
    
    def get_state_by_name(self, state_name: str) -> Optional[State]:
        """
        Get a state by name.
        
        Args:
            state_name: Name of the state to find
            
        Returns:
            State if found, None otherwise
        """
        for state in self.states:
            if state.name == state_name:
                return state
        return None
    
    def next_states(self, state_id: str) -> List[State]:
        """
        Get all states that can be reached from the given state.
        
        Args:
            state_id: ID of the source state
            
        Returns:
            List of states that can be reached from the given state
        """
        next_state_ids = []
        for transition in self.transitions:
            if transition.from_state == state_id:
                next_state_ids.append(transition.to_state)
        
        next_states = []
        for state_id in next_state_ids:
            state = self.get_state(state_id)
            if state:
                next_states.append(state)
        
        return next_states
    
    def terminal_states(self) -> List[State]:
        """
        Get all terminal states in the scenario.
        
        Terminal states are states that have no outgoing transitions.
        
        Returns:
            List of terminal states
        """
        # Get all states that have outgoing transitions
        states_with_outgoing = set()
        for transition in self.transitions:
            states_with_outgoing.add(transition.from_state)
        
        # Find states that don't have outgoing transitions
        terminal_states = []
        for state in self.states:
            if state.id not in states_with_outgoing:
                terminal_states.append(state)
        
        return terminal_states
    
    def initial_states(self) -> List[State]:
        """
        Get all initial states in the scenario.
        
        Initial states are states that have no incoming transitions.
        
        Returns:
            List of initial states
        """
        # Get all states that have incoming transitions
        states_with_incoming = set()
        for transition in self.transitions:
            states_with_incoming.add(transition.to_state)
        
        # Find states that don't have incoming transitions
        initial_states = []
        for state in self.states:
            if state.id not in states_with_incoming:
                initial_states.append(state)
        
        return initial_states
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the scenario to a dictionary.
        
        Returns:
            Dictionary representation of the scenario
        """
        return {
            "name": self.name,
            "description": self.description,
            "states": [state.dict() for state in self.states],
            "transitions": [transition.dict() for transition in self.transitions],
            "roles": [role.dict() if hasattr(role, "dict") else role for role in self.roles],
            "learner": self.learner,
            "learner_role": self.learner_role,
            "evolution": self.evolution
        }
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Scenario":
        """
        Create a scenario from YAML content.
        
        Args:
            yaml_content: YAML content to parse
            
        Returns:
            A new Scenario instance
        """
        import yaml
        data = yaml.safe_load(yaml_content)
        
        scenario_data = data.get("scenario", {})
        
        states = []
        for state_data in scenario_data.get("states", []):
            states.append(State(
                id=state_data.get("id", state_data["name"]),
                name=state_data["name"],
                description=state_data["description"],
                roles=state_data.get("roles", [])
            ))
        
        transitions = []
        for transition_data in scenario_data.get("transitions", []):
            transitions.append(StateTransition(
                from_state_name=transition_data["from_state_name"],
                to_state_name=transition_data["to_state_name"],
                condition=transition_data.get("condition", "")
            ))
        
        return cls(
            name=scenario_data.get("name", "Unnamed Scenario"),
            description=scenario_data.get("description"),
            learner=scenario_data.get("learner", {}),
            states=states,
            transitions=transitions,
            evolution=scenario_data.get("evolution", {})
        ) 