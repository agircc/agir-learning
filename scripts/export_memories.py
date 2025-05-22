#!/usr/bin/env python3
"""
Export memories for a specific learner to a JSON file.
"""
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from agir_db.db.session import get_db
from agir_db.models.memory import Memory
from agir_db.models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Export memories for a learner')
    
    parser.add_argument(
        'learner_id',
        help='ID of the learner whose memories to export',
    )
    
    parser.add_argument(
        '--output',
        help='Output file path (default: learner_<id>_memories_<date>.json)',
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print the JSON output',
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )
    
    return parser.parse_args()

def export_memories(learner_id: str, output_path: Optional[str] = None, pretty: bool = False) -> bool:
    """
    Export memories for a specific learner to a JSON file.
    
    Args:
        learner_id: ID of the learner
        output_path: Path to output file (optional)
        pretty: Whether to pretty-print the JSON
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = next(get_db())
        
        # Verify the learner exists
        user = db.query(User).filter(User.id == learner_id).first()
        if not user:
            logger.error(f"Learner with ID {learner_id} not found")
            return False
        
        logger.info(f"Exporting memories for learner: {user.username} (ID: {learner_id})")
        
        # Get all memories for the learner
        memories = db.query(Memory).filter(Memory.user_id == learner_id).all()
        
        if not memories:
            logger.warning(f"No memories found for learner {user.username}")
            return False
        
        logger.info(f"Found {len(memories)} memories")
        
        # Convert to JSON format
        memory_data = [
            {
                "id": str(memory.id),
                "content": memory.content,
                "created_at": memory.created_at.isoformat() if memory.created_at else None,
                "episode_id": str(memory.episode_id) if memory.episode_id else None,
                "type": memory.type if hasattr(memory, 'type') else "default"
            } 
            for memory in memories
        ]
        
        # Determine output file path
        if not output_path:
            output_path = f"learner_{learner_id}_memories_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Write to file
        with open(output_path, "w") as f:
            if pretty:
                json.dump(memory_data, f, indent=2)
            else:
                json.dump(memory_data, f)
        
        logger.info(f"Memories exported to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export memories: {str(e)}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    success = export_memories(
        learner_id=args.learner_id,
        output_path=args.output,
        pretty=args.pretty
    )
    
    if success:
        logger.info("Memory export completed successfully")
        return 0
    else:
        logger.error("Memory export failed")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 