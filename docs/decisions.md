# Engineering Decisions & Troubleshooting Runbook — NBA Analytics Pipeline

> Log of the main problems hit while building and operating the pipeline.
> Serves as a runbook for future troubleshooting and as a record of design decisions.
> Entry numbers (`#N`) and design-decision IDs (`D-NN`) are referenced from other docs — do not renumber.

---

## 1. Cloudflare blocking the BBR scraper

**Symptom:**
```
Page title: <title>Um momento…</title>
HTML length: 31798
```
The scraper returned a Cloudflare challenge page (~31 KB) instead of the data page.

**Cause:**
Basketball Reference detected the headless browser and served a bot challenge (CAPTCHA/WAF).
The behavior is intermittent — it depends on time of day, request frequency, and the headless
Chrome signature Cloudflare fingerprints.

**Temporary workaround applied:**
- Synthetic `bbr_id` generation following the BBR convention (`lastname[:5] + firstname[:2] + counter`),
  mapped per unique player name so traded players (multiple rows) stay consistent.
- `bbr_id` and `season` columns added directly to the existing `players.csv` via a Python script.

**Definitive fix (once the scraper works again):**
```bash
cd src/scraping && uv run python players.py
# Replaces the synthetic IDs with the real BBR ones. Then, from dbt/:
uv run dbt seed --full-refresh --select players
uv run dbt run
```

**Future prevention** — add to `common/browser.py`:
```python
page_title = BeautifulSoup(driver.page_source, "lxml").title
if page_title and "momento" in page_title.text.lower():
    raise CloudflareBlockedError("BBR retornou challenge page — tente novamente mais tarde.")
```

---

## 2. PostgreSQL inferring `integer` for columns of placeholder CSVs

**Symptom:**
```
Database Error: function pg_catalog.btrim(integer) does not exist
HINT: No function matches the given name and argument types.
```

**Cause:**
Placeholder CSVs created for missing seeds had only the header row (no data). dbt seed hands
that to PostgreSQL, which — with no values to look at — defaults every column to `integer`.
When the staging model runs `trim("Player")`, PostgreSQL can't find `btrim(integer)`.

**Fix applied** — two fronts at once:
1. Added a dummy row to each placeholder CSV with string values in the key columns, so
   PostgreSQL infers `text` correctly.
2. Added `column_types` in the seeds schema file to force the type on critical columns:
```yaml
config:
  column_types:
    Player: varchar
    Tm: varchar
```

**Why isn't the dummy row enough?**
Columns that are NULL in every row (e.g. `college` in the draft seed) can still be inferred as
integer. `column_types` in the schema file is the definitive, content-independent fix.

---

## 3. Stale schema blocks `dbt seed` without `--full-refresh`

**Symptom:**
```
Database Error: column "bbr_id" of relation "players" does not exist
```

**Cause:**
`analytics_raw.players` already existed in PostgreSQL with the old schema (no `bbr_id`, no
`season`). Plain `dbt seed` uses `INSERT` and assumes the table schema matches the CSV.
When the CSV has new columns, the INSERT fails.

**Fix applied** (from `dbt/`):
```bash
uv run dbt seed --full-refresh
```
`--full-refresh` does DROP + CREATE before the INSERT, so the schema is rebuilt from the
current CSV.

**Rule of thumb** — always use `--full-refresh` when:
- Adding or removing columns from a seed CSV
- Changing a column's type
- Right after installing `dbt_utils` for the first time (project change that invalidates the partial parser)

---

## 4. `dbt_utils` not installed — pipeline didn't compile

**Symptom:**
```
Compilation Error
  dbt found 1 package(s) specified in packages.yml,
  but only 0 package(s) installed in dbt_packages.
  Run "dbt deps" to install package dependencies.
```

**Cause:**
`packages.yml` declared the `dbt_utils` dependency, but `dbt deps` had never been run — the
packages were not in `dbt_packages/`.

**Fix applied:**
```bash
uv run dbt deps
```

**Future prevention:**
Run `dbt deps` once after any change to `packages.yml`. It is a mandatory initial-setup step
(documented in the README).

---

## 5. Team abbreviations diverging between BBR and `team_info.csv`

**Symptom:**
```
Failure in test relationships_dim_player_current_team_abbr__team_abbr__ref_dim_team_
  Got 59 results, configured to fail if != 0
```

**Cause:**
BBR uses different abbreviations from other sources for three teams:

| Team | BBR (scrapers) | team_info.csv (old) |
|---|---|---|
| Brooklyn Nets | `BRK` | `BKN` |
| Charlotte Hornets | `CHO` | `CHA` |
| Phoenix Suns | `PHO` | `PHX` |

