"""
User chat frame for interacting with simulated users
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from src.chat.chat_with_learner import LearnerChatSession
from .chat_display_frame import ChatDisplayFrame

class UserChatFrame(ttk.Frame):
    """Frame for chatting with a simulated user"""
    
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        
        # Chat history display
        self.chat_display = ChatDisplayFrame(self)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Input area at the bottom
        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Text entry
        self.input_text = scrolledtext.ScrolledText(self.input_frame, height=3, wrap=tk.WORD)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Send button
        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind Enter key to send message
        self.input_text.bind("<Return>", self.on_enter)
        
        # Chat session
        self.chat_session = None
        self.chat_history = []
    
    def on_enter(self, event):
        """Handle Enter key press"""
        if not (event.state & 0x1):  # Check if Shift key is not pressed
            self.send_message()
            return "break"  # Prevent default Enter behavior
        
    def set_chat_session(self, user_id):
        """Set the user to chat with"""
        try:
            self.chat_session = LearnerChatSession(user_id=user_id)
            self.chat_history = []
            self.chat_display.display_messages([])
            self.input_text.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Chat Error", f"Failed to start chat session: {str(e)}")
            self.chat_session = None
            self.input_text.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)
    
    def close_chat_session(self):
        """Close the current chat session"""
        if self.chat_session:
            try:
                self.chat_session.close()
            except:
                pass
            self.chat_session = None
            self.input_text.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)
    
    def send_message(self):
        """Send the current message to the user"""
        if not self.chat_session:
            messagebox.showinfo("Chat", "Please select a user to chat with first.")
            return
            
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
            
        # Clear input
        self.input_text.delete("1.0", tk.END)
        
        # Add user message to chat history
        self.chat_history.append({
            "sender_name": "You",
            "sender_id": "you",
            "timestamp": "now",
            "content": message
        })
        
        # Get response from user
        try:
            response = self.chat_session.chat(message)
            
            # Add response to chat history
            self.chat_history.append({
                "sender_name": self.chat_session.user.username,
                "sender_id": str(self.chat_session.user.id),
                "timestamp": "now",
                "content": response
            })
        except Exception as e:
            messagebox.showerror("Chat Error", f"Failed to get response: {str(e)}")
            return
            
        # Update chat display
        self.chat_display.display_messages(self.chat_history) 