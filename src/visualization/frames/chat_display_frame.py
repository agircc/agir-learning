"""
Chat display frame for showing formatted chat messages
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import random
import colorsys

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