`dim_player.current_team_abbr` came from BBR (e.g. `CHO`) while `dim_team.team_abbr` came from
`team_info.csv` (e.g. `CHA`). The FK test caught 59 players with no matching team.

**Fix applied** — updated `dbt/seeds/team_info.csv` to use the BBR abbreviations (the project's
source of truth):
```
BRK,Brooklyn Nets,...
CHO,Charlotte Hornets,...
PHO,Phoenix Suns,...
```

**Rule of thumb:**
BBR is the source of truth for team abbreviations in this project. Any static reference
(`team_info.csv`) must use BBR abbreviations to keep JOINs consistent.

---

## 6. Synthetic `bbr_id` colliding for players with similar names

**Symptom:**
```
Failure in test unique_dim_player_bbr_id — Got 12 results
Failure in test unique_dim_player_player_key — Got 12 results
```

**Cause:**
The first version of the synthetic `bbr_id` generator created IDs per CSV **row**, not per
**unique player**. Traded players (e.g. Luka Dončić with `2TM`, `DAL` and `LAL` rows) got a
different ID per occurrence. Also, players with very similar names (e.g. "Jordan Johnson" and
"Jordan Jones") produced the same base ID `johnjo`.

**Fix applied:**
1. Map by unique name before applying to the DataFrame:
   ```python
   unique_names = players["Player"].unique().tolist()
   id_map = make_bbr_id_map(unique_names)
   players["bbr_id"] = players["Player"].map(id_map)
   ```
2. Incremental counter per base to guarantee uniqueness:
   ```python
   base = (last[:5] + first[:2]).ljust(7, "0")[:7]
   counts[base] += 1
   mapping[name] = f"{base}{counts[base]:02d}"
   ```

**Important note:**
Synthetic `bbr_id`s do **not** match BBR's real ones. When the scraper works again, the real
IDs will differ, producing "new" surrogate keys. Migration plan:
`dbt seed --full-refresh --select players && dbt run --full-refresh`.

---

## 7. YAML validation broken by unquoted `:` inside parentheses

**Symptom:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
  in "_marts__models.yml", line 299, column 54
```

**Cause:**
Unquoted YAML descriptions containing `(ex: value)` are parsed as a mapping. The pattern
`(ex: 32.23)` breaks the parse because `: ` inside an unquoted string signals a new map key.

**Fix applied** — wrap such descriptions in double quotes:
```yaml
# BREAKS:
description: Minutos jogados como decimal (ex: 32.23)

# CORRECT:
description: "Minutos jogados como decimal (ex: 32.23)"
```

**Future prevention:**
Any YAML string containing `: ` (colon + space) must be quoted.

---

## 8. Draft placeholder with NULL `draft_year` and `pick`

**Symptom:**
```
Failure in test not_null_fct_draft_class_draft_year — Got 1 result
Failure in test not_null_fct_draft_class_pick — Got 1 result
```

**Cause:**
The dummy row in `draft.csv` had NULL `draft_year` and `pick` (to avoid faking data). The
staging model filtered only `player_name != ''`, not `draft_year IS NULL`.

**Fix applied** — defensive filter in `stg_bbr__draft.sql`:
```sql
where trim("player_name") != ''
  and "player_name" is not null
  and "draft_year" is not null  -- ← added
  and "pick" is not null        -- ← added
