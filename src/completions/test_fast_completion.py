#!/usr/bin/env python
"""
Test script for fast completion functionality
"""

import os
import sys
import time
import logging
from typing import Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.completions.fast_completion import create_fast_completion
from src.completions.fast_memory_retriever import get_fast_memory_retriever

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fast_completion(user_id: str = "00000000-0000-0000-0000-000000000000"):
    """Test the fast completion functionality"""
    
    try:
        print(f"Testing fast completion for user: {user_id}")
        
        # Test memory retriever
        print("\n1. Testing memory retriever...")
        start_time = time.time()
        retriever = get_fast_memory_retriever(user_id)
        retriever_time = time.time() - start_time
        
        memory_count = retriever.get_memory_count()
        print(f"   Loaded {memory_count} memories in {retriever_time:.3f}s")
        
        # Test memory search
        print("\n2. Testing memory search...")
        start_time = time.time()
        memories = retriever.search_memories("learning machine", k=3)
        search_time = time.time() - start_time
        
        print(f"   Found {len(memories)} relevant memories in {search_time:.3f}s")
        for i, memory in enumerate(memories):
            print(f"   Memory {i+1}: {memory['content'][:100]}...")
        
        # Test fast completion
        print("\n3. Testing fast completion...")
        start_time = time.time()
        completion = create_fast_completion(user_id, temperature=0.7, max_tokens=100)
        if not completion:
            print("   Failed to create fast completion")
            return
        
        completion_init_time = time.time() - start_time
        print(f"   Initialized completion in {completion_init_time:.3f}s")
        
        # Test actual completion
        print("\n4. Testing completion generation...")
        test_prompt = "Tell me about machine learning"
        
        start_time = time.time()
        response = completion.complete(test_prompt)
        completion_time = time.time() - start_time
        
        print(f"   Generated completion in {completion_time:.3f}s")
        print(f"   Prompt: {test_prompt}")
        print(f"   Response: {response[:200]}...")
        
        # Show stats
        print("\n5. Completion stats:")
        stats = completion.get_memory_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
            
        # Total time
        total_time = retriever_time + search_time + completion_init_time + completion_time
        print(f"\nTotal execution time: {total_time:.3f}s")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test fast completion")
    parser.add_argument("--user-id", default="00000000-0000-0000-0000-000000000000", 
                       help="User ID to test")
    
    args = parser.parse_args()
    test_fast_completion(args.user_id) 