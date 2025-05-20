"""
Scenarios tab for visualization of scenarios, episodes, and steps
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import uuid

from agir_db.models.scenario import Scenario
from agir_db.models.episode import Episode
from agir_db.models.step import Step

from .chat_display_frame import ChatDisplayFrame
from ..chat_utils import get_conversations_for_step, get_messages_for_conversation, format_messages

class ScenariosTab(ttk.Frame):
    """Class for managing the Scenarios tab content"""
    
    def __init__(self, parent, db, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.db = db
        
        # Create main paned window for two-column layout
        self.scenarios_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.scenarios_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left column (scenarios and episodes)
        self.left_column = ttk.Frame(self.scenarios_paned)
        self.scenarios_paned.add(self.left_column, weight=1)
        
        # Create right column (steps and step details/conversations)
        self.right_column = ttk.Frame(self.scenarios_paned)
        self.scenarios_paned.add(self.right_column, weight=1)
        
        # Setup left column
        self.setup_left_column()
        
        # Setup right column
        self.setup_right_column()
        
    def setup_left_column(self):
        """Setup the left column of the Scenarios tab"""
        # Create vertical paned window for scenarios and episodes
        self.left_paned = ttk.PanedWindow(self.left_column, orient=tk.VERTICAL)
        self.left_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create scenarios frame
        self.scenarios_frame = ttk.LabelFrame(self.left_paned, text="Scenarios")
        self.left_paned.add(self.scenarios_frame, weight=1)
        
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
        self.episodes_frame = ttk.LabelFrame(self.left_paned, text="Episodes")
        self.left_paned.add(self.episodes_frame, weight=1)
        
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
    
    def setup_right_column(self):
        """Setup the right column of the Scenarios tab"""
        # Create vertical paned window for steps and details
        self.right_paned = ttk.PanedWindow(self.right_column, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create steps frame
        self.steps_frame = ttk.LabelFrame(self.right_paned, text="Steps")
        self.right_paned.add(self.steps_frame, weight=1)
        
        # Create steps treeview
        self.steps_tree = ttk.Treeview(self.steps_frame, columns=("id", "description", "state", "created_at"))
        self.steps_tree.heading("#0", text="")
        self.steps_tree.heading("id", text="ID")
        self.steps_tree.heading("description", text="Description")
        self.steps_tree.heading("state", text="State")
        self.steps_tree.heading("created_at", text="Created At")
        self.steps_tree.column("#0", width=0, stretch=tk.NO)
        self.steps_tree.column("id", width=80, stretch=tk.NO)
        self.steps_tree.column("description", width=200)
        self.steps_tree.column("state", width=150)
        self.steps_tree.column("created_at", width=150)
        
        # Add scrollbar to steps treeview
        steps_scrollbar = ttk.Scrollbar(self.steps_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand=steps_scrollbar.set)
        
        # Pack steps treeview and scrollbar
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        steps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create details frame
        self.details_frame = ttk.LabelFrame(self.right_paned, text="Step Details & Conversations")
        self.right_paned.add(self.details_frame, weight=1)
        
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
                self.scenarios_tree.insert("", "end", str(scenario.id), 
                                          values=(scenario.id, scenario.name, scenario.description))
                
            print(f"Loaded {len(scenarios)} scenarios")
            
        except Exception as e:
            print(f"Exception in load_scenarios: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Database Error", f"Failed to load scenarios: {str(e)}")
    
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
                                         values=(episode.id, f"Episode {episode.id}", episode.status))
                
        except Exception as e:
            print(f"Exception in on_scenario_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load episodes: {str(e)}")
    
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
                state_name = step.state.name if step.state else "N/A"
                self.steps_tree.insert("", "end", str(step.id), 
                                      values=(step.id, description, state_name, step.created_at))
                
        except Exception as e:
            print(f"Exception in on_episode_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load steps: {str(e)}")
    
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