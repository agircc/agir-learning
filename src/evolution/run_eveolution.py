   
    def run_evolution(self, process: Process) -> bool:
        """
        Run the evolution process.
        
        Args:
            process: Process instance
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If process fails for any reason
        """
        logger.info(f"Starting evolution process: {process.name}")
        
        # Create database session
        with SessionLocal() as db:
            # Get or create target user first
            learnername = process.learner.get("username")
            if not learnername:
                raise ValueError("Target user username not specified in process")
            
            learner, created = get_or_create_user(db, learnername, process.learner)
            if created:
                logger.info(f"Created new target user: {learnername}")
            else:
                logger.info(f"Using existing target user: {learnername}")
            
            # 保存process实例到数据库，使用learner.id作为created_by
            db_process = create_process_record(db, {
                "name": process.name,
                "description": process.description,
                "created_by": str(learner.id)  # Use learner.id as the creator
            })
            logger.info(f"Created process record in database with ID: {db_process.id}")
            
            # 保存配置作为自定义字段到数据库
            # 将配置保存到process_instance表
            from agir_db.models.process_instance import ProcessInstance, ProcessInstanceStatus
            
            # Now create the process instance with learner.id
            process_instance = ProcessInstance(
                process_id=db_process.id,
                initiator_id=learner.id,  # Now we have learner.id
                status=ProcessInstanceStatus.RUNNING,
                config=json.dumps(process.to_dict())
            )
            db.add(process_instance)
            db.commit()
            logger.info(f"Saved process instance to database")
            process_instance_id = process_instance.id
            
            # Create ProcessNode records in the database for each node in the process
            from agir_db.models.process import ProcessNode as DBProcessNode, ProcessRole
            
            # Dictionary to store mapping from YAML node IDs to database node IDs
            node_id_mapping = {}
            
            # First, create role records
            role_id_mapping = {}
            for role in process.roles:
                db_role = ProcessRole(
                    process_id=db_process.id,
                    name=role.name,
                    description=role.description,
                    model=role.model
                )
                db.add(db_role)
                db.flush()  # Get the ID without committing
                role_id_mapping[role.id] = db_role.id
            
            # Now create node records
            for node in process.nodes:
                # Get the role ID from the mapping
                role_id = role_id_mapping.get(node.role)
                
                db_node = DBProcessNode(
                    process_id=db_process.id,
                    name=node.name,
                    description=node.description,
                    role_id=role_id
                )
                db.add(db_node)
                db.flush()  # Get the ID without committing
                node_id_mapping[node.id] = db_node.id
            
            db.commit()
            logger.info(f"Created {len(node_id_mapping)} process node records in database")
            
            # Store the mapping in the process instance for later use
            config = json.loads(process_instance.config) if process_instance.config else {}
            config["node_id_mapping"] = {k: str(v) for k, v in node_id_mapping.items()}
            process_instance.config = json.dumps(config)
            db.commit()
            
            # Process each node in the process
            current_node = process.nodes[0]  # Start with the first node
            history = []  # Conversation history
            
            while current_node:
                result = self._process_node(db, process, current_node, learner, history, db_process.id)
                
                processed_node, response, next_node = result
                
                # Add to conversation history
                history.append({
                    "node": processed_node.id,
                    "role": processed_node.role,
                    "content": response
                })
                
                # Update current node
                current_node = next_node
                
                if not current_node:
                    logger.info("Reached end of process or no valid next node")
                    break
            
            # 更新process实例状态为已完成
            if process_instance_id:
                process_instance = db.query(ProcessInstance).filter(ProcessInstance.id == process_instance_id).first()
                if process_instance:
                    process_instance.status = ProcessInstanceStatus.COMPLETED
                    db.commit()
                    logger.info(f"Updated process instance status to completed")
            
            # Process evolution
            self._process_evolution(db, process, learner, history, db_process.id)
            
            logger.info(f"Evolution process completed successfully: {process.name}")
            return True