```
This improves quality regardless of the placeholder — incomplete BBR rows (draft entries
missing pick number or year) can never reach the marts.

---

## 9. `dbt run` doesn't recreate tables on schema change — use `--full-refresh`

**Symptom:**
SQL changes to a `materialized: view` model show up on the next `dbt run`. Schema changes to
`materialized: table` models require `--full-refresh` for the new columns to appear.

**Cause:**
`materialized: table` uses `CREATE TABLE IF NOT EXISTS` + `INSERT`. If a column doesn't exist
in the physical table, the INSERT fails. Views are always rebuilt with `CREATE OR REPLACE VIEW`.

**Fix applied** — use `--full-refresh` after structural changes to marts:
```bash
uv run dbt run --full-refresh --select dim_player dim_team
```

---

## 10. Cloudflare bypassed with `selenium-stealth`

**Symptom:**
Every scraper returned `Title: Um momento…` (Cloudflare challenge page), even with standard
headless Selenium.

**Cause:**
Cloudflare detects headless Chrome via JavaScript properties like `navigator.webdriver = true`,
missing plugins, and GPU fingerprint. Vanilla Selenium hides none of these signatures.

**Fix applied** — installed `selenium-stealth` and wired it into `common/browser.py`:
```python
from selenium_stealth import stealth
stealth(driver, languages=["en-US","en"], vendor="Google Inc.",
        platform="Win32", webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine", fix_hairline=True)
```
Also added `--disable-blink-features=AutomationControlled` and removed the
`enable-automation` / `useAutomationExtension` options to reinforce the camouflage.

**Result:** BBR served real pages to every scraper after the change.

---

## 11. BBR renamed HTML table IDs — scrapers broke

**Symptom:**
```
ValueError: Table #contracts not found in page.
ValueError: Table #advanced_stats not found in page.
ValueError: Table #pgl_basic not found in page.
```

**Cause:**
Basketball Reference renamed several HTML table IDs between site versions:

| Scraper | Old ID | New ID |
|---|---|---|
| `contracts.py` | `contracts` | `player-contracts` |
| `advanced_stats.py` (regular) | `advanced_stats` | `advanced` |
| `advanced_stats.py` (playoffs) | `advanced_stats` | `advanced_stats` ✓ (unchanged) |
| `player_gamelogs.py` | `pgl_basic` | `player_game_log_reg` |

**Fix applied:**
- `contracts.py`: `get_table(soup, "player-contracts")`
- `advanced_stats.py`: dict `TABLE_IDS = {"regular": "advanced", "playoffs": "advanced_stats"}`
- `player_gamelogs.py`: `TABLE_ID = "player_game_log_reg"`

**Future prevention** — on `ValueError: Table #X not found`, inspect the page with:
```python
tables = soup.find_all("table")
print([t.get("id") for t in tables])
```

---

## 12. `data-stat="player"` renamed to `data-stat="name_display"` on BBR

**Symptom:**
```
Unique players com bbr_id: 0
```
`players.py` produced 733 rows but every `bbr_id` was NaN.

**Cause:**
`_extract_bbr_ids()` looked for cells with `data-stat="player"` to read the `data-append-csv`
attribute (which holds the real `bbr_id`). BBR renamed the attribute to
`data-stat="name_display"`.

**Fix applied:**
```python
# Before:
for td in table.find_all("td", {"data-stat": "player"}):
# After:
for td in table.find_all("td", {"data-stat": "name_display"}):
```

**Future prevention** — if every `bbr_id` is NaN after scraping, check with:
```python
row = table.find("tbody").find("tr")
for td in row.find_all("td")[:5]:
    print(td.get("data-stat"), td.get("data-append-csv"))
```

---

## 13. Gamelog table columns renamed on BBR

**Symptom:**
All 582 players returned "no data" in `player_gamelogs.py`.

**Cause:**
Besides the table ID (`pgl_basic` → `player_game_log_reg`), columns were renamed:

| Field | Old name | New name |
|---|---|---|
| Player's team | `Tm` | `Team` |
| Game date | `Date` | `Date` (same) |
| Result | (derived) | `Result` |
| Career game number | (didn't exist) | `Gcar` |
| Team game number | `G` | `Gtm` |

**Fix applied:**
Updated the `RENAME` dict in `player_gamelogs.py` to map the new names. Added `"Gcar"` and
`"Gtm"` to the drop list.

---

## 14. Chrome crashed mid-scrape of gamelogs — data lost

**Symptom:**
```
selenium.common.exceptions.WebDriverException: Message: tab crashed
  (Session info: chrome=147.0.7727.55)
```
The scraper failed at player 469/582 after ~30 minutes. Because data was accumulated in memory
(`frames = []`) and written only at the end, all 468 already-processed players were lost.

**Cause:**
Long-lived Chrome sessions accumulate memory. With 582 pages and a 3 s sleep per page
(~30 minutes), the Chrome process hit the WSL memory limit.

**Fix applied** — `player_gamelogs.py` refactored with three mechanisms:
1. **Incremental writes** — each player is appended to the CSV as soon as processed
   (`append` mode), eliminating data loss on crash.
2. **Automatic resume** — on restart, reads the `bbr_id`s already in the CSV and skips them.
3. **Periodic driver restart** — every 150 players, Chrome is shut down and relaunched to free
   memory.

**Future prevention:**
If `player_gamelogs.py` dies mid-run, just run it again — it resumes automatically.

---

## 15. CSV corrupted by column mismatch between placeholder and real data

**Symptom:**
```
pandas.errors.ParserError: Error tokenizing data. C error: Expected 31 fields in line 3, saw 35
```
The gamelog scraper failed on resume — `pd.read_csv` of the existing CSV threw a parse error.

**Cause:**
`dbt/seeds/player_gamelogs.csv` was originally a placeholder with 31 columns. When the
incremental-save scraper ran the first time it used `mode="a", header=False` — but the real BBR
data has 35 columns (`2P`, `2PA`, `2P%`, `eFG%` extra). The file ended up with a 31-column
header and 35-value rows: unreadable by any standard `pd.read_csv`.

**Fix applied:**
1. Deleted the corrupted CSV: `rm dbt/seeds/player_gamelogs.csv`
2. Updated `_already_scraped_ids()` to use `on_bad_lines="skip"` and filter the `_placeholder`
   sentinel from the returned IDs.
3. The scraper recreated the CSV with the correct 35-column header on first write.

**Future prevention:**
Fixed-column placeholders are fragile — when the scraper schema changes, the placeholder must
be regenerated. Alternatively, delete the placeholder before the first real-data run so the CSV
is created with the current schema.

---

## 16. Column misalignment in the gamelog CSV (rows missing `three_p_pct` or `ft_pct`)

**Symptom:**
```
column "season" is null for 1,047 rows in fct_player_game_log
The bbr_id value showed up in the minutes_decimal column (e.g. "durenja01")
```

**Cause:**
The scraper appends incrementally with `header=False` — rows are written by position, not by
column name. Players with 0 three-point attempts don't have the `three_p_pct` column in the BBR
table, so their DataFrame has 34 columns instead of 35. Appended positionally to the 35-column
CSV, everything from `three_p_pct` onward shifted one position left. A trailing comma masked
the problem by making the row look complete to pandas.

24 additional players were also missing `ft_pct` (0/0 free throws), causing a 2-position shift.

**Fix applied** — post-hoc Python repair script:
1. Identified affected rows via `season IS NULL` (the season value was shifted past the last column).
2. For the 1,023 rows missing `three_p_pct`: inserted `None` at position 12, shifting the rest right.
3. For the 24 rows missing both `three_p_pct` AND `ft_pct`: second `None` insertion at position 18.
4. CSV re-saved with 26,611 rows, all correctly aligned.

**Future prevention:**
Add `df = df.reindex(columns=EXPECTED_COLUMNS)` before `_append_to_csv()` in the scraper, so
DataFrames with missing columns are padded with `NaN` instead of shifting.

---

## 17. BBR changed the `game_result` format — point_diff parse broke

**Symptom:**
```
invalid input syntax for type integer: "109-119"
```
The `dim_game` model failed converting point_diff.

**Cause:**
BBR changed the `game_result` column format from `"W (+12)"` / `"L (-5)"` (margin in
parentheses) to `"W, 128-110"` / `"L, 109-119"` (full score). The old regex extracted digits
only, yielding `"109-119"` — not directly castable to integer.

**Fix applied** — dual-format handler in `stg_bbr__player_gamelogs.sql`:
```sql
case
    when trim("game_result") ~ '\([+-]?\d+\)' then
        (regexp_match(trim("game_result"), '\(([+-]?\d+)\)'))[1]::integer
    when trim("game_result") ~ '\d+-\d+' then
        (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[1]::integer
        - (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[2]::integer
    else null
end as point_diff
```

---

## 18. BBR uses `*` for starters in `games_started` — integer cast failed

**Symptom:**
```
invalid input syntax for integer: "*"
```

**Cause:**
BBR marks starters with `*` in the `GS` (games_started) column. The expression
`nullif(trim(...), '')::integer` doesn't handle the `*` character.

**Fix applied:**
```sql
case when trim("games_started"::text) = '*' then 1 else 0 end as games_started
```

---

## 19. Case-sensitive column names in PostgreSQL — stats columns not found

**Symptom:**
```
column "ft" does not exist
column "orb" does not exist
```

**Cause:**
dbt seed preserves the exact case of CSV headers. The columns `FT`, `FTA`, `ORB`, `DRB`, `TRB`,
`AST`, `STL`, `BLK`, `TOV`, `PF`, `PTS` land uppercase in the database. The staging model
referenced `"ft"`, `"orb"` etc. in lowercase.

**Fix applied:**
Updated `stg_bbr__player_gamelogs.sql` to use the uppercase references:
`"FT"`, `"FTA"`, `"ORB"`, `"DRB"`, `"TRB"`, `"AST"`, `"STL"`, `"BLK"`, `"TOV"`, `"PF"`, `"PTS"`.

---

## 20. Non-numeric values in stats columns — suspended players

**Symptom:**
```
invalid input syntax for type numeric: "Suspended"
```

**Cause:**
When a player is suspended, BBR fills every stat column (FG, FGA, PTS, etc.) with the string
`"Suspended"` instead of numbers. `nullif(trim(...), '')::numeric` handles only empty strings.

**Fix applied** — replaced `nullif(trim(...), '')::numeric` with a regex-guarded CASE on every
stat column in `stg_bbr__player_gamelogs.sql`:
```sql
(case when trim("PTS"::text) ~ '^-?[0-9]+\.?[0-9]*$' then trim("PTS"::text) end)::numeric(5,1)
```
Any non-numeric value (Suspended, Inactive, Did Not Play, etc.) becomes NULL.

---

## 21. `generate_id` collisions — duplicate surrogate key in `fct_player_game_log`

**Symptom:**
```
Failure in test unique_fct_player_game_log_game_player_key — Got 6 results
```
6 distinct `(bbr_id, game_date)` pairs produced the same 8-digit hash.

**Cause:**
The `generate_id` macro used `hashtext()` (32-bit) modulo 90M → a domain of only 90 million
values. With 26,611 rows, the birthday paradox predicts ~4 expected collisions
(n²/2m = 26611²/180M ≈ 3.94). The 6 observed are consistent with that.

**Fix applied:**
`generate_id` refactored to delegate to `dbt_utils.generate_surrogate_key`, which uses MD5 and
returns a 32-char varchar. Domain of 2^128 values — collisions are practically impossible at
this project's volumes. All models' surrogate keys changed from `integer` to `varchar`;
contracts updated in `_marts__models.yml`.

---

## 22. CI failing after switching `generate_id` to `dbt_utils`

**Symptom:**
```
Run failed: dbt Docs - master (9502b5a)
```
The GitHub Actions workflow failed right after the commit migrating `generate_id` to
`dbt_utils.generate_surrogate_key`.

**Cause:**
`dbt_packages/` is gitignored — the directory isn't in the repo. In a clean CI checkout,
`dbt_utils` doesn't exist until `dbt deps` runs. The `ci.yml` and `docs.yml` workflows didn't
have that step, so any `dbt_utils` macro failed compilation with a macro-not-found error.

**Fix applied** — added a `dbt deps` step in both workflows, before any dbt command that uses
packages:
```yaml
- name: dbt deps
  run: uv run dbt deps
```

**General rule:**
Whenever a new package is added to `packages.yml`, check that the CI workflows run `dbt deps`.
Without it, CI passes locally (where `dbt_packages/` already exists) but fails on the GitHub
runner.

---

## 23. Postgres won't start via `sudo service postgresql start` — this machine uses Docker

**Symptom:**
`dbt debug` / any dbt command fails with `connection to server at "localhost" (127.0.0.1),
port 5432 failed: Connection refused`. `sudo service postgresql start` asks for a password and,
even then, there is no service: no `/etc/init.d/postgresql`, `psql` not on PATH, no cluster
(`pg_lsclusters` missing).

**Cause:**
Postgres is **not installed locally** on this WSL. The project runs the database via **Docker**
(`docker-compose.yml`, image `postgres:17-alpine`, container `nba_postgres`).

**Fix:**
```bash
docker compose up -d postgres
```
If you see *"The command 'docker' could not be found in this WSL 2 distro"*, the binary exists
(`/mnt/c/Program Files/Docker/.../docker`) but **Docker Desktop's WSL Integration is off** for
this distro. Enable it: Docker Desktop → Settings → Resources → WSL Integration → enable the
distro → Apply & Restart. Then `docker compose up -d postgres`.

**Note for agents:** starting the database requires manual user action (sudo password or
enabling Docker Desktop integration) — it cannot be automated from a session. Ask the user to
run `docker compose up -d postgres`.

---

## 24. `dbt` on PATH was the wrong binary (dbt-fusion, no postgres adapter)

**Symptom:**
`dbt parse` / `dbt run` fails with
`[InvalidConfig (dbt1005)]: The 'postgres' adapter is not yet supported by dbt Fusion.
Supported adapters: snowflake, bigquery, databricks, redshift`. Looks like broken config, but
`profiles.yml` is fine.

**Cause:**
Two `dbt` installs coexisted on this machine:
- `~/.local/bin/dbt` → **dbt-fusion 2.0** (Rust rewrite; does **not** support postgres yet).
- the project environment → **dbt-core 1.9.x + postgres adapter** (the right one).

Without the project environment active, `~/.local/bin` wins on PATH and `dbt` resolves to
fusion, which rejects the postgres adapter. Every new shell (including each agent tool call)
starts without the environment activated.

**Fix:**
Always invoke dbt through the project environment — with uv this is simply:
```bash
cd dbt && uv run dbt parse     # dbt-core with the postgres adapter registered
```
To confirm which one is active: `uv run dbt --version` must say `Core: installed 1.9.x` and
`Registered adapter: postgres`. If it says `dbt-fusion`, it's the wrong binary (bare `dbt`
from PATH).

**Note for agents:** never call bare `dbt`/`python` — always `uv run dbt` / `uv run python` so
the project-pinned versions resolve.

---

## 25. BBR changed the draft table's 2-level header — `read_html`+flatten broke (D-30)

**Symptom:**
Re-scraping the draft (`draft.py`) to capture `bbr_id` produced wrong columns:
`Round 1_Player`, `Round 1_College`, `Shooting_FG%`, `Advanced_WS` — and **no `player_name` or
`bbr_id`**. Since the slug-capture block was guarded by `if "player_name" in df.columns`, it
simply never ran.

**Cause:**
BBR changed the two-layer header labels of the draft's `#stats` table. `pd.read_html` +
`_flatten_columns` built names as `<group>_<column>`, and the `RENAME` map expected the old
groups (`Totals_FG%`, `Per Game_PTS`, `WS`). With the new groups (`Round 1`, `Shooting`,
`Advanced`) nothing matched — the "Player" column became `Round 1_Player`. Same failure class
as #11/#12 (BBR periodically renames HTML).

**Fix:**
Dropped `read_html`+flatten and parse the table by **`data-stat`** (as `college.py` already
does) — stable, SQL-safe names, immune to superheader changes, and the `player` cell's
`<a href>` yields the `bbr_id` directly. Current map (inspected 2026-06-21):
`pick_overall, team_id, player, college_name, seasons, g, mp, pts, trb, ast, fg_pct, fg3_pct,
ft_pct, mp_per_g, pts_per_g, trb_per_g, ast_per_g, ws, ws_per_48, bpm, vorp`.

**Related gotcha (same block):** on the **player page**, the totals row of `per_game_stats` is
no longer labeled "Career" but **"N Yrs"** (e.g. "2 Yrs", "14 Yrs"). `nba_careers.py` matches
both via `^(career|\d+\s+yrs?)$`. Total games (`g`) doesn't appear on that row — it stays NULL
in the seed; the `nba_career_games` actually used comes from the `draft` seed.

**Note for agents:** prefer **`data-stat`** over `read_html` in any new BBR parser.

---

## 26. College scrape died entirely from a single page timeout

**Symptom:** `python college.py` (480 pages) aborted mid-run with
`urllib3.exceptions.ReadTimeoutError` (chromedriver); the final `to_csv` never ran (seed not
updated), and the exit code was 0 — masked by the trailing `| grep` in the pipe.

**Cause:** the `scrape()` loop only caught `ValueError` (missing table). A driver
timeout/error propagated and killed the whole run. Also, if parsing failed, `driver.quit()`
never ran (Chrome leak).

**Fix:** in `scrape()`, catch `except Exception` per page (skip and continue, logging the error
type); in `_scrape_one`, close the driver in `try/finally`. One bad page now stays out of the
seed without killing the other 479.

**General rule:** an N-page scraper must be resilient per item — broad `except` in the loop +
`finally` to release the resource. Don't trust the exit code when the command ends in `| grep`
(the exit is grep's, not python's).

---

## 27. FantasyGM ("Bandeja de 3") moved sites — extraction via internal API, not HTML

**Context:** the fantasy league migrated to `https://bskt.fantasygm.com.br/`. The site is a
React SPA — the initial HTML only has the `<title>`, so plain `requests`/fetch sees no data
(everything is JS-rendered).

**Discovery:** behind the SPA there is a clean **JSON REST API** at
`https://bskt.fantasygm.com.br:82/api`. Auth is a custom header `chavesessao: <UUID>` (the same
UUID lands in the `access_token` cookie after login). Only **one active session per user** —
two consecutive logins invalidate the older key (hence the scraper does a single login per run).

**Solution (`src/scraping/fantasy_gm.py`):** Selenium only for the login (grab the
`access_token` cookie); from there plain `requests` against the API with the `chavesessao`
header. CORS is a browser rule — server-side `requests` calls pass without preflight. Key
endpoint: `/liga/listao/{liga}` returns all 24 franchises + full rosters (per-year salaries,
positions, status) in one call. Credentials come from `FGM_EMAIL`/`FGM_PASS` (env vars, never
hard-coded); CSVs land in `dbt/seeds/` (gitignored).

**Pitfall:** `build_driver()` (with `selenium-stealth`, needed for BBR/Cloudflare) makes
startup slow and blows the snap chromedriver's 120 s timeout. FantasyGM has no anti-bot
protection, so this scraper uses a lightweight driver **without stealth** (`_plain_driver()`).
If startup still times out, kill orphaned Chromes and retry.

---

## 28. Fantasy Streamlit app crashed for users without matplotlib

**Context:** the dashboard's Cap tab used `df.style.background_gradient(cmap=...)`. That pandas
styler requires **matplotlib**, which is not a project dependency (the fantasy engine is
deliberately lightweight — reads seeds, no DB, no heavy plotting libs). On a clean clone the
app started but threw `ImportError: background_gradient requires matplotlib` on the Cap tab.

**Discovery:** caught by a headless smoke test with `streamlit.testing.v1.AppTest` (runs the
whole script without a server and collects `at.exception`) — worth running whenever the app
changes; it catches per-tab errors that would only surface on click.

**Fix:** replaced `background_gradient` with `Styler.map` and conditional colors (green if cap
space > $20M, red if < $5M). `Styler.map` is pure HTML/CSS, **no matplotlib** — the app is
portable again. Same pattern used for the "worth buying" highlight on the Draft Board.

**Related pitfall:** `dashboard/fa_draft_engine.py` uses a relative import
(`from fantasy_engine import ...`) — it only runs **from `dashboard/`**, not from the repo root.

---

## 29. Scraped roster was pre-trade — trade overrides without re-scraping

**Context:** the FantasyGM scrape is a snapshot; trades closed *after* the scrape (or agreed
off-site and not yet processed) don't show up — contaminating cap, valuation, and the winrate
simulation.

**Solution (`dashboard/fantasy_engine.py` → `_apply_trade_overrides`):** versioned manual seed
`dbt/seeds/fantasy_trade_overrides.csv` (`player_name, to_franchise`). On load, the engine
reassigns each player (with their contract) to the new franchise on top of the snapshot — a
trade becomes "move the player's row from one team to another". Future picks aren't roster rows
so they're not included (they only affect the draft, not current cap). It is **reproducible,
requires no re-scrape**, and self-retires: once a fresh scrape already reflects the trade, the
override becomes a no-op.

**Why override instead of re-scrape:** re-scraping needs Selenium + credentials and only helps
if the trade is already processed on the site; the override is instant, versioned, and doubles
as an auditable trade record. `fantasy_trade_overrides.csv` is a manual seed → needs a
`.gitignore` exception (like `my_roster.csv`/`nba_landing_spots.csv`).

**After applying an override, rebuild the cache** (otherwise the FA/Draft tabs show stale
state): `python -c "from fa_draft_engine import FADraft; FADraft().build_all()"`.

---

## 30. Fantasy views "disappeared" after a partial build — Postgres DROP CASCADE

**Symptom:** the dashboard broke with `relation "analytics_marts.fct_my_roster" does not
exist`; building only the folder (`dbt run --select models/marts/fantasy
models/staging/fantasy`) made the metrics models fail with `int_fantasy__roster_valuation does
not exist` — even though that view had been created in a previous run.

**Cause:** on Postgres, dbt recreates staging views with `drop ... cascade`. The CASCADE also
drops the DEPENDENT views (the intermediates), and since they weren't in the run selection,
nothing recreated them. Aggravating factor: the `nba_landing_spots` seed had never been loaded
(`fct_draft_board` depends on it).

**Fix:** always build the fantasy layer with its upstream closure (from `dbt/`):

```bash
uv run dbt seed --select nba_landing_spots   # once
uv run dbt run  --select +models/marts/fantasy
```

The `+` includes staging + intermediate + marts in dependency order (29 models, ~16 s).
General rule: **in a partial run over view-materialized staging, always include the
downstream** — or use a `+` selector. (Note: the "DB crashed during build" from an older
session did not reproduce as a model crash; Postgres went down once on WSL and recovered by
itself — if it recurs, investigate WSL memory, not the SQL.)

## 31. Comps tab took ~8 min per query — k-NN view recomputed on every query

**Context:** the unified dashboard's AppTest smoke test blew the 300 s timeout. Instrumenting
`q()` with a timer: the Comps tab query (`int_prospect__comps` filtered by prospect) took
**503 s**, and a `select distinct` on the same relation, 15 s.

**Cause:** `int_prospect__comps` was a **view** (the intermediate-layer default) — and its SQL
does the full k-NN (cross join of ~3.7k player-seasons × standardized features + window
functions). The `where prospect_id = ...` filter doesn't push down into the windows: Postgres
recomputed the ENTIRE k-NN per query.

**Fix:** `{{ config(materialized='table') }}` on the model (a documented exception to the
view-default of the intermediate layer). The tab query went from 503 s to ~0 s; the full smoke
test from ~9 min to ~1 min. General rule: **a model with a heavy cross-join/window that is
queried interactively → table, not view.**

> Backlog (R6 peer review): the O(n²) itself is still paid on every `dbt run` (~13.7M pairs).
> If the college backbone grows, prune the cross join by archetype inside the join itself
> (main path same-archetype + fallback branch).

## 32. Dashboard froze when an RSS feed was down — feedparser has no timeout

**Context:** `dashboard/news.py` uses `feedparser.parse(url)`, which **exposes no timeout** —
a dead feed holds the socket indefinitely and freezes the whole dashboard (and the AppTest).

**Fix:** `socket.setdefaulttimeout(10)` around the fetch (restored in `finally`). A dead feed
now costs at most 10 s and the dashboard proceeds with the rest.

## 33. Gitignored seed with no CI sample — dbt breaks at PARSE on the next PR

**Context:** the `stg_fantasy__*` models `ref()` seeds that the FantasyGM scraper generates and
`.gitignore` excludes (`fantasy_rosters`, `fantasy_franchises`, `fantasy_standings`,
`fantasy_draft_class`). CI copies `ci/sample_seeds/*.csv` into `dbt/seeds/` before
`dbt compile` — and there was no fantasy sample at all. A `ref()` to a seed with no file
doesn't resolve: the **parse** fails, before seed/run even start.

**Fix:** `ci/make_sample_seeds.py` now generates all 4 (full copies with `nome_usuario`
anonymized; with an existence guard for machines without the scrape).
**General rule: every gitignored seed that any model references NEEDS a sample in
`ci/sample_seeds/`** — when creating a new staging model over a scraper seed, update the
generator and run `python ci/make_sample_seeds.py`.

Bonus finding: with the whole league in the samples but `players_stats` sampled down (25
players), the `rank()` in `fct_league_category_strength` tied totals and the
`unique league_rank` test would fail — fixed with a deterministic tiebreak:
`row_number() over (order by total_va desc, franchise_id)`.

## 34. The engine played with 6 categories — the league has 7 (Plus/Minus was missing)

**Context:** the league decides a matchup by **4+ of 7 categories** (PTS, REB, AST, STOCKS,
3PM, **+/-**, TOV), but `fantasy_engine` valued and simulated with 6: +/- was left out because
BBR's per-game table (`players_stats.csv`) doesn't carry that column. Consequences: the binary
simulation used the wrong rule (4 of 6 plus "3-3 ties" that can't exist with 7 cats), the value
metric was missing an entire category, and FA weights were distorted.

**Fix:** `Engine._merge_plus_minus()` — per-game +/- comes from the **gamelogs** (26.6k games,
99.9% coverage; the field is a string "+5"/"-3" → tolerant coercion), averaged per player into
`PM_pg` in `self.stats`; `PM` added to `CATS`, `_cat_vector`, the fit, and the column lists.
Matchup rule corrected to 4+ of 7 (no ties). In the projections module, PM enters the VALUE
categories but stays OUT of the per-game Floor/Ceiling/CV score — it is signed and crosses
zero, which would break the CV.

**Why it took so long to surface:** the dbt marts were ALWAYS 7-cat (`z_plus_minus` existed
from the start) — only the Python decision engine was on 6. The fix materially changed player
valuations and category weights. General rule: **validate the engine's category list against
the league's written rules, not against what the data source happens to offer.**

## Recovery command cheat-sheet

All dbt commands run from `dbt/` via `uv run`:

| Situation | Command |
|---|---|
| New packages added to `packages.yml` | `uv run dbt deps` |
| Columns added/removed in a seed CSV | `uv run dbt seed --full-refresh` |
| A mart model's schema changed | `uv run dbt run --full-refresh --select <model>` |
| BBR blocked by Cloudflare | Install `selenium-stealth` and apply it in `build_driver()` |
| BBR table not found | Inspect IDs with `[t.get("id") for t in soup.find_all("table")]` |
| All `bbr_id` NaN after scraping | Check the player cell's `data-stat` — it may have changed |
| Chrome tab crashed in a scraper | Rerun the script — it resumes from the partial CSV |
| Corrupted surrogate keys (ID collision) | `uv run dbt run --full-refresh` |
| FK tests failing | Compare abbreviations in `team_info.csv` vs scraped data |
| `Connection refused` on `dbt debug` (port 5432) | `docker compose up -d postgres` (not a local service — see #23) |
| `postgres adapter not supported by dbt Fusion` | Use `uv run dbt` (bare PATH `dbt` resolves to fusion — see #24) |
