# Command Reference

This document provides a comprehensive reference of all commands available in the AGIR Learning system, organized by function.

## Makefile Commands

AGIR Learning provides a set of Makefile commands to simplify common operations. These commands abstract away the complexity of the underlying Python scripts.

### Basic Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `make learning` | Run a scenario | `make learning SCENARIO=path/to/scenario.yml` |
| `make visualizer` | Launch the visualization interface | `make visualizer` |
| `make migrate` | Run database migrations | `make migrate` |
| `make clear_db` | Clear database tables (with confirmation) | `make clear_db` |
| `make chat` | Chat with an agent | `make chat AGENT=agent_username` |
| `make read_book` | Process a book and create memories for a user | `make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/BOOK_TITLE.txt"` |

### Advanced Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `make run_init` | Initialize a scenario without running it | `make run_init SCENARIO=path/to/scenario.yml` |
| `make run_existing` | Run an existing scenario by ID | `make run_existing SCENARIO_ID=123` |
| `make setup_only` | Set up a scenario without executing it | `make setup_only SCENARIO=path/to/scenario.yml` |
| `make run_advanced` | Run with advanced options | `make run_advanced SCENARIO=path/to/scenario.yml OPTS="--verbose --skip-yaml-validation"` |
| `make export_memories` | Export memories for a learner | `make export_memories LEARNER_ID=123` |
| `make clear_db_force` | Clear database tables without confirmation | `make clear_db_force` |

## Direct Python Commands

If you need more control than the Makefile provides, you can use the underlying Python commands directly.

### Main Execution Script

The primary script for running scenarios is `run.py`:

```bash
# Initialize and run a scenario (default behavior)
python run.py path/to/scenario.yml

# Initialize scenario only
python run.py path/to/scenario.yml --mode init

# Run existing scenario
python run.py path/to/scenario.yml --mode run --scenario-id 123

# Run multiple episodes
python run.py path/to/scenario.yml --episodes 3

# Advanced options
python run.py path/to/scenario.yml --verbose --skip-db-check --skip-yaml-validation
```

### Command-Line Options for run.py

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Enable verbose logging |
| `--skip-db-check` | Skip database check (not recommended) |
| `--skip-yaml-validation` | Skip YAML validation |
| `--skip-llm` | Skip LLM initialization for debugging |
| `--setup-only` | Only setup the scenario in the database without executing it |
| `--mode {init,run,all}` | Execution mode: init (only initialize), run (only run), all (both) |
| `--scenario-id` | Scenario ID for run mode (required when mode=run) |
| `--episodes`, `-e` | Number of episodes to run (default: 1) |
| `--no-color` | Disable colorized logging output |
| `--log-file` | Path to write logs to a file |

### Database Management

To clear the database tables:

```bash
# With confirmation prompt
python commands/clear_db.py

# Without confirmation prompt
python commands/clear_db.py --confirm

# With verbose logging
python commands/clear_db.py --verbose
```

### Memory Export

To export memories for a specific learner:

```bash
# Basic usage
python commands/export_memories.py learner_id

# With pretty-printing
python commands/export_memories.py learner_id --pretty

# With custom output path
python commands/export_memories.py learner_id --output path/to/output.json

# With verbose logging
python commands/export_memories.py learner_id --verbose
```

### Chat with Agent

To chat with a specific agent:

```bash
python -m commands.chat_learner_cli agent_username
```

### Visualization

To launch the visualization interface:

```bash
python -m src.visualization.run_visualizer
```

### Book Reading

To read a book and create memories for a user:

```bash
# Using Makefile (recommended)
make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"

# Using Python script directly
python commands/read_book.py alice_007 "scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"
```

The book reading process:
1. Divides the book into manageable chunks
2. Processes each chunk to extract knowledge using the user's LLM model
3. Creates a reflection for each chunk of the book
4. Generates a final reflection on the entire book
5. Creates a memory record indicating the user has read this specific book
6. All memories are associated with the user's ID and can be retrieved through the normal memory retrieval mechanisms

This feature is helpful for building an agent's knowledge base from text sources.

## Environment Variables

The following environment variables can be set in the `.env` file to configure the system:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL database connection URL | `postgresql://user:pass@localhost:5432/agir_learning` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-abcdefg123456789` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-api-abcdefg123` |
| `LOG_LEVEL` | Logging level | `INFO`, `DEBUG`, `WARNING`, etc. |
| `VECTOR_STORE_PATH` | Path to store vector databases | `./vector_stores` |

## Example Command Sequences

### Complete Workflow Example

```bash
# 1. Ensure database is migrated
make migrate

# 2. Clear any existing data (if needed)
make clear_db

# 3. Run a scenario with 3 episodes
make learning SCENARIO=scenarios/medical_diagnosis.yml EPISODES=3

# 4. Visualize the results
make visualizer

# 5. Export memories for a specific learner
make export_memories LEARNER_ID=123
```

### Development Workflow Example

```bash
# 1. Initialize a scenario without running it (for testing)
make run_init SCENARIO=scenarios/test_scenario.yml

# 2. Run with verbose output and skip validations
make run_advanced SCENARIO=scenarios/test_scenario.yml OPTS="--verbose --skip-yaml-validation"
```

### Book Reading Workflow Example

```bash
# 1. Ensure database is migrated
make migrate

# 2. Create a user (or use existing one)
# A user must exist with a valid LLM model configured

# 3. Process a book to create memories
make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"

# 4. Chat with the user to see their knowledge of the book
make chat AGENT=alice_007
```

## Troubleshooting Commands

If you encounter issues, these commands can help diagnose problems:

```bash
# Check if the database connection is working
python -c "from agir_db.db.session import get_db; next(get_db()); print('Database connection successful')"

# Check which tables exist in the database
python -c "from agir_db.db.session import get_db; import sqlalchemy as sa; print([t for t in sa.inspect(next(get_db()).bind).get_table_names()])"

# Test LLM API connection (replace with your API key)
OPENAI_API_KEY=your_key_here python -c "import openai; print(openai.models.list())"
``` 