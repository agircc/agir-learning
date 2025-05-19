"""
Scenario Visualizer using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
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

from .frames.scenarios_tab import ScenariosTab
from .frames.users_tab import UsersTab


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
        
        # Create and add Scenarios tab
        self.scenarios_tab = ScenariosTab(self.notebook, self.db)
        self.notebook.add(self.scenarios_tab, text="Scenarios")
        
        # Create and add Users tab
        self.users_tab = UsersTab(self.notebook, self.db)
        self.notebook.add(self.users_tab, text="Users")
        
        # Load initial data
        self.scenarios_tab.load_scenarios()
        self.users_tab.load_users()
        
        # Add tab change handler
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
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
        # Close any active chat session when switching tabs
        if self.notebook.index(self.notebook.select()) == 1:  # Users tab
            pass  # Nothing special when switching to Users tab
        else:  # Scenarios tab or any other tab
            self.users_tab.close_chat_session()
    
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


def main():
    root = tk.Tk()
    app = ScenarioVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 