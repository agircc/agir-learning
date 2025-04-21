# AGIR Learning

A system for evolving LLM-powered agents through simulated experiences based on process YAML definitions.

## Overview

AGIR Learning allows users to evolve through simulated experiences provided by LLM-powered agents. The system:

1. Loads process definitions from YAML files
2. Creates or finds target users and agent users in the database
3. Simulates interactions between agents following the process graph
4. Generates reflections and evolution insights for the target user

## Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running an Evolution Process

```bash
# Using OpenAI with default GPT-4 model
python run_evolution.py examples/doctor.yml

# Using Anthropic with Claude
python run_evolution.py examples/doctor.yml --model anthropic

# Specifying a model name
python run_evolution.py examples/doctor.yml --model openai --model-name gpt-4-turbo

# Enable verbose logging
python run_evolution.py examples/doctor.yml -v
```

### Environment Variables

Set the following environment variables in `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Process YAML Format

Process YAML files define the evolution experience:

```yaml
process:
  name: "Process Name"
  description: "Process Description"

  target_user:
    username: "username_of_target_user"
    first_name: "User's First Name"
    last_name: "User's Last Name"
    # Other user attributes
    evolution_objective: "Description of what the user should learn"

  nodes:
    - id: node1
      name: "Node Name"
      role: "role_id"
      description: "Node description"
      assigned_to: "optional_username"  # If assigned to target user

  transitions:
    - from: node1
      to: node2
    # More transitions

  roles:
    - id: role_id
      name: "Role Name"
      description: "Role description"

  evolution:
    method: "Evolution Method Name"
    description: "Description of how evolution works"
    knowledge_sources:
      - "Source 1"
      - "Source 2"
```

## Project Structure

```
agir_learning/
├── __init__.py             # Package initialization
├── cli.py                  # Command-line interface
├── evolution.py            # Main evolution engine
├── db/                     # Database utilities
│   └── __init__.py         # Database initialization
├── llms/                   # LLM providers
│   ├── __init__.py         # LLM module initialization
│   ├── base.py             # Base LLM provider interface
│   ├── openai.py           # OpenAI implementation
│   └── anthropic.py        # Anthropic implementation
├── models/                 # Data models
│   ├── __init__.py         # Models initialization
│   ├── agent.py            # Agent model
│   ├── process.py          # Process models
│   └── role.py             # Role model
└── utils/                  # Utility functions
    ├── __init__.py         # Utils initialization
    ├── database.py         # Database utility functions
    └── yaml_loader.py      # YAML loading utilities
```

## Extending

### Adding a New LLM Provider

1. Create a new provider in `agir_learning/llms/`
2. Implement the `BaseLLMProvider` interface
3. Add the provider to `agir_learning/llms/__init__.py`
4. Update the CLI in `agir_learning/cli.py` to support the new provider

### Creating a Custom Process

1. Create a new YAML file based on the examples
2. Define nodes, transitions, roles, and evolution method
3. Run the process using the CLI