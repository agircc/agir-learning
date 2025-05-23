#!/usr/bin/env python3
"""
Direct test for the enhanced thinking chain functionality
Tests memory-aware knowledge analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.completions.fast_completion import create_fast_completion
import time

def test_thinking_chain():
    """Test the enhanced thinking chain process"""
    
    print("🧠 Testing Enhanced Thinking Chain Process")
    print("=" * 50)
    
    # Use a real user ID from the database
    user_id = "e030d930-913d-4525-8478-1cf77b698364"  # emotion_master user
    
    # Test prompt
    test_prompt = "How can I optimize database performance for large datasets?"
    
    print(f"📝 Test Prompt: {test_prompt}")
    print(f"👤 User ID: {user_id}")
    
    try:
        # Create fast completion instance
        start_time = time.time()
        completion = create_fast_completion(user_id=user_id, temperature=0.7, max_tokens=200)
        init_time = time.time() - start_time
        
        if not completion:
            print("❌ Failed to create completion instance")
            return
        
        print(f"✅ Completion instance created in {init_time:.2f}s")
        
        # Get memory stats
        stats = completion.get_memory_stats()
        print(f"📊 Memory Stats: {stats['memory_count']} memories for user {stats['username']}")
        
        # Test the complete method (which now uses enhanced thinking chain)
        print("\n🔄 Running Enhanced Thinking Chain...")
        completion_start = time.time()
        
        response = completion.complete(test_prompt)
        
        completion_time = time.time() - completion_start
        total_time = time.time() - start_time
        
        print(f"⏱️  Completion Time: {completion_time:.2f}s")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        
        print("\n📋 Generated Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # Analyze response quality
        response_length = len(response.split())
        print(f"\n📊 Response Analysis:")
        print(f"   Length: {response_length} words")
        print(f"   Contains 'database': {'Yes' if 'database' in response.lower() else 'No'}")
        print(f"   Contains 'performance': {'Yes' if 'performance' in response.lower() else 'No'}")
        print(f"   Contains technical terms: {'Yes' if any(term in response.lower() for term in ['index', 'query', 'optimization', 'cache']) else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_thinking_chain()
    if success:
        print("\n✅ Enhanced thinking chain test completed successfully!")
    else:
        print("\n❌ Enhanced thinking chain test failed!")
        sys.exit(1) 