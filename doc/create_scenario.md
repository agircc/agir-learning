# Creating and Running AGIR Learning Scenarios

This document provides detailed guidance on creating, running AGIR Learning scenarios, and viewing the results.

## Creating Scenarios

AGIR Learning scenarios are defined through YAML files, which describe the learning environment, participants, and interaction flow.

### YAML Format Specification

Scenario YAML files need to include the following main components:

```yaml
scenario:
  name: "Scenario Name"
  description: "Detailed scenario description"

  # Learner definition (the core user whose skills are being developed)
  learner:
    username: "username"  # Username in the database
    first_name: "First"
    last_name: "Last"
    model: "gpt-4"  # LLM model used by the learner
    evolution_objective: "Learning objective description"

  # Role definitions (agents in the scenario)
  roles:
    - name: "role1"
      model: "gpt-4"  # Each role can use different LLM models
      description: "Description of role1"
    - name: "role2"
      model: "gpt-3.5-turbo"
      description: "Description of role2"

  # State definitions (steps in the scenario)
  states:
    - name: "state1"
      role: "role1"  # Which role this state belongs to
      description: "Description of state1"
    - name: "state2"
      role: "learner"  # role="learner" indicates this is an action by the learner
      description: "Description of state2"

  # State transition definitions (flow relationships between states)
  transitions:
    - from: "state1"
      to: "state2"
    - from: "state2"
      to: "state3"

  # Evolution definition (how the learner improves skills)
  evolution:
    method: "Evolution method name"
    description: "Evolution method description"
    knowledge_sources:
      - "Knowledge source 1"
      - "Knowledge source 2"
```

### YAML Example: Medical Diagnosis Training

Here is an example scenario for providing diagnostic training to medical students:

```yaml
scenario:
  name: "Medical Diagnosis Training"
  description: "Patient diagnosis training for medical students"

  learner:
    username: "medical_student"
    first_name: "John"
    last_name: "Doctor"
    model: "gpt-4"
    evolution_objective: "Improve diagnostic skills and patient communication"

  roles:
    - name: "patient"
      model: "gpt-4"
      description: "Patient with various symptoms seeking diagnosis"
    - name: "nurse"
      model: "gpt-3.5-turbo"
      description: "Assists with patient information and preliminary assessment"

  states:
    - name: "patient_reception"
      role: "nurse"
      description: "Initial collection of patient information"
    - name: "patient_interview"
      role: "learner"
      description: "Medical student inquires about patient symptoms"
    - name: "diagnosis_formulation"
      role: "learner"
      description: "Medical student formulates a diagnosis"
    - name: "treatment_plan"
      role: "learner"
      description: "Medical student proposes treatment recommendations"
    - name: "patient_feedback"
      role: "patient"
      description: "Patient feedback on the diagnosis and treatment"

  transitions:
    - from: "patient_reception"
      to: "patient_interview"
    - from: "patient_interview"
      to: "diagnosis_formulation"
    - from: "diagnosis_formulation"
      to: "treatment_plan"
    - from: "treatment_plan"
      to: "patient_feedback"

  evolution:
    method: "Feedback Learning"
    description: "Improve diagnosis accuracy through patient feedback and self-reflection"
    knowledge_sources:
      - "Medical textbooks"
      - "Clinical guidelines"
      - "Expert advice"
```

### Best Practices for Creating Scenarios

1. **Clear Learning Objectives**: Ensure that the skills the learner should acquire are clearly defined in `evolution_objective`
2. **Design Reasonable State Transitions**: State transitions should reflect real interaction processes
3. **Role Definitions Should Match the Scenario**: Each role's description should be detailed and align with its purpose in the scenario
4. **Allocate LLM Models Appropriately**: Use more powerful models for complex roles and lighter models for simpler roles

## Running Scenarios

After creating the YAML file, you can run the scenario using the provided Makefile commands.

### Basic Run Command

```bash
# Run the default scenario (scenarios/hello.yml)
make learning

# Run a specific scenario
make learning SCENARIO=path/to/scenario.yml
```

This will perform two steps:
1. Initialize the scenario (import YAML configuration into the database)
2. Execute the scenario (create an episode and run it)

### Running Multiple Episodes

You can specify how many episodes to run using the EPISODES parameter:

```bash
# Run 3 episodes
make learning SCENARIO=path/to/scenario.yml EPISODES=3
```

### Advanced Run Options

For more advanced options not covered by the Makefile, you can use the underlying Python command:

