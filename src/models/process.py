"""
Process model
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, validator
import uuid
import yaml
from .role import Role


class ProcessNode(BaseModel):
    """
    Represents a node in the process graph.
    """
    id: str
    name: str
    role: str
    description: str
    assigned_to: Optional[str] = None


class ProcessTransition(BaseModel):
    """
    Represents a transition between nodes in the process graph.
    """
    from_node: str
    to_node: str


class Process(BaseModel):
    """
    Represents a process definition with nodes and transitions.
    """
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    learner: Dict[str, Any] = Field(default_factory=dict)
    nodes: List[ProcessNode] = Field(default_factory=list)
    transitions: List[ProcessTransition] = Field(default_factory=list)
    roles: List[Role] = Field(default_factory=list)
    evolution: Dict[str, Any] = Field(default_factory=dict)
    
    def get_node(self, node_id: str) -> Optional[ProcessNode]:
        """
        Get a node by its ID.
        
        Args:
            node_id: ID of the node
            
        Returns:
            The node with matching ID, or None if not found
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """
        Get a role by its ID.
        
        Args:
            role_id: ID of the role
            
        Returns:
            The role with matching ID, or None if not found
        """
        for role in self.roles:
            if role.id == role_id:
                return role
        return None
    
    def next_nodes(self, node_id: str) -> List[ProcessNode]:
        """
        Get the next nodes for a given node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            A list of next nodes
        """
        next_nodes = []
        for transition in self.transitions:
            if transition.from_node == node_id:
                next_node_id = transition.to_node
                next_node = self.get_node(next_node_id)
                if next_node:
                    next_nodes.append(next_node)
        return next_nodes
    
    def terminal_nodes(self) -> List[ProcessNode]:
        """
        Get all terminal nodes in the process.
        
        A terminal node is a node with no outgoing transitions.
        
        Returns:
            A list of terminal nodes
        """
        # Get all nodes with outgoing transitions
        nodes_with_outgoing = set()
        for transition in self.transitions:
            nodes_with_outgoing.add(transition.from_node)
        
        # Find all nodes that are not in the above set
        terminal_nodes = []
        for node in self.nodes:
            if node.id not in nodes_with_outgoing:
                terminal_nodes.append(node)
        
        return terminal_nodes
    
    def initial_nodes(self) -> List[ProcessNode]:
        """
        Get all initial nodes in the process.
        
        An initial node is a node with no incoming transitions.
        
        Returns:
            A list of initial nodes
        """
        # Get all nodes with incoming transitions
        nodes_with_incoming = set()
        for transition in self.transitions:
            nodes_with_incoming.add(transition.to_node)
        
        # Find all nodes that are not in the above set
        initial_nodes = []
        for node in self.nodes:
            if node.id not in nodes_with_incoming:
                initial_nodes.append(node)
        
        return initial_nodes
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the process to a dictionary.
        
        Returns:
            Dictionary representation of the process
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "learner": self.learner,
            "nodes": [node.dict() for node in self.nodes],
            "transitions": [transition.dict() for transition in self.transitions],
            "roles": [role.dict() for role in self.roles],
            "evolution": self.evolution
        }
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Process":
        """
        Create a process from YAML content.
        
        Args:
            yaml_content: The YAML content
            
        Returns:
            A new Process instance
        """
        data = yaml.safe_load(yaml_content)
        process_data = data.get("process", {})
        
        # Prepare nodes
        nodes = []
        for node_data in process_data.get("nodes", []):
            nodes.append(ProcessNode(
                id=node_data["id"],
                name=node_data["name"],
                role=node_data["role"],
                description=node_data["description"],
                assigned_to=node_data.get("assigned_to")
            ))
            
        # Prepare transitions
        transitions = []
        for transition_data in process_data.get("transitions", []):
            transitions.append(ProcessTransition(
                from_node=transition_data["from"],
                to_node=transition_data["to"]
            ))
            
        # Prepare roles
        roles = []
        for role_data in process_data.get("roles", []):
            roles.append(Role(
                id=role_data["id"],
                name=role_data["name"],
                description=role_data["description"]
            ))
            
        return cls(
            name=process_data.get("name", "Unnamed Process"),
            description=process_data.get("description"),
            learner=process_data.get("learner", {}),
            nodes=nodes,
            transitions=transitions,
            roles=roles,
            evolution=process_data.get("evolution", {})
        ) 