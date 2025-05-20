EPISODES ?= 1
SCENARIO ?= scenarios/hello.yml
OPTS ?=

migrate:
	@python -m alembic -c "$$(python -c 'import agir_db; import os; print(os.path.join(agir_db.__path__[0], "alembic.ini"))')" upgrade head

visualizer:
	python -m src.visualization.run_visualizer

clear_db:
	PYTHONPATH=$(shell pwd) python commands/clear_db.py

learning:
	PYTHONPATH=$(shell pwd) python commands/run.py $(SCENARIO) --episodes=$(EPISODES)

chat:
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Error: You must provide AGENT. Usage: make chat_learn AGENT=alice_001"; \
		exit 1; \
	fi
	python -m commands.chat_learner_cli $(AGENT)

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