#!/usr/bin/env python3
"""
Launcher for the AGIR Scenario Visualizer
"""

import os
import sys
import tkinter as tk
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Add the project root to the path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the visualizer
from src.visualization.scenario_visualizer import ScenarioVisualizer

def main():
    print("Starting AGIR Scenario Visualizer...")
    root = tk.Tk()
    app = ScenarioVisualizer(root)
    root.mainloop()

if __name__ == "__main__":
    main() 