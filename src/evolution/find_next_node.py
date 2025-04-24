def find_next_node(self, process: Process, current_node: ProcessNode) -> Optional[ProcessNode]:
  """
  Find the next node in the process based on the current node.
  
  Args:
      process: Process instance
      current_node: Current node
      
  Returns:
      Optional[ProcessNode]: Next node if available, None otherwise
  """
  # Check if process is a dictionary (from get_process) or a Process object
  is_dict = isinstance(process, dict)
  
  # Access transitions based on the object type
  if is_dict:
      transitions = process.get("transitions", [])
      if not transitions:
          return None
  else:
      if not hasattr(process, 'transitions') or not process.transitions:
          return None
      transitions = process.transitions
      
  # Find transitions where current node is the 'from' node
  next_node_names = []
  for transition in transitions:
      # Handle both dictionary and object cases
      if is_dict:
          from_node = transition.get('from') 
          to_node = transition.get('to')
      else:
          from_node = transition.get('from') if isinstance(transition, dict) else getattr(transition, 'from_node', None)
          to_node = transition.get('to') if isinstance(transition, dict) else getattr(transition, 'to_node', None)
          
      # Get current node name, accounting for both dict and object
      current_node_name = current_node.name if hasattr(current_node, 'name') else current_node.get('name')
      
      if from_node == current_node_name:
          next_node_names.append(to_node)
          
  if not next_node_names:
      return None
      
  # Get the first next node (could be extended with branching logic)
  next_node_name = next_node_names[0]
  
  # Access nodes based on the object type
  if is_dict:
      nodes = process.get("nodes", [])
  else:
      nodes = process.nodes
      
  # Find the node in the process nodes
  for node in nodes:
      # Handle both dictionary and object cases
      node_name = node.name if hasattr(node, 'name') else node.get('name')
      if node_name == next_node_name:
          return node
          
  return None 