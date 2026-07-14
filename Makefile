.PHONY: setup db-up demo pipeline test dashboard dagster smoke lint

## setup: install Python deps (uv) and dbt packages
setup:
	uv sync
	cd dbt && uv run dbt deps

## db-up: start PostgreSQL via Docker
db-up:
	docker compose up -d postgres

## demo: load the small sample dataset and run the full dbt pipeline
demo:
	bash scripts/bootstrap_demo.sh

## pipeline: dbt seed + run + test against local PostgreSQL
pipeline:
	cd dbt && uv run dbt seed && uv run dbt run && uv run dbt test

## test: dbt tests only
test:
	cd dbt && uv run dbt test

## dashboard: launch the Streamlit app (http://localhost:8501)
dashboard:
	uv run streamlit run dashboard/app.py

## dagster: compile the dbt manifest and start the Dagster UI (http://localhost:3000)
dagster:
	cd dbt && uv run dbt compile
	uv run dagster dev -f orchestration/definitions.py

## smoke: headless smoke test of every dashboard tab
smoke:
	uv run python dashboard/test_app_smoke.py

## lint: ruff over the Python code
lint:
	uv run ruff check src orchestration dashboard ci
