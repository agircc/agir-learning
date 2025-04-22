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
    Represents a learning process with nodes, transitions, and roles.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    target_user: Dict[str, Any] = Field(default_factory=dict)
    nodes: List[ProcessNode] = Field(default_factory=list)
    transitions: List[ProcessTransition] = Field(default_factory=list)
    roles: List[Role] = Field(default_factory=list)
    evolution: Dict[str, Any] = Field(default_factory=dict)

    # Node lookup cache
    _node_map: Dict[str, ProcessNode] = {}
    
    def node_by_id(self, node_id: str) -> Optional[ProcessNode]:
        """
        Get a node by its ID.
        
        Args:
            node_id: The node ID
            
        Returns:
            The node or None if not found
        """
        # Populate cache if empty
        if not self._node_map:
            self._node_map = {node.id: node for node in self.nodes}
            
        return self._node_map.get(node_id)
    
    def next_nodes(self, node_id: str) -> List[ProcessNode]:
        """
        Get the next nodes after the given node.
        
        Args:
            node_id: The current node ID
            
        Returns:
            List of next possible nodes
        """
        next_node_ids = [
            t.to_node for t in self.transitions 
            if t.from_node == node_id
        ]
        
        return [
            self.node_by_id(node_id) 
            for node_id in next_node_ids 
            if self.node_by_id(node_id) is not None
        ]
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """
        Get a role by its ID.
        
        Args:
            role_id: The role ID
            
        Returns:
            The role or None if not found
        """
        for role in self.roles:
            if role.id == role_id:
                return role
        return None
    
    def validate_graph(self) -> Tuple[bool, List[str]]:
        """
        Validate the process graph for correctness.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for nodes referenced in transitions that don't exist
        node_ids = {node.id for node in self.nodes}
        
        for transition in self.transitions:
            if transition.from_node not in node_ids:
                errors.append(f"Transition references non-existent 'from' node: {transition.from_node}")
            if transition.to_node not in node_ids:
                errors.append(f"Transition references non-existent 'to' node: {transition.to_node}")
        
        # Check for nodes with no incoming or outgoing transitions
        nodes_with_incoming = {t.to_node for t in self.transitions}
        nodes_with_outgoing = {t.from_node for t in self.transitions}
        
        nodes_with_no_incoming = node_ids - nodes_with_incoming
        if nodes_with_no_incoming and not nodes_with_no_incoming.issubset({self.nodes[0].id}):
            # It's okay for the first node to have no incoming transitions
            no_incoming_except_first = nodes_with_no_incoming - {self.nodes[0].id}
            if no_incoming_except_first:
                errors.append(f"Nodes with no incoming transitions: {no_incoming_except_first}")
        
        nodes_with_no_outgoing = node_ids - nodes_with_outgoing
        if nodes_with_no_outgoing:
            # It might be okay to have leaf nodes with no outgoing transitions
            errors.append(f"Possible leaf nodes with no outgoing transitions: {nodes_with_no_outgoing}")
        
        # Check for roles referenced in nodes that don't exist
        role_ids = {role.id for role in self.roles}
        for node in self.nodes:
            if node.role not in role_ids:
                errors.append(f"Node '{node.id}' references non-existent role: {node.role}")
        
        return len(errors) == 0, errors
    
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
            target_user=process_data.get("target_user", {}),
            nodes=nodes,
            transitions=transitions,
            roles=roles,
            evolution=process_data.get("evolution", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将Process对象转换为字典，用于序列化到数据库
        
        Returns:
            字典表示
        """
        # 转换nodes
        nodes_list = []
        for node in self.nodes:
            node_dict = {
                "id": node.id,
                "name": node.name,
                "role": node.role,
                "description": node.description
            }
            if node.assigned_to:
                node_dict["assigned_to"] = node.assigned_to
            nodes_list.append(node_dict)
            
        # 转换transitions
        transitions_list = []
        for transition in self.transitions:
            transitions_list.append({
                "from": transition.from_node,
                "to": transition.to_node
            })
            
        # 转换roles
        roles_list = []
        for role in self.roles:
            roles_list.append({
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "system_prompt_template": role.system_prompt_template
            })
            
        # 构建完整字典
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_user": self.target_user,
            "nodes": nodes_list,
            "transitions": transitions_list,
            "roles": roles_list,
            "evolution": self.evolution
        } 