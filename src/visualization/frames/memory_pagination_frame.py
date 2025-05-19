"""
Memory pagination frame for displaying user memories with paging controls
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from agir_db.models.memory import UserMemory

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