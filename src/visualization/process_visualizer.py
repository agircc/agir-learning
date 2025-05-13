"""
Process Visualizer using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from agir_db.db.session import get_db
from agir_db.models.process import Process, ProcessNode
from agir_db.models.process_instance import ProcessInstance
from agir_db.models.process_instance_step import ProcessInstanceStep
from agir_db.models.chat_conversation import ChatConversation
from agir_db.models.process_role import ProcessRole

from .chat_utils import get_conversations_for_step, get_messages_for_conversation, format_messages


class ProcessVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("AGIR Process Visualizer")
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
        
        # Create process tab
        self.process_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.process_tab, text="Processes")
        
        # Create process instances tab
        self.instances_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.instances_tab, text="Process Instances")
        
        # Setup process tab
        self.setup_process_tab()
        
        # Setup process instances tab
        self.setup_instances_tab()
        
        # Load initial data
        self.load_processes()

    def setup_process_tab(self):
        # Create frame for process list
        self.process_list_frame = ttk.LabelFrame(self.process_tab, text="Processes")
        self.process_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for process list
        self.process_scroll = ttk.Scrollbar(self.process_list_frame)
        self.process_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create process treeview
        self.process_tree = ttk.Treeview(self.process_list_frame, 
                                         columns=("name", "description", "learner_role"),
                                         show="headings",
                                         yscrollcommand=self.process_scroll.set)
        self.process_scroll.config(command=self.process_tree.yview)
        
        # Configure columns
        self.process_tree.heading("name", text="Name")
        self.process_tree.heading("description", text="Description")
        self.process_tree.heading("learner_role", text="Learner Role")
        self.process_tree.column("name", width=150)
        self.process_tree.column("description", width=300)
        self.process_tree.column("learner_role", width=150)
        
        # Pack the process treeview
        self.process_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.process_tree.bind("<Double-1>", self.on_process_selected)
        
        # Create frame for process details
        self.process_detail_frame = ttk.LabelFrame(self.process_tab, text="Process Details")
        self.process_detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create info frame
        self.info_frame = ttk.Frame(self.process_detail_frame)
        self.info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Process name
        ttk.Label(self.info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.process_name_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.process_name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Process description
        ttk.Label(self.info_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.process_desc_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.process_desc_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Learner role
        ttk.Label(self.info_frame, text="Learner:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.process_learner_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.process_learner_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Create nodes frame
        self.nodes_frame = ttk.LabelFrame(self.process_detail_frame, text="Process Nodes")
        self.nodes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for nodes list
        self.nodes_scroll = ttk.Scrollbar(self.nodes_frame)
        self.nodes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create nodes treeview
        self.nodes_tree = ttk.Treeview(self.nodes_frame, 
                                      columns=("name", "description", "roles"),
                                      show="headings",
                                      yscrollcommand=self.nodes_scroll.set)
        self.nodes_scroll.config(command=self.nodes_tree.yview)
        
        # Configure columns
        self.nodes_tree.heading("name", text="Name")
        self.nodes_tree.heading("description", text="Description")
        self.nodes_tree.heading("roles", text="Roles")
        self.nodes_tree.column("name", width=150)
        self.nodes_tree.column("description", width=300)
        self.nodes_tree.column("roles", width=150)
        
        # Pack the nodes treeview
        self.nodes_tree.pack(fill=tk.BOTH, expand=True)

    def setup_instances_tab(self):
        # Create left frame for instances list
        self.instances_list_frame = ttk.LabelFrame(self.instances_tab, text="Process Instances")
        self.instances_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar for instances list
        self.instances_scroll = ttk.Scrollbar(self.instances_list_frame)
        self.instances_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create instances treeview
        self.instances_tree = ttk.Treeview(self.instances_list_frame, 
                                          columns=("process", "status", "current_node"),
                                          show="headings",
                                          yscrollcommand=self.instances_scroll.set)
        self.instances_scroll.config(command=self.instances_tree.yview)
        
        # Configure columns
        self.instances_tree.heading("process", text="Process")
        self.instances_tree.heading("status", text="Status")
        self.instances_tree.heading("current_node", text="Current Node")
        self.instances_tree.column("process", width=150)
        self.instances_tree.column("status", width=100)
        self.instances_tree.column("current_node", width=150)
        
        # Pack the instances treeview
        self.instances_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind click event
        self.instances_tree.bind("<Double-1>", self.on_instance_selected)
        
        # Create right frame for instance details
        self.instance_detail_frame = ttk.LabelFrame(self.instances_tab, text="Instance Details")
        self.instance_detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for steps and conversations
        self.instance_notebook = ttk.Notebook(self.instance_detail_frame)
        self.instance_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create steps tab
        self.steps_tab = ttk.Frame(self.instance_notebook)
        self.instance_notebook.add(self.steps_tab, text="Steps")
        
        # Create conversations tab
        self.conversations_tab = ttk.Frame(self.instance_notebook)
        self.instance_notebook.add(self.conversations_tab, text="Conversations")
        
        # Set up steps tab
        self.setup_steps_tab()
        
        # Set up conversations tab
        self.setup_conversations_tab()
        
        # Load process instances
        self.load_instances()

    def setup_steps_tab(self):
        # Create scrollbar for steps list
        self.steps_scroll = ttk.Scrollbar(self.steps_tab)
        self.steps_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create steps treeview
        self.steps_tree = ttk.Treeview(self.steps_tab, 
                                      columns=("node", "user", "action", "created_at"),
                                      show="headings",
                                      yscrollcommand=self.steps_scroll.set)
        self.steps_scroll.config(command=self.steps_tree.yview)
        
        # Configure columns
        self.steps_tree.heading("node", text="Node")
        self.steps_tree.heading("user", text="User")
        self.steps_tree.heading("action", text="Action")
        self.steps_tree.heading("created_at", text="Created At")
        self.steps_tree.column("node", width=150)
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

    def load_processes(self):
        try:
            db = next(get_db())
            processes = db.query(Process).all()
            
            # Clear existing items
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)
            
            # Add processes to tree
            for process in processes:
                self.process_tree.insert("", tk.END, iid=str(process.id),
                                       values=(process.name, process.description, process.learner_role))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load processes: {str(e)}")

    def load_instances(self):
        try:
            db = next(get_db())
            instances = db.query(ProcessInstance).all()
            
            # Clear existing items
            for item in self.instances_tree.get_children():
                self.instances_tree.delete(item)
            
            # Add instances to tree
            for instance in instances:
                process_name = instance.process.name if instance.process else "Unknown"
                node_name = instance.current_node.name if instance.current_node else "None"
                
                self.instances_tree.insert("", tk.END, iid=str(instance.id),
                                        values=(process_name, instance.status, node_name))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load process instances: {str(e)}")

    def on_process_selected(self, event):
        item_id = self.process_tree.focus()
        if not item_id:
            return
            
        try:
            process_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get process details
            process = db.query(Process).filter(Process.id == process_id).first()
            if not process:
                return
                
            # Update process info
            self.process_name_var.set(process.name)
            self.process_desc_var.set(process.description if process.description else "")
            self.process_learner_var.set(process.learner_role)
            
            # Clear existing nodes
            for item in self.nodes_tree.get_children():
                self.nodes_tree.delete(item)
            
            # Add nodes to tree
            for node in process.nodes:
                # Get roles for this node
                role_names = []
                for role in node.roles:
                    role_names.append(role.name)
                
                self.nodes_tree.insert("", tk.END, iid=str(node.id),
                                    values=(node.name, node.description, ", ".join(role_names)))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load process details: {str(e)}")

    def on_instance_selected(self, event):
        item_id = self.instances_tree.focus()
        if not item_id:
            return
            
        try:
            instance_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get instance details
            instance = db.query(ProcessInstance).filter(ProcessInstance.id == instance_id).first()
            if not instance:
                return
            
            # Clear existing steps
            for item in self.steps_tree.get_children():
                self.steps_tree.delete(item)
            
            # Get steps for this instance
            steps = db.query(ProcessInstanceStep).filter(
                ProcessInstanceStep.instance_id == instance_id
            ).order_by(ProcessInstanceStep.created_at).all()
            
            # Add steps to tree
            for step in steps:
                node_name = step.node.name if step.node else "Unknown"
                user_name = step.user.name if step.user else "Unknown"
                
                self.steps_tree.insert("", tk.END, iid=str(step.id),
                                    values=(node_name, user_name, step.action, step.created_at))
            
            # Clear conversations tree
            for item in self.conversations_tree.get_children():
                self.conversations_tree.delete(item)
            
            # TODO: Load conversations related to this instance
            # This would require linking conversations to process instances in the database
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load instance details: {str(e)}")

    def on_step_selected(self, event):
        item_id = self.steps_tree.focus()
        if not item_id:
            return
            
        try:
            step_id = uuid.UUID(item_id)
            db = next(get_db())
            
            # Get step details
            step = db.query(ProcessInstanceStep).filter(ProcessInstanceStep.id == step_id).first()
            if not step:
                return
            
            # Clear existing text
            self.step_text.delete(1.0, tk.END)
            
            # Add step details
            self.step_text.insert(tk.END, f"Node: {step.node.name if step.node else 'Unknown'}\n\n")
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
    app = ProcessVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 