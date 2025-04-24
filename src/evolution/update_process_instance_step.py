def update_process_instance_step(self, db: Session, node_record_id: Any, status: str, response: str = None, error: str = None):
  """更新节点执行记录状态"""
  if not node_record_id:
      return
      
  try:
      # 使用process_instance_step表更新状态
      from agir_db.models.process_instance_step import ProcessInstanceStep
      node_record = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == node_record_id).first()
      if node_record:
          # Check if the model has a status field before trying to update it
          if hasattr(node_record, 'status'):
              node_record.status = status
          else:
              # If status field doesn't exist, log a warning
              logger.warning(f"ProcessInstanceStep model doesn't have a status field, skipping status update")
          
          # Update response if the field exists and a value is provided
          if response and hasattr(node_record, 'response'):
              node_record.response = response
          
          # Update error if the field exists and a value is provided
          if error and hasattr(node_record, 'error'):
              node_record.error = error
          
          db.commit()
          logger.info(f"Updated node record {node_record_id}")
  except Exception as e:
      logger.error(f"Failed to update node record status: {str(e)}")