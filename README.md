# Agent Evolution System

A system for agent evolution through simulated experiences defined in YAML.

## Overview

This system allows users to evolve through simulated experiences provided by LLM-powered agents. The system:

1. Loads process definitions from YAML files
2. Creates or finds target users and agent users in the database
3. Simulates interactions between agents according to the process graph
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

### Running Evolution Process

```bash
# Using default OpenAI GPT-4 model
python run_evolution.py examples/doctor.yml

# Using Anthropic's Claude model
python run_evolution.py examples/doctor.yml --model anthropic

# Specify model name
python run_evolution.py examples/doctor.yml --model openai --model-name gpt-4-turbo

# Enable verbose logging
python run_evolution.py examples/doctor.yml -v
```

### Environment Variables

Set the following environment variables in a `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

## Process YAML Format

Process YAML files define the evolution experience:

```yaml
process:
  name: "Process Name"
  description: "Process Description"

  target_user:
    username: "target_username"
    first_name: "User's First Name"
    last_name: "User's Last Name"
    # Other user attributes
    evolution_objective: "Description of what the user should learn"

  nodes:
    - name: "Node Name"
      role: "role_id"
      description: "Node Description"
      assigned_to: "optional_username"  # If assigned to target user

  transitions:
    - from: "Node Name"
      to: "Another Node Name"
    # More transitions

  roles:
    - id: role_id
      name: "Role Name"
      description: "Role Description"

  evolution:
    method: "Evolution Method Name"
    description: "Description of how evolution works"
    knowledge_sources:
      - "Source 1"
      - "Source 2"
```

## Process Creation Flow

The system follows these steps when creating a process:

1. **Database Validation**
   - Check if required database tables exist
   - If tables don't exist, prompt user to run database migrations

2. **User Creation**
   - Read the YAML file and extract target user information
   - Check if the target user exists in the user table based on username
   - If not found, create a new user record

3. **Process Creation**
   - Check if a process with the given name and creator already exists
   - If not found, create a new process record

4. **Process Roles Creation**
   - For each role defined in the YAML, create a process role record
   - Store mapping between YAML role IDs and database role IDs

5. **Process Nodes Creation**
   - For each node defined in the YAML, create a process node record
   - Associate each node with its corresponding role using the role mapping
   - Store mapping between YAML node IDs and database node IDs

6. **Process Transitions Creation**
   - For each transition defined in the YAML, create a process transition record
   - Use node mappings to correctly link from_node_id and to_node_id

## Process Execution Flow

When executing a process, the system follows these steps:

1. **Process Instance Creation**
   - Create a process instance record linked to the process and target user
   - Set initial status to RUNNING
   - Store the full process configuration as JSON in the config field

2. **Process Instance Steps**
   - Start with the first node in the process
   - For each node:
     - Create a process instance step record linked to the appropriate node
     - Execute the node logic (agent interaction, etc.)
     - Update the step status upon completion
     - Determine the next node based on transitions

3. **Evolution Generation**
   - After completing all nodes or reaching a terminal node
   - Generate evolution insights based on the process history
   - Update the target user with new knowledge/skills

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
    ├── cli.py              # Command line interface
    ├── evolution.py        # Main evolution engine
    ├── db/                 # Database utilities
    │   └── __init__.py     # Database initialization
    ├── llms/               # LLM providers
    │   ├── __init__.py     # LLM module initialization
    │   ├── base.py         # Base LLM provider interface
    │   ├── openai.py       # OpenAI implementation
    │   └── anthropic.py    # Anthropic implementation
    ├── models/             # Data models
    │   ├── __init__.py     # Models initialization
    │   ├── agent.py        # Agent model
    │   ├── process.py      # Process model
    │   └── role.py         # Role model
    └── utils/              # Utility functions
        ├── __init__.py     # Utils initialization
        ├── database.py     # Database utility functions
        └── yaml_loader.py  # YAML loading utilities
```

## System Flow Diagram

```mermaid
graph TD
    A[User Input: YAML Process File] --> B[CLI Arguments Processing]
    B --> C{Check DB Tables}
    C -->|Tables Exist| D[ProcessManager: Create Process from YAML]
    C -->|Tables Don't Exist| C1[Error: Run Migrations]
    
    D --> D1[Create/Find Target User]
    D1 --> D2[Create/Find Process]
    D2 --> D3[Create Process Roles]
    D3 --> D4[Create Process Nodes]
    D4 --> D5[Create Process Transitions]
    D5 --> E[Initialize LLM Provider]
    
    E --> F[EvolutionEngine: Run Evolution with Process ID]
    F --> G[ProcessManager: Execute Process]
    G --> G1[Create Process Instance]
    G1 --> H[Process Nodes Sequentially]
    
    H --> I{Node Type?}
    I -->|Target User Node| J[Simulate Target User]
    I -->|Agent Node| K[Execute Agent Logic]
    
    J --> L[Generate Node Response]
    K --> L
    
    L --> M{More Nodes?}
    M -->|Yes| N[Advance Process to Next Node]
    N --> H
    M -->|No| O[Process Evolution]
    
    O --> P[Generate Reflections]
    P --> Q[Update User Knowledge]
    Q --> R[Mark Process Complete]
    
    subgraph "Database Interactions"
        DB1[(PostgreSQL DB)]
        D1 -.-> DB1
        D2 -.-> DB1
        D3 -.-> DB1
        D4 -.-> DB1
        D5 -.-> DB1
        G1 -.-> DB1
        L -.-> DB1
        N -.-> DB1
        Q -.-> DB1
        R -.-> DB1
    end
    
    subgraph "LLM Providers"
        LLM1[OpenAI Provider]
        LLM2[Anthropic Provider]
        E -.-> LLM1
        E -.-> LLM2
        J -.-> LLM1
        K -.-> LLM1
        P -.-> LLM1
    end
```

## Extension

### Adding New LLM Providers

1. Create a new provider in `src/llms/`
2. Implement the `BaseLLMProvider` interface
3. Add the provider to `src/llms/__init__.py`
4. Update the CLI in `src/cli.py` to support the new provider

### Creating Custom Processes

1. Create a new YAML file based on the examples
2. Define nodes, transitions, roles, and evolution method
3. Run the process using the CLI

## Development Notes

- This project uses the latest version of agir_db package
- All database operations are performed using agir_db models, not raw SQL
- All code comments are in English