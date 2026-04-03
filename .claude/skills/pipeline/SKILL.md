---
name: pipeline
description: Run the full dbt pipeline in order: seed CSVs, run all models, then test. Use this after making changes to seeds or models.
---

Run the full dbt pipeline in this exact order. Explain each step to the user as it runs.

The virtual environment is at `.venv/`. dbt needs `--profiles-dir .dbt` because the connection config is not in the default location.

1. **Activate venv and seed** — Load the CSV files from `basket_dbt/seeds/` into PostgreSQL:
   ```bash
   source .venv/bin/activate && dbt seed --profiles-dir .dbt
   ```
   If this fails with CSV errors, suggest running `python fix_csv.py basket_dbt/seeds/players.csv basket_dbt/seeds/players_stats.csv` first.
   If this fails with "connection refused", PostgreSQL is not running — tell the user to run `sudo service postgresql start`.

2. **Run models** — Execute all enabled SQL models (staging layer):
   ```bash
   dbt run --profiles-dir .dbt
   ```
   Report which models ran and whether any failed.

3. **Test** — Validate column constraints (unique, not_null) defined in YAML files:
   ```bash
   dbt test --profiles-dir .dbt
   ```
   If tests fail, explain which column failed, what the constraint was, and what likely caused it.

After all three steps complete, summarize: how many models ran, how many tests passed/failed, and any next steps.
