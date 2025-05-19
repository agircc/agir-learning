"""
User profile frame for displaying user information
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from agir_db.models.user import User

class UserProfileFrame(ttk.Frame):
    """Frame for displaying user profile information"""
    
    def __init__(self, parent, db, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.db = db
        
        # Create profile display
        self.profile_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.profile_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.profile_text.config(state=tk.DISABLED)
    
    def load_profile(self, user_id):
        """Load and display the user profile"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return
                
            self.profile_text.config(state=tk.NORMAL)
            self.profile_text.delete(1.0, tk.END)
            
            self.profile_text.insert(tk.END, f"Username: {user.username}\n\n")
            self.profile_text.insert(tk.END, f"Name: {user.first_name} {user.last_name}\n\n")
            
            if user.description:
                self.profile_text.insert(tk.END, f"Description:\n{user.description}\n\n")
                
            self.profile_text.insert(tk.END, f"LLM Model: {user.llm_model or 'Not set'}\n\n")
            
            # Add any other relevant user information here
            
            self.profile_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Profile Error", f"Failed to load profile: {str(e)}") 