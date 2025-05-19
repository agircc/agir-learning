"""
Users tab for visualization of users, their memories, and chat functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import uuid

from agir_db.models.user import User

from .user_profile_frame import UserProfileFrame
from .memory_pagination_frame import MemoryPaginationFrame
from .user_chat_frame import UserChatFrame

class UsersTab(ttk.Frame):
    """Class for managing the Users tab content"""
    
    def __init__(self, parent, db, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.db = db
        
        # Create main paned window for two-column layout
        self.users_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.users_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left column (user list and profile)
        self.left_column = ttk.Frame(self.users_paned)
        self.users_paned.add(self.left_column, weight=1)
        
        # Create right column (memories and chat)
        self.right_column = ttk.Frame(self.users_paned)
        self.users_paned.add(self.right_column, weight=1)
        
        # Setup left column
        self.setup_left_column()
        
        # Setup right column
        self.setup_right_column()
        
    def setup_left_column(self):
        """Setup the left column of the Users tab"""
        # Create vertical paned window for user list and profile
        self.left_paned = ttk.PanedWindow(self.left_column, orient=tk.VERTICAL)
        self.left_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create user list frame
        self.user_list_frame = ttk.LabelFrame(self.left_paned, text="User List")
        self.left_paned.add(self.user_list_frame, weight=1)
        
        # Create user list treeview
        self.users_tree = ttk.Treeview(self.user_list_frame, columns=("id", "username", "name"))
        self.users_tree.heading("#0", text="")
        self.users_tree.heading("id", text="ID")
        self.users_tree.heading("username", text="Username")
        self.users_tree.heading("name", text="Name")
        self.users_tree.column("#0", width=0, stretch=tk.NO)
        self.users_tree.column("id", width=80, stretch=tk.NO)
        self.users_tree.column("username", width=150)
        self.users_tree.column("name", width=150)
        
        # Add scrollbar to user list treeview
        users_scrollbar = ttk.Scrollbar(self.user_list_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=users_scrollbar.set)
        
        # Pack user list treeview and scrollbar
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        users_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create user profile frame
        self.user_profile_frame = ttk.LabelFrame(self.left_paned, text="User Profile")
        self.left_paned.add(self.user_profile_frame, weight=1)
        
        # Create user profile display
        self.user_profile = UserProfileFrame(self.user_profile_frame, self.db)
        self.user_profile.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection events
        self.users_tree.bind("<<TreeviewSelect>>", self.on_user_selected)
    
    def setup_right_column(self):
        """Setup the right column of the Users tab"""
        # Create vertical paned window for memories and chat
        self.right_paned = ttk.PanedWindow(self.right_column, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create memories frame
        self.memories_frame = ttk.LabelFrame(self.right_paned, text="User Memories")
        self.right_paned.add(self.memories_frame, weight=1)
        
        # Create memories display with pagination
        self.memories_display = MemoryPaginationFrame(self.memories_frame, self.db)
        self.memories_display.pack(fill=tk.BOTH, expand=True)
        
        # Create chat frame
        self.chat_frame = ttk.LabelFrame(self.right_paned, text="Chat with User")
        self.right_paned.add(self.chat_frame, weight=1)
        
        # Create chat interface
        self.user_chat_frame = UserChatFrame(self.chat_frame)
        self.user_chat_frame.pack(fill=tk.BOTH, expand=True)
        
    def load_users(self):
        """Load users from the database."""
        if self.db is None:
            messagebox.showerror("Database Error", "No database connection available.")
            return
            
        try:
            # Clear existing items
            for item in self.users_tree.get_children():
                self.users_tree.delete(item)
                
            # Get all users
            users = self.db.query(User).all()
            
            # Add to treeview
            for user in users:
                full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else ""
                self.users_tree.insert("", "end", str(user.id), 
                                      values=(user.id, user.username, full_name))
                
            print(f"Loaded {len(users)} users")
            
        except Exception as e:
            print(f"Exception in load_users: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Database Error", f"Failed to load users: {str(e)}")
    
    def on_user_selected(self, event):
        """Handle user selection."""
        item_id = self.users_tree.focus()
        if not item_id or self.db is None:
            return
            
        try:
            user_id = uuid.UUID(item_id)
            
            # Load user profile
            self.user_profile.load_profile(user_id)
            
            # Load user memories
            self.memories_display.load_memories(user_id)
            
            # Set chat session
            self.user_chat_frame.set_chat_session(user_id)
            
        except Exception as e:
            print(f"Exception in on_user_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load user details: {str(e)}")
            
    def close_chat_session(self):
        """Close the current chat session"""
        if hasattr(self, 'user_chat_frame'):
            self.user_chat_frame.close_chat_session() 