```bash
# Initialize the scenario only, without executing
make run_init SCENARIO=path/to/scenario.yml

# Run with an existing scenario ID
make run_existing SCENARIO_ID=123

# Only set up the scenario but don't execute
make setup_only SCENARIO=path/to/scenario.yml

# Run with additional options
make run_advanced SCENARIO=path/to/scenario.yml OPTS="--verbose --skip-yaml-validation"
```

## Viewing Results

After running a scenario, you can view the results in multiple ways.

### Visualization Interface

AGIR Learning provides a visualization interface to view scenario run results using the Makefile:

```bash
make visualizer
```

This will launch a graphical interface where you can:
- Browse all scenarios and episodes
- View interaction content for each state
- Analyze the learner's progress

### Database Management

You can clear the database using the provided Makefile command:

```bash
# Clean database tables with confirmation prompt
make clear_db
```

### Database Queries

You can also get results directly through database queries:

```python
from agir_db.db.session import get_db
from agir_db.models.episode import Episode
from agir_db.models.step import Step

# Get database session
db = next(get_db())

# Query all episodes for a specific scenario
episodes = db.query(Episode).filter(Episode.scenario_id == scenario_id).all()

# Query all steps for a specific episode
steps = db.query(Step).filter(Step.episode_id == episode_id).all()

# Print step content
for step in steps:
    print(f"State: {step.state_id}, Content: {step.content}")
```

### Analyzing Learner Progress

To analyze a learner's progress across multiple episodes:

```python
from agir_db.models.user import User
from agir_db.models.memory import Memory

# Get the learner's memories
memories = db.query(Memory).filter(Memory.user_id == learner_id).all()

# View progress sorted by time
for memory in sorted(memories, key=lambda m: m.created_at):
    print(f"Time: {memory.created_at}, Learning: {memory.content}")
```

### Exporting Memories to a File

You can export the learner's memories to a file:

```python
import json
from datetime import datetime

# Get the learner's memories
memories = db.query(Memory).filter(Memory.user_id == learner_id).all()

# Convert to JSON format
memory_data = [
    {
        "id": memory.id,
        "content": memory.content,
        "created_at": memory.created_at.isoformat(),
        "episode_id": memory.episode_id
    } 
    for memory in memories
]

# Write to file
filename = f"learner_{learner_id}_memories_{datetime.now().strftime('%Y%m%d')}.json"
with open(filename, "w") as f:
    json.dump(memory_data, f, indent=2)

print(f"Memories exported to {filename}")
```

## Using Chat with a Learner

To engage in a chat with a specific agent:

```bash
make chat AGENT=agent_username
```

## Database Migration

Before running scenarios, ensure the database is properly migrated:

```bash
make migrate
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check if the `DATABASE_URL` in the `.env` file is correct
   - Ensure the database server is running
   - Run `make migrate` to ensure the database is up to date

2. **YAML Validation Failures**:
   - Check if the YAML format is correct
   - Ensure all required fields are defined

3. **LLM API Errors**:
   - Verify that the API keys in the `.env` file are correct
   - Check network connection
   - Check if API call limits have been reached

4. **Scenario Execution Errors**:
   - Check if state transitions form a valid path
   - Ensure role and state names are consistent throughout the YAML file

## Suggested Makefile Additions

The following commands could be added to the Makefile to support all operations mentioned in this document:

```makefile
# Add these to your Makefile

# Run scenario initialization only
run_init:
	python run.py $(SCENARIO) --mode init

# Run an existing scenario
run_existing:
	@if [ -z "$(SCENARIO_ID)" ]; then \
		echo "❌ Error: You must provide SCENARIO_ID. Usage: make run_existing SCENARIO_ID=123"; \
		exit 1; \
	fi
	python run.py --mode run --scenario-id=$(SCENARIO_ID)

# Setup scenario without executing
setup_only:
	python run.py $(SCENARIO) --setup-only

# Run with advanced options
run_advanced:
	python run.py $(SCENARIO) $(OPTS)

# Export memories for a learner
export_memories:
	@if [ -z "$(LEARNER_ID)" ]; then \
		echo "❌ Error: You must provide LEARNER_ID. Usage: make export_memories LEARNER_ID=123"; \
		exit 1; \
	fi
	python commands/export_memories.py $(LEARNER_ID)

# Clear database with confirmation skipped
clear_db_force:
	PYTHONPATH=$(shell pwd) python commands/clear_db.py --confirm
```
