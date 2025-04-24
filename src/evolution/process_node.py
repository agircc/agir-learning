def process_node(
    self, 
    db: Session, 
    process: Process, 
    node: ProcessNode, 
    target_user: Any,
    history: List[Dict[str, Any]],
    process_id: Any = None
) -> Optional[Tuple[ProcessNode, str, Optional[ProcessNode]]]:
    """
    Process a node in the evolution process.
    
    Args:
        db: Database session
        process: Process instance
        node: Current node to process
        target_user: Target user for the process
        history: Conversation history
        process_id: ID of the process in the database
        
    Returns:
        Tuple of (node, response, next_node)
        
    Raises:
        ValueError: If there is an error processing the node
    """
    logger.info(f"Processing node: {node.name}")
    
    # Get the appropriate LLM provider for this node
    llm_provider = self._get_provider_for_node(db, node, self.llm_provider)
    
    # Get the role for this node
    role_id = node.role
    
    # Check if node is assigned to a specific user or if it's a learner node
    is_learner_node = False
    if role_id == "learner":
        is_learner_node = True
        logger.info(f"Node {node.name} is a learner node, will use learner's model")
    elif hasattr(node, 'assigned_to') and node.assigned_to and node.assigned_to == target_user.username:
        is_learner_node = True
        logger.info(f"Node {node.name} is assigned to target user {target_user.username}")
        
    # Generate context for the node
    context = self._generate_node_context(process, node, history, target_user)
    
    # If node is for the learner, handle differently
    response = ""
    try:
        if is_learner_node:
            response = learner_generate_response(node, context)
        else:
            # Generate agent prompt
            prompt = self._generate_agent_prompt(node, context, history)
            
            # Get response from LLM
            response = llm_provider.generate(
                prompt=prompt,
                system_prompt=f"You are simulating a {node.role} in a process called {process.name}. {node.description}",
                temperature=0.7,
                max_tokens=1000
            )
            
        # Add to history
        history.append({
            "node": node.name,
            "role": role_id,
            "response": response
        })
        
        # Find next node if available
        next_node = self._find_next_node(process, node)
        
        return (node, response, next_node)
        
    except Exception as e:
        error_msg = f"Error processing node {node.name}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)