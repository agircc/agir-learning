# AGIR Learning: Agent-Guided Intelligent Reflection for Skill Development

A system designed to improve learner skills through simulated experiences and guided interactions with AI agents in virtual scenarios.

## Overview

AGIR Learning is a platform that helps learners develop specific skills through structured interactions with AI agents in simulated environments. The system creates virtual scenarios where learners can practice skills, receive feedback, and reflect on their performance—all with the guidance of specialized AI agents.

The core purpose of AGIR Learning is to **accelerate skill development through simulated practice in a safe environment**. Whether learning medical diagnosis, negotiation tactics, or programming techniques, the system provides:

1. **Structured learning environments** defined as scenarios in YAML
2. **Role-based AI agents** that simulate different participants in the learning scenario
3. **Guided reflection** to help learners understand their strengths and areas for improvement
4. **Iterative skill development** through repeated practice with increasing complexity

### Key Concepts

- **Learner**: The primary user whose skills are being developed through the scenario. In the database, a learner is a record in the user table.
- **Scenario**: A structured sequence of interactions designed as a learning experience for specific skills.
- **Agents**: AI participants in the scenario represented by different roles (stored as users in the database).
- **Evolution**: The mechanism by which the learner's skills improve through experiences, feedback, and guided reflection.

## Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running Evolution Process

```bash
# Initialize scenario only
python run.py path/to/scenario.yml --mode init

# Run existing scenario
python run.py path/to/scenario.yml --mode run --scenario-id 123

# Initialize scenario and run (default behavior)
python run.py path/to/scenario.yml

# Or explicitly specify
python run.py path/to/scenario.yml --mode all
```

### Environment Variables

Set the following environment variables in a `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

## Scenario YAML Format

Scenario YAML files define the evolution experience:

```yaml
scenario:
  name: "Scenario Name"
  description: "Scenario Description"

  # The learner is the central user whose skills are being developed
  learner:
    username: "username"  # Username in the database
    first_name: "First Name"
    last_name: "Last Name"
    model: "gpt-4"  # LLM model to use for this learner
    # Other user attributes
    evolution_objective: "Description of what the learner should learn"

  # Roles represent different agents in the scenario
  roles:
    - name: "patient"
      model: "phi"  # Each role can use a different LLM model
      description: "Patient agent with medical history, symptoms."
    - name: "nurse"
      model: "phi"
      description: "Nurse agent for triage, registration, and examinations."

  # States are the steps in the scenario
  states:
    - name: "State Name"
      role: "role_name"  # Role this state belongs to
      description: "State Description"
      # If role is "learner", this state represents actions by the learner

  # Transitions define the flow between states
  transitions:
    - from: "First State Name"
      to: "Second State Name"
    # More transitions

  # Evolution defines how the learner improves
  evolution:
    method: "Evolution Method Name"
    description: "Description of how evolution works"
    knowledge_sources:
      - "Source 1"
      - "Source 2"
```

## Learner-Centric Architecture

This system is designed around the central concept of a **learner** - a user whose skills and knowledge evolve through simulated scenarios. Here's how it works:

1. **Learner Identification**: 
   - The system identifies the learner based on the YAML configuration
   - The learner is always a real user in the database
   - All interactions are designed to benefit this user's development

2. **Multi-Provider LLM Architecture**:
   - Each role in the scenario can be assigned a different LLM model
   - The learner can have their own designated model
   - This allows for efficient resource allocation (powerful models for complex tasks, simpler models for basic interactions)

3. **User Database Integration**:
   - All agents in the system, including the learner, are stored in the user table
   - This unified approach ensures consistent user handling and evolution tracking

## Scenario Creation Flow

The system follows these steps when creating a scenario:

1. **Database Validation**
   - Check if required database tables exist
   - If tables don't exist, prompt user to run database migrations

2. **Learner Creation**
   - Read the YAML file and extract learner information
   - Check if the learner exists in the user table based on username
   - If not found, create a new user record

3. **Scenario Creation**
   - Check if a scenario with the given name and creator already exists
   - If not found, create a new scenario record

4. **Agent Roles Creation**
   - For each role defined in the YAML, create an agent role record
   - Special handling for the "learner" role which references the main user

5. **States Creation**
   - For each state defined in the YAML, create a state record
   - Special handling for states with role="learner" - these represent learner actions

6. **State Transitions Creation**
   - For each transition defined in the YAML, create a state transition record
   - Transitions define the flow of the learning experience

## Episode Execution Flow

When executing a scenario, the system follows these steps:

1. **Episode Creation**
   - Create an episode record linked to the scenario and learner
   - Set initial status to RUNNING

2. **Episode Steps**
   - Start with the first state in the scenario
   - For each state:
     - Create a step record
     - Use the appropriate LLM model based on role or learner configuration
     - Generate responses and advance through the scenario

3. **Evolution Generation**
   - After completing all states
   - Generate evolution insights based on the episode history
   - Update the learner with new knowledge/skills
   - Store evolution data in the database for future reference

## Project Structure

```
Project Root/
├── run_evolution.py        # Main entry script
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (create this)
├── examples/               # Example YAML files directory
│   └── doctor.yml          # Doctor example
└── src/                    # Source code directory
    ├── __init__.py         # Module initialization
    ├── cli.py              # Command line interface and LLM provider management
    ├── evolution.py        # Main evolution engine
    ├── db/                 # Database utilities
    │   └── __init__.py     # Database initialization
    ├── llms/               # LLM providers
    │   ├── __init__.py     # LLM module initialization
    │   ├── base.py         # Base LLM provider interface
    │   ├── openai.py       # OpenAI implementation
    │   ├── anthropic.py    # Anthropic implementation
    │   └── ollama.py       # Ollama implementation
    ├── models/             # Data models
    │   ├── __init__.py     # Models initialization
    │   ├── agent.py        # Agent model
    │   ├── scenario.py     # Scenario model
    │   └── role.py         # Role model
    ├── episode_manager.py  # Episode management and execution
    └── utils/              # Utility functions
        ├── __init__.py     # Utils initialization
        ├── database.py     # Database utility functions
        └── yaml_loader.py  # YAML loading utilities
```

## Extension

### Adding New LLM Providers

1. Create a new provider in `src/llms/`
2. Implement the `BaseLLMProvider` interface
3. Add the provider to `src/llms/__init__.py`
4. Update the `LLMProviderManager` in `src/cli.py` to support the new provider

### Creating Custom Scenarios

1. Create a new YAML file based on the examples
2. Define the learner, states, transitions, roles, and evolution method
3. Run the scenario using the CLI

## Development Notes

- This project uses the latest version of agir_db package
- All database operations are performed using agir_db models, not raw SQL
- All code comments are in English