EPISODES ?= 1
SCENARIO ?= scenarios/hello.yml
OPTS ?=

migrate:
	@python -m alembic -c "$$(python -c 'import agir_db; import os; print(os.path.join(agir_db.__path__[0], "alembic.ini"))')" upgrade head

visualizer:
	python -m src.visualization.run_visualizer

clear_db:
	PYTHONPATH=$(shell pwd) python scripts/clear_db.py

learning:
	PYTHONPATH=$(shell pwd) python scripts/run.py $(SCENARIO) --episodes=$(EPISODES)

chat:
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Error: You must provide AGENT. Usage: make chat_learn AGENT=alice_001"; \
		exit 1; \
	fi
	python -m scripts.chat_learner_cli $(AGENT)

# Read a book and create memories for a user
read_book:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: You must provide USERNAME. Usage: make read_book USERNAME=alice_007 BOOK_PATH=scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"; \
		exit 1; \
	fi
	@if [ -z "$(BOOK_PATH)" ]; then \
		echo "❌ Error: You must provide BOOK_PATH. Usage: make read_book USERNAME=alice_007 BOOK_PATH=scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"; \
		exit 1; \
	fi
	PYTHONPATH=$(shell pwd) python scripts/read_book.py $(USERNAME) "$(BOOK_PATH)" $(if $(START_CHUNK),--start-chunk=$(START_CHUNK),)

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
	python scripts/export_memories.py $(LEARNER_ID)

# Clear database with confirmation skipped
clear_db_force:
	PYTHONPATH=$(shell pwd) python scripts/clear_db.py --confirm

# Add negative memories for all users
add_negative_memories:
	PYTHONPATH=$(shell pwd) python scripts/add_negative_memory.py

# Add negative memories with custom options
add_negative_memories_custom:
	@if [ -z "$(MODEL)" ]; then \
		MODEL="gpt-4.1-nano"; \
	fi
	PYTHONPATH=$(shell pwd) python scripts/add_negative_memory.py --model=$(MODEL) $(if $(LIMIT),--limit=$(LIMIT),) $(if $(FORCE),--force,) $(if $(DEBUG),--debug,)

# Add negative memories for limited users (testing)
add_negative_memories_test:
	PYTHONPATH=$(shell pwd) python scripts/add_negative_memory.py --limit=3 --debug

# Add negative memories with force mode (overwrite existing)
add_negative_memories_force:
	PYTHONPATH=$(shell pwd) python scripts/add_negative_memory.py --force

# Start the API server
api:
	python -m api.run

# Start the Next.js development server
web:
	cd web && npm run dev

# Start both API and web servers (API in background)
start:
	python -m api.run & \
	cd web && npm run dev