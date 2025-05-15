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
        
        # Create main paned window for two-column layout
        self.main_paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left column (scenarios and episodes)
        self.left_column = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_column, weight=1)
        
        # Create right column (steps and step details/conversations)
        self.right_column = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_column, weight=1)
        
        # Setup left column
        self.setup_left_column()
        
        # Setup right column
        self.setup_right_column()
        
        # Load scenarios data
        self.load_scenarios()

    def setup_left_column(self):
        # Create vertical paned window for scenarios and episodes
        self.left_paned = ttk.PanedWindow(self.left_column, orient=tk.VERTICAL)
        self.left_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create scenarios frame
        self.scenarios_frame = ttk.LabelFrame(self.left_paned, text="Scenarios")
        self.left_paned.add(self.scenarios_frame, weight=1)
        
        # Create scrollbar for scenarios
        self.scenarios_scroll = ttk.Scrollbar(self.scenarios_frame)
        self.scenarios_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create scenarios treeview
        self.scenarios_tree = ttk.Treeview(self.scenarios_frame, 
                                          columns=("name", "description", "learner_role"),
                                          show="headings",
                                          yscrollcommand=self.scenarios_scroll.set)
        self.scenarios_scroll.config(command=self.scenarios_tree.yview)
        
        # Configure columns
        self.scenarios_tree.heading("name", text="Name")
        self.scenarios_tree.heading("description", text="Description")
        self.scenarios_tree.heading("learner_role", text="Learner Role")
        self.scenarios_tree.column("name", width=150)
        self.scenarios_tree.column("description", width=300)
        self.scenarios_tree.column("learner_role", width=150)
        
        # Pack the scenarios treeview
        self.scenarios_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.scenarios_tree.bind("<Double-1>", self.on_scenario_selected)
        
        # Create episodes frame
        self.episodes_frame = ttk.LabelFrame(self.left_paned, text="Episodes")
        self.left_paned.add(self.episodes_frame, weight=1)
        
        # Create scrollbar for episodes
        self.episodes_scroll = ttk.Scrollbar(self.episodes_frame)
        self.episodes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create episodes treeview
        self.episodes_tree = ttk.Treeview(self.episodes_frame, 
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

    def setup_right_column(self):
        # Create vertical paned window for steps and details
        self.right_paned = ttk.PanedWindow(self.right_column, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Create steps frame
        self.steps_frame = ttk.LabelFrame(self.right_paned, text="Steps")
        self.right_paned.add(self.steps_frame, weight=1)
        
        # Create scrollbar for steps
        self.steps_scroll = ttk.Scrollbar(self.steps_frame)
        self.steps_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create steps treeview
        self.steps_tree = ttk.Treeview(self.steps_frame, 
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
        
        # Create details paned window (horizontal)
        self.details_paned = ttk.PanedWindow(self.right_paned, orient=tk.HORIZONTAL)
        self.right_paned.add(self.details_paned, weight=1)
        
        # Create step details frame
        self.step_detail_frame = ttk.LabelFrame(self.details_paned, text="Step Details")
        self.details_paned.add(self.step_detail_frame, weight=1)
        
        # Create text widget for step details
        self.step_text = tk.Text(self.step_detail_frame, wrap=tk.WORD)
        self.step_text.pack(fill=tk.BOTH, expand=True)
        
        # Create conversation frame
        self.conversation_frame = ttk.LabelFrame(self.details_paned, text="Conversation")
        self.details_paned.add(self.conversation_frame, weight=1)
        
        # Create enhanced chat display widget for conversation
        self.conversation_display = ChatDisplayFrame(self.conversation_frame)
        self.conversation_display.pack(fill=tk.BOTH, expand=True)

    def load_scenarios(self):
        db = None
        try:
            print("Attempting to get database session...")
            db = next(get_db())
            print(f"Got database session: {db}")
            
            print("Querying scenarios...")
            scenarios = db.query(Scenario).all()
            print(f"Found {len(scenarios)} scenarios")
            
            # Clear existing items
            for item in self.scenarios_tree.get_children():
                self.scenarios_tree.delete(item)
            
            # Add scenarios to tree
            for scenario in scenarios:
                print(f"Adding scenario: {scenario.id} - {scenario.name}")
                self.scenarios_tree.insert("", tk.END, iid=str(scenario.id),
                                        values=(scenario.name, scenario.description, scenario.learner_role))
        except Exception as e:
            print(f"Exception in load_scenarios: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load scenarios: {str(e)}")
        finally:
            if db:
                db.close()
                print("Database session closed")

    def on_scenario_selected(self, event):
        item_id = self.scenarios_tree.focus()
        if not item_id:
            return
            
        db = None
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
            
            # Clear episodes tree
            for item in self.episodes_tree.get_children():
                self.episodes_tree.delete(item)
                
            # Clear steps tree
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
                
            # Clear step details and conversation
            self.step_text.delete(1.0, tk.END)
            self.conversation_display.display_messages([])
            
            # Get episodes for this scenario
            print(f"Getting episodes for scenario: {scenario_id}")
            episodes = db.query(Episode).filter(
                Episode.scenario_id == scenario_id
            ).all()
            print(f"Found {len(episodes)} episodes")
            
            # Add episodes to tree
            for episode in episodes:
                state_name = episode.current_state.name if episode.current_state else "None"
                print(f"Adding episode: {episode.id} - {episode.status} - {state_name}")
                self.episodes_tree.insert("", tk.END, iid=str(episode.id),
                                       values=(scenario.name, episode.status, state_name))
                
        except Exception as e:
            print(f"Exception in on_scenario_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load scenario episodes: {str(e)}")
        finally:
            if db:
                db.close()
                print("Database session closed for scenario selection")

    def on_episode_selected(self, event):
        item_id = self.episodes_tree.focus()
        if not item_id:
            return
            
        db = None
        try:
            print(f"Episode selected: {item_id}")
            episode_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get episode details
            print(f"Querying episode details for ID: {episode_id}")
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                print("Episode not found")
                return
            
            # Clear steps tree
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
            
            # Clear step details and conversation
            self.step_text.delete(1.0, tk.END)
            self.conversation_display.display_messages([])
            
            # Get steps for this episode
            print(f"Getting steps for episode: {episode_id}")
            steps = db.query(Step).filter(
                Step.episode_id == episode_id
            ).order_by(Step.created_at).all()
            print(f"Found {len(steps)} steps")
            
            # Add steps to tree
            for step in steps:
                state_name = step.state.name if step.state else "Unknown"
                user_name = step.user.username if step.user else "Unknown"
                print(f"Adding step: {step.id}, state: {state_name}, user: {user_name}")
                
                self.steps_tree.insert("", tk.END, iid=str(step.id),
                                    values=(state_name, user_name, step.action, step.created_at))
            
        except Exception as e:
            print(f"Exception in on_episode_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load episode details: {str(e)}")
        finally:
            if db:
                db.close()
                print("Database session closed for episode details")

    def on_step_selected(self, event):
        item_id = self.steps_tree.focus()
        if not item_id:
            return
            
        db = None
        try:
            print(f"Step selected: {item_id}")
            step_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get step details
            print(f"Querying step details for ID: {step_id}")
            step = db.query(Step).filter(Step.id == step_id).first()
            if not step:
                print("Step not found")
                return
            
            # Clear existing text
            self.step_text.delete(1.0, tk.END)
            
            # Add step details
            self.step_text.insert(tk.END, f"State: {step.state.name if step.state else 'Unknown'}\n\n")
            self.step_text.insert(tk.END, f"Action: {step.action}\n\n")
            self.step_text.insert(tk.END, f"User: {step.user.username if step.user else 'Unknown'}\n\n")
            self.step_text.insert(tk.END, f"Created At: {step.created_at}\n\n")
            
            # Add generated text if available
            if step.generated_text:
                self.step_text.insert(tk.END, "Generated Text:\n\n")
                self.step_text.insert(tk.END, step.generated_text)
            
            # Load related conversations
            print(f"Getting conversations for step: {step_id}")
            conversations = get_conversations_for_step(db, step_id)
            print(f"Found {len(conversations)} conversations")
            
            # If there are conversations, display the first one
            if conversations:
                conversation = conversations[0]  # Display first conversation
                print(f"Displaying conversation: {conversation.id} - {conversation.title}")
                
                # Get and display messages
                messages = get_messages_for_conversation(db, conversation.id)
                if messages:
                    formatted_messages = format_messages(messages)
                    # Display using our enhanced chat display
                    self.conversation_display.display_messages(formatted_messages)
                else:
                    # No messages
                    self.conversation_display.display_messages([])
            else:
                # No conversations
                self.conversation_display.display_messages([])
            
        except Exception as e:
            print(f"Exception in on_step_selected: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load step details: {str(e)}")
        finally:
            if db:
                db.close()
                print("Database session closed for step details")


def main():
    root = tk.Tk()
    app = ScenarioVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 