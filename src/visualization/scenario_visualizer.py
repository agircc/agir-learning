"""
Scenario Visualizer using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
import os

from agir_db.db.session import get_db
# Debug print to see database configuration
try:
    from agir_db.db.session import SQLALCHEMY_DATABASE_URI
    print(f"Visualization is using database URI: {SQLALCHEMY_DATABASE_URI}")
except Exception as e:
    print(f"Could not import database URI: {e}")
    
# Print environment variable directly for comparison
print(f"Environment DATABASE_URI: {os.environ.get('SQLALCHEMY_DATABASE_URI')}")

from agir_db.models.scenario import Scenario, State
from agir_db.models.episode import Episode
from agir_db.models.step import Step
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.agent_role import AgentRole

from .chat_utils import get_conversations_for_step, get_messages_for_conversation, format_messages


class ScenarioVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("AGIR Scenario Visualizer")
        self.root.geometry("1200x800")
        
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
        
        # Create scenario tab
        self.scenario_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scenario_tab, text="Scenarios")
        
        # Create episodes tab
        self.episodes_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.episodes_tab, text="Episodes")
        
        # Setup scenario tab
        self.setup_scenario_tab()
        
        # Setup episodes tab
        self.setup_episodes_tab()
        
        # Load initial data
        self.load_scenarios()

    def setup_scenario_tab(self):
        # Create frame for scenario list
        self.scenario_list_frame = ttk.LabelFrame(self.scenario_tab, text="Scenarios")
        self.scenario_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for scenario list
        self.scenario_scroll = ttk.Scrollbar(self.scenario_list_frame)
        self.scenario_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create scenario treeview
        self.scenario_tree = ttk.Treeview(self.scenario_list_frame, 
                                         columns=("name", "description", "learner_role"),
                                         show="headings",
                                         yscrollcommand=self.scenario_scroll.set)
        self.scenario_scroll.config(command=self.scenario_tree.yview)
        
        # Configure columns
        self.scenario_tree.heading("name", text="Name")
        self.scenario_tree.heading("description", text="Description")
        self.scenario_tree.heading("learner_role", text="Learner Role")
        self.scenario_tree.column("name", width=150)
        self.scenario_tree.column("description", width=300)
        self.scenario_tree.column("learner_role", width=150)
        
        # Pack the scenario treeview
        self.scenario_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.scenario_tree.bind("<Double-1>", self.on_scenario_selected)
        
        # Create frame for scenario details
        self.scenario_detail_frame = ttk.LabelFrame(self.scenario_tab, text="Scenario Details")
        self.scenario_detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create info frame
        self.info_frame = ttk.Frame(self.scenario_detail_frame)
        self.info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Scenario name
        ttk.Label(self.info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.scenario_name_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.scenario_name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Scenario description
        ttk.Label(self.info_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.scenario_desc_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.scenario_desc_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Learner role
        ttk.Label(self.info_frame, text="Learner:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.scenario_learner_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.scenario_learner_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Create states frame
        self.states_frame = ttk.LabelFrame(self.scenario_detail_frame, text="States")
        self.states_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for states list
        self.states_scroll = ttk.Scrollbar(self.states_frame)
        self.states_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create states treeview
        self.states_tree = ttk.Treeview(self.states_frame, 
                                      columns=("name", "description", "roles"),
                                      show="headings",
                                      yscrollcommand=self.states_scroll.set)
        self.states_scroll.config(command=self.states_tree.yview)
        
        # Configure columns
        self.states_tree.heading("name", text="Name")
        self.states_tree.heading("description", text="Description")
        self.states_tree.heading("roles", text="Roles")
        self.states_tree.column("name", width=150)
        self.states_tree.column("description", width=300)
        self.states_tree.column("roles", width=150)
        
        # Pack the states treeview
        self.states_tree.pack(fill=tk.BOTH, expand=True)

    def setup_episodes_tab(self):
        # Create left frame for episodes list
        self.episodes_list_frame = ttk.LabelFrame(self.episodes_tab, text="Episodes")
        self.episodes_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for episodes list
        self.episodes_scroll = ttk.Scrollbar(self.episodes_list_frame)
        self.episodes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create episodes treeview
        self.episodes_tree = ttk.Treeview(self.episodes_list_frame, 
                                          columns=("scenario", "status", "current_state"),
                                          show="headings",
                                          yscrollcommand=self.episodes_scroll.set)
        self.episodes_scroll.config(command=self.episodes_tree.yview)
        
        # Configure columns
        self.episodes_tree.heading("scenario", text="Scenario")
        self.episodes_tree.heading("status", text="Status")
        self.episodes_tree.heading("current_state", text="Current State")
        self.episodes_tree.column("scenario", width=150)
        self.episodes_tree.column("status", width=100)
        self.episodes_tree.column("current_state", width=150)
        
        # Pack the episodes treeview
        self.episodes_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.episodes_tree.bind("<Double-1>", self.on_episode_selected)
        
        # Create right frame for episode details
        self.episode_detail_frame = ttk.LabelFrame(self.episodes_tab, text="Episode Details")
        self.episode_detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for steps and conversations
        self.episode_notebook = ttk.Notebook(self.episode_detail_frame)
        self.episode_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create steps tab
        self.steps_tab = ttk.Frame(self.episode_notebook)
        self.episode_notebook.add(self.steps_tab, text="Steps")
        
        # Create conversations tab
        self.conversations_tab = ttk.Frame(self.episode_notebook)
        self.episode_notebook.add(self.conversations_tab, text="Conversations")
        
        # Set up steps tab
        self.setup_steps_tab()
        
        # Set up conversations tab
        self.setup_conversations_tab()
        
        # Load episodes
        self.load_episodes()

    def setup_steps_tab(self):
        # Create scrollbar for steps list
        self.steps_scroll = ttk.Scrollbar(self.steps_tab)
        self.steps_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create steps treeview
        self.steps_tree = ttk.Treeview(self.steps_tab, 
                                      columns=("state", "user", "action", "created_at"),
                                      show="headings",
                                      yscrollcommand=self.steps_scroll.set)
        self.steps_scroll.config(command=self.steps_tree.yview)
        
        # Configure columns
        self.steps_tree.heading("state", text="State")
        self.steps_tree.heading("user", text="User")
        self.steps_tree.heading("action", text="Action")
        self.steps_tree.heading("created_at", text="Created At")
        self.steps_tree.column("state", width=150)
        self.steps_tree.column("user", width=150)
        self.steps_tree.column("action", width=100)
        self.steps_tree.column("created_at", width=150)
        
        # Pack the steps treeview
        self.steps_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.steps_tree.bind("<Double-1>", self.on_step_selected)
        
        # Create step detail frame
        self.step_detail_frame = ttk.LabelFrame(self.steps_tab, text="Step Details")
        self.step_detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget for step details
        self.step_text = tk.Text(self.step_detail_frame, wrap=tk.WORD)
        self.step_text.pack(fill=tk.BOTH, expand=True)

    def setup_conversations_tab(self):
        # Create left frame for conversations list
        self.conversations_list_frame = ttk.Frame(self.conversations_tab)
        self.conversations_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for conversations list
        self.conversations_scroll = ttk.Scrollbar(self.conversations_list_frame)
        self.conversations_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create conversations treeview
        self.conversations_tree = ttk.Treeview(self.conversations_list_frame, 
                                             columns=("title", "created_at"),
                                             show="headings",
                                             yscrollcommand=self.conversations_scroll.set)
        self.conversations_scroll.config(command=self.conversations_tree.yview)
        
        # Configure columns
        self.conversations_tree.heading("title", text="Title")
        self.conversations_tree.heading("created_at", text="Created At")
        self.conversations_tree.column("title", width=200)
        self.conversations_tree.column("created_at", width=150)
        
        # Pack the conversations treeview
        self.conversations_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.conversations_tree.bind("<Double-1>", self.on_conversation_selected)
        
        # Create right frame for conversation messages
        self.messages_frame = ttk.LabelFrame(self.conversations_tab, text="Messages")
        self.messages_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget for messages
        self.messages_text = tk.Text(self.messages_frame, wrap=tk.WORD)
        self.messages_text.pack(fill=tk.BOTH, expand=True)

    def load_scenarios(self):
        try:
            print("Attempting to get database session...")
            db = next(get_db())
            print(f"Got database session: {db}")
            
            print("Querying scenarios...")
            scenarios = db.query(Scenario).all()
            print(f"Found {len(scenarios)} scenarios")
            
            # Clear existing items
            for item in self.scenario_tree.get_children():
                self.scenario_tree.delete(item)
            
            # Add scenarios to tree
            for scenario in scenarios:
                print(f"Adding scenario: {scenario.id} - {scenario.name}")
                self.scenario_tree.insert("", tk.END, iid=str(scenario.id),
                                       values=(scenario.name, scenario.description, scenario.learner_role))
        except Exception as e:
            print(f"Exception in load_scenarios: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load scenarios: {str(e)}")

    def load_episodes(self):
        try:
            print("Attempting to get database session for episodes...")
            db = next(get_db())
            print(f"Got database session for episodes: {db}")
            
            print("Querying episodes...")
            episodes = db.query(Episode).all()
            print(f"Found {len(episodes)} episodes")
            
            # Clear existing items
            for item in self.episodes_tree.get_children():
                self.episodes_tree.delete(item)
            
            # Add episodes to tree
            for episode in episodes:
                scenario_name = episode.scenario.name if episode.scenario else "Unknown"
                state_name = episode.current_state.name if episode.current_state else "None"
                
                print(f"Adding episode: {episode.id} - {scenario_name} - {episode.status}")
                self.episodes_tree.insert("", tk.END, iid=str(episode.id),
                                        values=(scenario_name, episode.status, state_name))
        except Exception as e:
            print(f"Exception in load_episodes: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load episodes: {str(e)}")

    def on_scenario_selected(self, event):
        item_id = self.scenario_tree.focus()
        if not item_id:
            return
            
        try:
            print(f"Scenario selected: {item_id}")
            scenario_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get scenario details
            print(f"Querying scenario details for ID: {scenario_id}")
            scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if not scenario:
                print("Scenario not found")
                return
                
            # Update scenario info
            print(f"Updating scenario info: {scenario.name}")
            self.scenario_name_var.set(scenario.name)
            self.scenario_desc_var.set(scenario.description if scenario.description else "")
            self.scenario_learner_var.set(scenario.learner_role)
            
            # Clear existing states
            for item in self.states_tree.get_children():
                self.states_tree.delete(item)
            
            # Add states to tree
            print(f"Adding {len(scenario.states)} states to tree")
            for state in scenario.states:
                # Get roles for this state
                role_names = []
                print(f"Getting roles for state: {state.name}, {len(state.roles)} roles found")
                for role in state.roles:
                    print(f"Processing role: {role}")
                    role_names.append(role.name)
                
                self.states_tree.insert("", tk.END, iid=str(state.id),
                                    values=(state.name, state.description, ", ".join(role_names)))
        except Exception as e:
            print(f"Exception in on_scenario_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load scenario details: {str(e)}")

    def on_episode_selected(self, event):
        item_id = self.episodes_tree.focus()
        if not item_id:
            return
            
        try:
            episode_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get episode details
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                return
            
            # Clear existing steps
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
            
            # Get steps for this episode
            steps = db.query(Step).filter(
                Step.episode_id == episode_id
            ).order_by(Step.created_at).all()
            
            # Add steps to tree
            for step in steps:
                state_name = step.state.name if step.state else "Unknown"
                user_name = step.user.name if step.user else "Unknown"
                
                self.steps_tree.insert("", tk.END, iid=str(step.id),
                                    values=(state_name, user_name, step.action, step.created_at))
            
            # Clear conversations tree
            for item in self.conversations_tree.get_children():
                self.conversations_tree.delete(item)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load episode details: {str(e)}")

    def on_step_selected(self, event):
        item_id = self.steps_tree.focus()
        if not item_id:
            return
            
        try:
            step_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get step details
            step = db.query(Step).filter(Step.id == step_id).first()
            if not step:
                return
            
            # Clear existing text
            self.step_text.delete(1.0, tk.END)
            
            # Add step details
            self.step_text.insert(tk.END, f"State: {step.state.name if step.state else 'Unknown'}\n\n")
            self.step_text.insert(tk.END, f"Action: {step.action}\n\n")
            self.step_text.insert(tk.END, f"User: {step.user.name if step.user else 'Unknown'}\n\n")
            self.step_text.insert(tk.END, f"Created At: {step.created_at}\n\n")
            
            # Add generated text if available
            if step.generated_text:
                self.step_text.insert(tk.END, "Generated Text:\n\n")
                self.step_text.insert(tk.END, step.generated_text)
            
            # Clear conversations tree
            for item in self.conversations_tree.get_children():
                self.conversations_tree.delete(item)
            
            # Load related conversations
            conversations = get_conversations_for_step(db, step_id)
            for conversation in conversations:
                self.conversations_tree.insert("", tk.END, iid=str(conversation.id),
                                            values=(conversation.title, conversation.created_at))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load step details: {str(e)}")

    def on_conversation_selected(self, event):
        item_id = self.conversations_tree.focus()
        if not item_id:
            return
            
        try:
            conversation_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get conversation details
            conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
            if not conversation:
                return
            
            # Clear existing text
            self.messages_text.delete(1.0, tk.END)
            
            # Get messages for this conversation
            messages = get_messages_for_conversation(db, conversation_id)
            
            # Format and display messages
            self.messages_text.insert(tk.END, f"Title: {conversation.title}\n\n")
            self.messages_text.insert(tk.END, f"Created At: {conversation.created_at}\n\n")
            
            if messages:
                formatted_messages = format_messages(messages)
                self.messages_text.insert(tk.END, formatted_messages)
            else:
                self.messages_text.insert(tk.END, "No messages found for this conversation.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load conversation details: {str(e)}")


def main():
    root = tk.Tk()
    app = ScenarioVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 