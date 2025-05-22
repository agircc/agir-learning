#!/usr/bin/env python
"""
Command-line interface for chatting with a learner.
Usage: python chat_learner_cli.py <username>
"""

import sys
import os
import logging
import argparse
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from src.chat.chat_with_learner import create_chat_session, LearnerChatSession

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Chat with a learner.')
    parser.add_argument('username', help='Username of the learner to chat with')
    parser.add_argument('--add-memory', action='store_true', help='Enable memory addition mode')
    return parser.parse_args()

def run_chat_session(username: str, add_memory_mode: bool = False):
    """
    Run an interactive chat session with a learner.
    
    Args:
        username: Username of the learner to chat with
        add_memory_mode: Whether to enable memory addition mode
    """
    try:
        print(f"Starting chat session with learner: {username}")
        session = create_chat_session(username=username)
        
        if not session:
            print(f"Failed to create chat session with learner: {username}")
            return
        
        print(f"Chat session started with {session.user.first_name} {session.user.last_name} ({session.user.username})")
        print(f"Using LLM model: {session.model_name}")
        print("-" * 50)
        
        if add_memory_mode:
            print("MEMORY ADDITION MODE ENABLED")
            print("Enter memories to add, or 'exit' to quit.")
            
            while True:
                memory = input("\nEnter memory to add (or 'exit'): ")
                if memory.lower() == 'exit':
                    break
                    
                importance = input("Enter importance (0.0-2.0, default 1.0): ") or "1.0"
                try:
                    importance = float(importance)
                except ValueError:
                    print("Invalid importance value, using default 1.0")
                    importance = 1.0
                    
                memory_id = session.add_memory(memory, importance=importance)
                if memory_id:
                    print(f"Memory added successfully! ID: {memory_id}")
                else:
                    print("Failed to add memory.")
        else:
            print("Chat mode: Type your messages and press Enter to chat.")
            print("Type 'exit' to end the conversation.")
            print("-" * 50)
            
            while True:
                try:
                    message = input("\nYou: ")
                    
                    if message.lower() == 'exit':
                        break
                        
                    response = session.chat(message)
                    print(f"\n{session.user.username}: {response}")
                    
                except KeyboardInterrupt:
                    print("\nChat session interrupted.")
                    break
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    logger.error(f"Error during chat: {str(e)}")
        
        # Close the session
        session.close()
        print("\nChat session ended.")
        
    except Exception as e:
        logger.error(f"Error in chat session: {str(e)}")
        print(f"Error: {str(e)}")

def main():
    """Main entry point."""
    args = parse_args()
    run_chat_session(args.username, args.add_memory)

if __name__ == "__main__":
    main() 