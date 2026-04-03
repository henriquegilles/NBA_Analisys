---
name: verify
description: Run dbt tests to validate all model constraints (unique, not_null). Use after editing SQL models or seeds to catch data quality issues.
---

Run dbt tests and report results clearly:

```bash
source .venv/bin/activate && dbt test --profiles-dir .dbt
```

For each failure:
- Name the model and column that failed
- State what constraint was violated (e.g., "column player_name has duplicate values")
- Suggest the likely cause (e.g., BBR inserts repeated header rows that weren't filtered)
- Explain what to do to fix it

If all tests pass, confirm that and summarize how many tests ran.
