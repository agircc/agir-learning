#!/usr/bin/env python3
"""
Launcher for the AGIR Process Visualizer
"""

import os
import sys
import tkinter as tk
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the visualizer
from src.visualization.process_visualizer import ProcessVisualizer

def main():
    print("Starting AGIR Process Visualizer...")
    root = tk.Tk()
    app = ProcessVisualizer(root)
    root.mainloop()

if __name__ == "__main__":
    main() 