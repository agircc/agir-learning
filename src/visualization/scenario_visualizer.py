"""
Scenario Visualizer using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font
from typing import List, Dict, Any, Optional, Tuple, Set
import uuid
from sqlalchemy.orm import Session
import os
import random
import colorsys
import atexit

from agir_db.db.session import get_db
# Debug print to see database configuration
try:
    from agir_db.db.session import SQLALCHEMY_DATABASE_URI
    print(f"Visualization is using database URI: {SQLALCHEMY_DATABASE_URI}")
except Exception as e:
    print(f"Could not import database URI: {e}")
    
# Print environment variable directly for comparison
print(f"Environment DATABASE_URI: {os.environ.get('SQLALCHEMY_DATABASE_URI')}")

from agir_db.models.scenario import Scenario
from agir_db.models.state import State
from agir_db.models.episode import Episode
from agir_db.models.step import Step
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.state_role import StateRole
from agir_db.models.user import User
from agir_db.models.memory import UserMemory

from .chat_utils import get_conversations_for_step, get_messages_for_conversation, format_messages
from src.chat.chat_with_learner import LearnerChatSession


class ChatDisplayFrame(ttk.Frame):
    """Custom frame for displaying chat messages with better styling."""
    
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        
        # Chat display colors
        self.colors = {}
        self.default_colors = ["#4285F4", "#EA4335", "#FBBC05", "#34A853", "#8A2BE2", "#FF6347", "#20B2AA", "#FF8C00"]
        
        # Create scrollable text widget with custom styling
        self.text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for styling
        self.text.tag_configure("timestamp", foreground="#666666", font=("Helvetica", 9, "italic"))
        self.text.tag_configure("header", font=("Helvetica", 10, "bold"))
        self.text.tag_configure("message", font=("Helvetica", 11), lmargin1=20, lmargin2=20)
        self.text.tag_configure("system", foreground="#999999", font=("Helvetica", 10, "italic"))
        
        # Make the text widget read-only
        self.text.config(state=tk.DISABLED)
        
    def get_agent_color(self, agent_id, agent_role=None):
        """Get a consistent color for an agent based on their ID."""
        if agent_id in self.colors:
            return self.colors[agent_id]
        
        # Generate a new color
        if len(self.default_colors) > 0:
            color = self.default_colors.pop(0)
        else:
            # Generate a random visually distinct color if we've used all defaults
            h = random.random()
            s = random.uniform(0.5, 0.9)
            l = random.uniform(0.4, 0.6)
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
        self.colors[agent_id] = color
        return color
        
    def display_messages(self, messages):
        """Display messages in the chat widget with styling."""
        # Clear current content
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        
        # Reset colors
        self.colors = {}
        
        if not messages:
            self.text.insert(tk.END, "No messages to display.", "system")
            self.text.config(state=tk.DISABLED)
            return
            
        for msg in messages:
            # Format and insert message with styling
            sender_name = msg["sender_name"]
            sender_id = msg["sender_id"]
            timestamp = msg["timestamp"]
            content = msg["content"]
            
            # Create a tag for this sender if it doesn't exist
            sender_tag = f"sender_{sender_id}"
            if not sender_tag in self.text.tag_names():
                color = self.get_agent_color(sender_id)
                self.text.tag_configure(sender_tag, foreground=color, font=("Helvetica", 10, "bold"))
            
            # Insert timestamp
            self.text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            
            # Insert sender name with color
            self.text.insert(tk.END, f"{sender_name}: ", sender_tag)
            
            # Insert message content
            self.text.insert(tk.END, f"\n{content}\n\n", "message")
        
        # Make read-only again
        self.text.config(state=tk.DISABLED)
        
        # Scroll to the end
        self.text.see(tk.END)


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


class MemoryPaginationFrame(ttk.Frame):
    """Frame for displaying user memories with pagination"""
    
    def __init__(self, parent, db, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.db = db
        self.current_user_id = None
        self.page = 1
        self.page_size = 10
        self.total_pages = 1
        
        # Create memory display
        self.memory_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15)
        self.memory_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.memory_text.config(state=tk.DISABLED)
        
        # Pagination controls
        self.pagination_frame = ttk.Frame(self)
        self.pagination_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.prev_button = ttk.Button(self.pagination_frame, text="Previous", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT)
        
        self.page_label = ttk.Label(self.pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.next_button = ttk.Button(self.pagination_frame, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.LEFT)
        
        # Disable buttons initially
        self.prev_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)
    
    def load_memories(self, user_id):
        """Load memories for the specified user"""
        self.current_user_id = user_id
        self.page = 1
        self.load_current_page()
    
    def load_current_page(self):
        """Load the current page of memories"""
        if not self.current_user_id:
            return
            
        try:
            # Calculate offset
            offset = (self.page - 1) * self.page_size
            
            # Get total count
            total_count = self.db.query(UserMemory).filter(
                UserMemory.user_id == self.current_user_id
            ).count()
            
            # Get memories for current page
            memories = self.db.query(UserMemory).filter(
                UserMemory.user_id == self.current_user_id
            ).order_by(
                UserMemory.created_at.desc()
            ).offset(offset).limit(self.page_size).all()
            
            # Update total pages
            self.total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
            
            # Update page label
            self.page_label.config(text=f"Page {self.page} of {self.total_pages}")
            
            # Enable/disable pagination buttons
            self.prev_button.config(state=tk.NORMAL if self.page > 1 else tk.DISABLED)
            self.next_button.config(state=tk.NORMAL if self.page < self.total_pages else tk.DISABLED)
            
            # Display memories
            self.memory_text.config(state=tk.NORMAL)
            self.memory_text.delete(1.0, tk.END)
            
            if not memories:
                self.memory_text.insert(tk.END, "No memories found.")
            else:
                for memory in memories:
                    self.memory_text.insert(tk.END, f"[{memory.created_at}]\n", "timestamp")
                    self.memory_text.insert(tk.END, f"{memory.content}\n\n", "")
            
            self.memory_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Memory Error", f"Failed to load memories: {str(e)}")
    
    def next_page(self):
        """Go to the next page"""
        if self.page < self.total_pages:
            self.page += 1
            self.load_current_page()
    
    def prev_page(self):
        """Go to the previous page"""
        if self.page > 1:
            self.page -= 1
            self.load_current_page()


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


class ScenarioVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("AGIR Scenario Visualizer")
        
        # Set window size to screen size with margin
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = screen_width - 100
        window_height = screen_height - 100
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create a persistent database session
        try:
            self.db = next(get_db())
            print("Opened persistent database session")
            
            # Register a callback to close the session when the application exits
            atexit.register(self.close_db)
            # Also bind to window close event
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception as e:
            print(f"Failed to create persistent database connection: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Database Error", f"Failed to connect to database: {str(e)}")
            self.db = None
        
        # Try to maximize window in a cross-platform way
        try:
            # Windows
            self.root.state('zoomed')
        except:
            try:
                # macOS and Linux 
                import platform
                if platform.system() == 'Darwin':  # macOS
                    # On macOS, just set window size close to screen size
                    pass
                else:  # Linux
                    self.root.attributes('-zoomed', True)
            except:
                # If above methods fail, use normal fullscreen
                self.root.attributes('-fullscreen', True)
                # Add Escape key to exit fullscreen
                self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=25)
        self.style.configure("TNotebook.Tab", padding=[10, 5])
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create Scenarios tab
        self.scenarios_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scenarios_tab, text="Scenarios")
        
        # Create Users tab
        self.users_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.users_tab, text="Users")
        
        # Setup Scenarios tab
        self.setup_scenarios_tab()
        
        # Setup Users tab
        self.setup_users_tab()
        
        # Load initial data
        self.load_scenarios()
        self.load_users()
        
        # Add tab change handler
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Current chat session
        self.current_chat_session = None
    
    def close_db(self):
        """Close the database session."""
        if self.db:
            self.db.close()
            print("Closed database session")
    
    def on_close(self):
        """Handle window close event."""
        self.close_db()
        self.root.destroy()
    
    def on_tab_changed(self, event):
        """Handle tab change event"""
        if self.user_chat_frame and hasattr(self, 'user_chat_frame'):
            self.user_chat_frame.close_chat_session()
    
    def setup_scenarios_tab(self):
        """Setup the Scenarios tab content"""
        # Create main paned window for two-column layout
        self.scenarios_paned = ttk.PanedWindow(self.scenarios_tab, orient=tk.HORIZONTAL)
        self.scenarios_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left column (scenarios and episodes)
        self.scenarios_left_column = ttk.Frame(self.scenarios_paned)
        self.scenarios_paned.add(self.scenarios_left_column, weight=1)
        
        # Create right column (steps and step details/conversations)
        self.scenarios_right_column = ttk.Frame(self.scenarios_paned)
        self.scenarios_paned.add(self.scenarios_right_column, weight=1)
        
        # Setup left column
        self.setup_scenarios_left_column()
        
        # Setup right column
        self.setup_scenarios_right_column()
    
    def setup_scenarios_left_column(self):
        """Setup the left column of the Scenarios tab"""
        # Create vertical paned window for scenarios and episodes
        self.scenarios_left_paned = ttk.PanedWindow(self.scenarios_left_column, orient=tk.VERTICAL)
        self.scenarios_left_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create scenarios frame
        self.scenarios_frame = ttk.LabelFrame(self.scenarios_left_paned, text="Scenarios")
        self.scenarios_left_paned.add(self.scenarios_frame, weight=1)
        
        # Create scenarios treeview
        self.scenarios_tree = ttk.Treeview(self.scenarios_frame, columns=("id", "name", "description"))
        self.scenarios_tree.heading("#0", text="")
        self.scenarios_tree.heading("id", text="ID")
        self.scenarios_tree.heading("name", text="Name")
        self.scenarios_tree.heading("description", text="Description")
        self.scenarios_tree.column("#0", width=0, stretch=tk.NO)
        self.scenarios_tree.column("id", width=80, stretch=tk.NO)
        self.scenarios_tree.column("name", width=150)
        self.scenarios_tree.column("description", width=250)
        
        # Add scrollbar to scenarios treeview
        scenarios_scrollbar = ttk.Scrollbar(self.scenarios_frame, orient=tk.VERTICAL, command=self.scenarios_tree.yview)
        self.scenarios_tree.configure(yscrollcommand=scenarios_scrollbar.set)
        
        # Pack scenarios treeview and scrollbar
        self.scenarios_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scenarios_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create episodes frame
        self.episodes_frame = ttk.LabelFrame(self.scenarios_left_paned, text="Episodes")
        self.scenarios_left_paned.add(self.episodes_frame, weight=1)
        
        # Create episodes treeview
        self.episodes_tree = ttk.Treeview(self.episodes_frame, columns=("id", "name", "status"))
        self.episodes_tree.heading("#0", text="")
        self.episodes_tree.heading("id", text="ID")
        self.episodes_tree.heading("name", text="Name")
        self.episodes_tree.heading("status", text="Status")
        self.episodes_tree.column("#0", width=0, stretch=tk.NO)
        self.episodes_tree.column("id", width=80, stretch=tk.NO)
        self.episodes_tree.column("name", width=150)
        self.episodes_tree.column("status", width=100)
        
        # Add scrollbar to episodes treeview
        episodes_scrollbar = ttk.Scrollbar(self.episodes_frame, orient=tk.VERTICAL, command=self.episodes_tree.yview)
        self.episodes_tree.configure(yscrollcommand=episodes_scrollbar.set)
        
        # Pack episodes treeview and scrollbar
        self.episodes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        episodes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection events
        self.scenarios_tree.bind("<<TreeviewSelect>>", self.on_scenario_selected)
        self.episodes_tree.bind("<<TreeviewSelect>>", self.on_episode_selected)
    
    def setup_scenarios_right_column(self):
        """Setup the right column of the Scenarios tab"""
        # Create vertical paned window for steps and details
        self.scenarios_right_paned = ttk.PanedWindow(self.scenarios_right_column, orient=tk.VERTICAL)
        self.scenarios_right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create steps frame
        self.steps_frame = ttk.LabelFrame(self.scenarios_right_paned, text="Steps")
        self.scenarios_right_paned.add(self.steps_frame, weight=1)
        
        # Create steps treeview
        self.steps_tree = ttk.Treeview(self.steps_frame, columns=("id", "description", "created_at"))
        self.steps_tree.heading("#0", text="")
        self.steps_tree.heading("id", text="ID")
        self.steps_tree.heading("description", text="Description")
        self.steps_tree.heading("created_at", text="Created At")
        self.steps_tree.column("#0", width=0, stretch=tk.NO)
        self.steps_tree.column("id", width=80, stretch=tk.NO)
        self.steps_tree.column("description", width=200)
        self.steps_tree.column("created_at", width=150)
        
        # Add scrollbar to steps treeview
        steps_scrollbar = ttk.Scrollbar(self.steps_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand=steps_scrollbar.set)
        
        # Pack steps treeview and scrollbar
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        steps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create details frame
        self.details_frame = ttk.LabelFrame(self.scenarios_right_paned, text="Step Details & Conversations")
        self.scenarios_right_paned.add(self.details_frame, weight=1)
        
        # Create notebook for step details and conversations
        self.details_notebook = ttk.Notebook(self.details_frame)
        self.details_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create step details tab
        self.step_details_tab = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.step_details_tab, text="Step Details")
        
        # Create conversations tab
        self.conversations_tab = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.conversations_tab, text="Conversations")
        
        # Create chat display frame in conversations tab
        self.chat_display = ChatDisplayFrame(self.conversations_tab)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Create step details display in step details tab
        self.step_details_text = scrolledtext.ScrolledText(self.step_details_tab, wrap=tk.WORD)
        self.step_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.step_details_text.config(state=tk.DISABLED)
        
        # Bind selection events
        self.steps_tree.bind("<<TreeviewSelect>>", self.on_step_selected)
    
    def setup_users_tab(self):
        """Setup the Users tab content"""
        # Create main paned window for two-column layout
        self.users_paned = ttk.PanedWindow(self.users_tab, orient=tk.HORIZONTAL)
        self.users_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left column (user list and profile)
        self.users_left_column = ttk.Frame(self.users_paned)
        self.users_paned.add(self.users_left_column, weight=1)
        
        # Create right column (memories and chat)
        self.users_right_column = ttk.Frame(self.users_paned)
        self.users_paned.add(self.users_right_column, weight=1)
        
        # Setup left column of Users tab
        self.setup_users_left_column()
        
        # Setup right column of Users tab
        self.setup_users_right_column()
    
    def setup_users_left_column(self):
        """Setup the left column of the Users tab"""
        # Create vertical paned window for user list and profile
        self.users_left_paned = ttk.PanedWindow(self.users_left_column, orient=tk.VERTICAL)
        self.users_left_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create user list frame
        self.user_list_frame = ttk.LabelFrame(self.users_left_paned, text="User List")
        self.users_left_paned.add(self.user_list_frame, weight=1)
        
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
        self.user_profile_frame = ttk.LabelFrame(self.users_left_paned, text="User Profile")
        self.users_left_paned.add(self.user_profile_frame, weight=1)
        
        # Create user profile display
        self.user_profile = UserProfileFrame(self.user_profile_frame, self.db)
        self.user_profile.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection events
        self.users_tree.bind("<<TreeviewSelect>>", self.on_user_selected)
    
    def setup_users_right_column(self):
        """Setup the right column of the Users tab"""
        # Create vertical paned window for memories and chat
        self.users_right_paned = ttk.PanedWindow(self.users_right_column, orient=tk.VERTICAL)
        self.users_right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create memories frame
        self.memories_frame = ttk.LabelFrame(self.users_right_paned, text="User Memories")
        self.users_right_paned.add(self.memories_frame, weight=1)
        
        # Create memories display with pagination
        self.memories_display = MemoryPaginationFrame(self.memories_frame, self.db)
        self.memories_display.pack(fill=tk.BOTH, expand=True)
        
        # Create chat frame
        self.chat_frame = ttk.LabelFrame(self.users_right_paned, text="Chat with User")
        self.users_right_paned.add(self.chat_frame, weight=1)
        
        # Create chat interface
        self.user_chat_frame = UserChatFrame(self.chat_frame)
        self.user_chat_frame.pack(fill=tk.BOTH, expand=True)

    def load_scenarios(self):
        """Load scenarios from the database."""
        if self.db is None:
            messagebox.showerror("Database Error", "No database connection available.")
            return
            
        try:
            # Clear existing items
            for item in self.scenarios_tree.get_children():
                self.scenarios_tree.delete(item)
                
            # Get all scenarios
            scenarios = self.db.query(Scenario).all()
            
            # Add to treeview
            for scenario in scenarios:
                self.scenarios_tree.insert("", "end", scenario.id, 
                                          values=(scenario.id, scenario.name, scenario.description))
                
            print(f"Loaded {len(scenarios)} scenarios")
            
        except Exception as e:
            print(f"Exception in load_scenarios: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Database Error", f"Failed to load scenarios: {str(e)}")
            
            # Try to reconnect
            self.reconnect_db()
    
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
            
            # Try to reconnect
            self.reconnect_db()
    
    def reconnect_db(self):
        """Attempt to reconnect to the database."""
        try:
            print("Attempting to reconnect to database...")
            if hasattr(self, 'db') and self.db is not None:
                self.db.close()
            
            self.db = next(get_db())
            print("Successfully reconnected to database")
            return True
        except Exception as e:
            print(f"Failed to reconnect to database: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to reconnect to database: {str(e)}")
            self.db = None
            return False

    def on_scenario_selected(self, event):
        """Handle scenario selection."""
        item_id = self.scenarios_tree.focus()
        if not item_id or self.db is None:
            return
            
        try:
            # Get the scenario ID
            scenario_id = uuid.UUID(item_id)
            
            # Clear episodes, steps, and step details
            for item in self.episodes_tree.get_children():
                self.episodes_tree.delete(item)
                
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
                
            self.step_details_text.config(state=tk.NORMAL)
            self.step_details_text.delete(1.0, tk.END)
            self.step_details_text.config(state=tk.DISABLED)
            
            self.chat_display.display_messages([])
            
            # Load episodes for this scenario
            episodes = self.db.query(Episode).filter(Episode.scenario_id == scenario_id).all()
            
            # Add episodes to tree
            for episode in episodes:
                self.episodes_tree.insert("", "end", str(episode.id), 
                                         values=(episode.id, episode.name, episode.status))
                
        except Exception as e:
            print(f"Exception in on_scenario_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load episodes: {str(e)}")
            
            # Try to reconnect if there's a database error
            self.reconnect_db()
    
    def on_episode_selected(self, event):
        """Handle episode selection."""
        item_id = self.episodes_tree.focus()
        if not item_id or self.db is None:
            return
            
        try:
            # Get the episode ID
            episode_id = uuid.UUID(item_id)
            
            # Clear steps and step details
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
                
            self.step_details_text.config(state=tk.NORMAL)
            self.step_details_text.delete(1.0, tk.END)
            self.step_details_text.config(state=tk.DISABLED)
            
            self.chat_display.display_messages([])
            
            # Load steps for this episode
            steps = self.db.query(Step).filter(Step.episode_id == episode_id).order_by(Step.created_at).all()
            
            # Add steps to tree
            for step in steps:
                description = f"{step.action}" if step.action else "No action"
                self.steps_tree.insert("", "end", str(step.id), 
                                      values=(step.id, description, step.created_at))
                
        except Exception as e:
            print(f"Exception in on_episode_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load steps: {str(e)}")
            
            # Try to reconnect if there's a database error
            self.reconnect_db()

    def on_step_selected(self, event):
        """Handle step selection."""
        item_id = self.steps_tree.focus()
        if not item_id or self.db is None:
            return
            
        try:
            # Get the step from the database
            step_id = uuid.UUID(item_id)
            step = self.db.query(Step).filter(Step.id == step_id).first()
            
            if not step:
                return
                
            # Display step details
            self.step_details_text.config(state=tk.NORMAL)
            self.step_details_text.delete(1.0, tk.END)
            
            self.step_details_text.insert(tk.END, f"Step ID: {step.id}\n\n")
            self.step_details_text.insert(tk.END, f"Episode ID: {step.episode_id}\n\n")
            
            if step.state:
                self.step_details_text.insert(tk.END, f"State: {step.state.name}\n")
                self.step_details_text.insert(tk.END, f"State Description: {step.state.description}\n\n")
            
            if step.user:
                self.step_details_text.insert(tk.END, f"User: {step.user.username}\n\n")
                
            self.step_details_text.insert(tk.END, f"Action: {step.action}\n\n")
            self.step_details_text.insert(tk.END, f"Created At: {step.created_at}\n\n")
            
            if step.generated_text:
                self.step_details_text.insert(tk.END, "Generated Text:\n")
                self.step_details_text.insert(tk.END, f"{step.generated_text}\n\n")
                
            self.step_details_text.config(state=tk.DISABLED)
            
            # Load conversations for this step
            conversations = get_conversations_for_step(self.db, step.id)
            
            if conversations:
                # If multiple conversations, use the first one for now
                # In a real app, we might want to have tabs for each conversation
                conversation = conversations[0]
                
                # Get messages for this conversation
                messages = get_messages_for_conversation(self.db, conversation.id)
                
                if messages:
                    # Format messages for display
                    formatted_messages = format_messages(messages)
                    # Display messages
                    self.chat_display.display_messages(formatted_messages)
                else:
                    self.chat_display.display_messages([])
            else:
                self.chat_display.display_messages([])
                
        except Exception as e:
            print(f"Exception in on_step_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load step details: {str(e)}")
            
            # Try to reconnect if there's a database error
            self.reconnect_db()

    def on_user_selected(self, event):
        item_id = self.users_tree.focus()
        if not item_id or self.db is None:
            return
            
        try:
            print(f"User selected: {item_id}")
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
            
            # Try to reconnect if there's a database error
            self.reconnect_db()


def main():
    root = tk.Tk()
    app = ScenarioVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 