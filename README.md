# AGIR Learning: Agent-Guided Intelligent Reflection for Skill Development

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Conda](https://img.shields.io/badge/conda-environment-green.svg)](environment.yml)

</div>

AGIR Learning is a platform designed to accelerate skill development through structured interactions with AI agents in simulated environments. It creates safe, repeatable scenarios for practice, feedback, and reflection.

## 🚀 Key Features

- **Structured Learning Environments**: Define learning scenarios with YAML configuration
- **Role-Based AI Agents**: Simulate different participants with customizable LLM backends
- **Guided Reflection**: Help learners identify strengths and areas for improvement
- **Iterative Development**: Progress through increasingly complex scenarios
- **Multi-LLM Architecture**: Use different models for different roles (efficiency & cost control)
- **Memory System**: Store and retrieve learning insights across episodes

## 📋 Quick Start

### Prerequisites

- Python 3.12+
- Conda package manager
- PostgreSQL database
- API keys for LLM providers (OpenAI, Anthropic, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/agir-learning.git
cd agir-learning

# Create and activate conda environment
conda env create -f environment.yml
conda activate agir-learning

# Configure your environment
cp .env.example .env
# Edit .env with your database URL and API keys
```

### Basic Usage

```bash
# Ensure database is migrated
make migrate

# Run a sample scenario
make learning SCENARIO=scenarios/hello.yml

# Visualize results
make visualizer
```

## 📖 Documentation

### Core Concepts

- **Learner**: The primary user whose skills are being developed.
- **Scenario**: A structured sequence of interactions designed to teach specific skills.
- **Agents**: AI participants with different roles in the scenario.
- **Evolution**: The mechanism by which the learner's skills improve through guided practice.

### Detailed Documentation

- [Creating Scenarios](doc/create_scenario.md): How to define and configure learning scenarios
- [Scenario Construction Process](doc/construction.md): How scenarios are built in the system
- [Evolution Process](doc/evolution.md): How scenarios are executed and learning occurs
- [Installation Guide](doc/installation.md): Detailed installation instructions
- [Architecture Overview](doc/architecture.md): System design and components

## 🧩 Project Structure

```
├── commands/              # CLI utility commands
├── doc/                   # Documentation files
├── scenarios/             # Example scenario YAML files
├── src/                   # Source code
│   ├── chat/              # Chat functionality
│   ├── common/            # Shared utilities
│   ├── construction/      # Scenario construction
│   ├── evolution/         # Scenario execution/evolution
│   ├── llm/               # LLM provider integrations
│   └── visualization/     # Result visualization
├── tests/                 # Test suite
├── vector_stores/         # Vector databases for memory
├── Makefile               # Common commands
├── environment.yml        # Conda environment specification
└── run.py                 # Main execution script
```

## 🛠️ Development Tools

The project includes several useful Makefile commands to simplify common operations:

```bash
# Run database migrations
make migrate

# Launch the visualization interface
make visualizer

# Clear database tables
make clear_db

# Run a scenario
make learning SCENARIO=path/to/scenario.yml EPISODES=3

# Chat with an agent
make chat AGENT=agent_username

# Export learner memories
make export_memories LEARNER_ID=123
```

See the [full command reference](doc/commands.md) for more details.

## 🧪 Example Scenarios

The repository includes several example scenarios:

- `scenarios/hello.yml`: A simple introduction scenario
- `scenarios/medical_diagnosis.yml`: Medical diagnosis training
- `scenarios/programming_mentor.yml`: Code review and mentoring

Read the [scenario examples guide](doc/scenario_examples.md) to learn more about these examples.

## 🤝 Contributing

Contributions are welcome! See our [Contributing Guide](doc/contributing.md) for more details on how to get involved.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- This project uses [LangChain](https://github.com/langchain-ai/langchain) for LLM orchestration
- Vector storage powered by [FAISS](https://github.com/facebookresearch/faiss)