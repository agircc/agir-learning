EPISODES ?= 1
SCENARIO ?= scenarios/hello.yml

migrate:
	@python -m alembic -c "$$(python -c 'import agir_db; import os; print(os.path.join(agir_db.__path__[0], "alembic.ini"))')" upgrade head

run_visualizer:
	python -m src.visualization.run_visualizer

clear_db:
	python commands/clear_db.py

learning:
	python run.py $(SCENARIO) --episodes=$(EPISODES)