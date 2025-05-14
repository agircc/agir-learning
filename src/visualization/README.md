# Visualization

Visualizes data after scenario construction and evolution.

Construction and evolution processes are located in `src/construction` and `src/evolution` directories.

The visualization shows:
- Scenario information: name, description, learner
- Episodes (previously process instances)
- When clicking on an episode, it displays the steps within that episode
- When clicking on a step, it shows related chat conversations and their messages

All data is retrieved from the database.

To run the visualizer:
```
python -m src.visualization.run_visualizer
```