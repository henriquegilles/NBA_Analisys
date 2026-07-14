# Data Model — NBA Analytics

---

## 1. Logical Model

The logical model describes the **business entities**, their attributes in plain language, and
the **relationships** between them, independent of technology.

### Entities and relationships

```
┌─────────────────────┐         ┌──────────────────────┐
│      PLAYER         │         │        TEAM          │
│─────────────────────│         │──────────────────────│
│ PK  player_id       │◄────────│ PK  team_id          │
│     name            │  plays  │     abbreviation      │
│     bbr_id          │  for    │     full_name         │
│     position        │         │     city              │
│     age             │         │     conference        │
│ FK  current_team_id │         │     division          │
│     conference      │         │     historic_wins     │
│     division        │         │     championships     │
└─────────────────────┘         └──────────────────────┘
          │                               │
          │ has                           │ has
          │                               │
          ▼                               ▼
┌──────────────────────────────────────────────────────────┐
│                  SEASON STATISTICS                       │
│  (grain: player × season)                                │
│──────────────────────────────────────────────────────────│
│ PK  stat_key                                             │
│ FK  player_id → PLAYER                                   │
│ FK  team_id   → TEAM                                     │
│     season  (e.g. 2025-26)                               │
│     games, minutes, points, rebounds, assists...         │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│              ADVANCED SEASON STATISTICS                  │
│  (grain: player × season × season_type)                  │
│──────────────────────────────────────────────────────────│
│ PK  adv_key                                              │
│ FK  player_id  → PLAYER                                  │
│ FK  team_id    → TEAM                                    │
│     season                                               │
│     season_type  (regular | playoffs)                    │
│     PER, TS%, WS, BPM, VORP...                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│               GAME LOG (PLAYER × GAME)                   │
│  (grain: player × game)                                  │
│──────────────────────────────────────────────────────────│
│ PK  game_player_key                                      │
│ FK  player_id      → PLAYER                              │
│ FK  team_id        → TEAM  (player's team)               │
│ FK  opponent_id    → TEAM  (opposing team)               │
│     game_date                                            │
│     result  (W | L)                                      │
│     home_away  (home | away)                             │
│     minutes, points, game_score, +/-...                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  PLAYER CONTRACT                         │
│  (grain: player — current snapshot)                      │
│──────────────────────────────────────────────────────────│
│ PK  contract_key                                         │
│ FK  player_id  → PLAYER                                  │
│ FK  team_id    → TEAM                                    │
│     salary_2024_25, salary_2025_26...                    │
│     cba_mechanism  (Bird Rights, MLE, Rookie Scale...)   │
│     guaranteed_amount                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  DRAFT (PICK)                            │
│  (grain: draft_year × pick_number)                       │
│──────────────────────────────────────────────────────────│
│ PK  draft_pick_key                                       │
│ FK  player_id     → PLAYER  (null if never played)       │
│     draft_year                                           │
│     round  (1 | 2)                                       │
│     pick_number                                          │
│     drafting_team                                        │
│     college                                              │
│     career_wins, career BPM, VORP...                     │
└──────────────────────────────────────────────────────────┘
```

### Cardinalities

| Relationship | Type | Notes |
|---|---|---|
| PLAYER → TEAM (current) | N:1 | Each player belongs to 1 team; a team has N players |
| PLAYER → SEASON STATISTICS | 1:N | One row per season the player was active |
| PLAYER → ADVANCED STATISTICS | 1:N | One row per season × type (regular/playoffs) |
| PLAYER → GAME LOG | 1:N | One row per game played in the season |
| PLAYER → CONTRACT | 1:1 | Current contract snapshot |
| PLAYER → DRAFT | 1:1 (opt.) | Not every draftee reaches the NBA; undrafted players have no row |
| TEAM → GAME LOG (opponent) | 1:N | A team appears as the opponent in N game-log rows |

---

## 2. Physical Model

The physical model details the **actual PostgreSQL tables** (schema `analytics_marts`), with
data types, PKs and FKs.

### Conventions

- Surrogate keys: `VARCHAR` generated as `MD5(natural_fields)` via the `generate_surrogate_key()` macro
- Percentages: `NUMERIC(5,3)` — stored as decimals (0–1), e.g. 0.512
- Salaries: `VARCHAR` — BBR formats them as `"$12,345,678"`; parsed at analysis time
- Dates: `DATE`
- Season: `VARCHAR(7)` — `"YYYY-YY"` format, e.g. `"2025-26"`

---

### `analytics_marts.dim_player`

```sql
CREATE TABLE analytics_marts.dim_player (
    player_key          VARCHAR     NOT NULL,   -- PK  MD5(player_name)
    player_name         VARCHAR     NOT NULL,   --     full name
    bbr_id              VARCHAR,                --     BBR identifier (e.g. jamesle01)
    position            VARCHAR,                --     position (G, F, C)
    age                 INTEGER,                --     age
    current_team_abbr   VARCHAR,                -- FK  → dim_team.team_abbr
    current_team_name   VARCHAR,                --     team name
    conference          VARCHAR,                --     East | West
    division            VARCHAR,                --     Atlantic | Central | ...

    CONSTRAINT pk_dim_player PRIMARY KEY (player_key),
    CONSTRAINT uq_dim_player_name UNIQUE (player_name),
    CONSTRAINT uq_dim_player_bbr_id UNIQUE (bbr_id),
    CONSTRAINT fk_dim_player_team
        FOREIGN KEY (current_team_abbr) REFERENCES analytics_marts.dim_team(team_abbr)
);
```

---

### `analytics_marts.dim_team`

```sql
CREATE TABLE analytics_marts.dim_team (
    team_key            VARCHAR     NOT NULL,   -- PK  MD5(team_abbr)
    team_abbr           VARCHAR(3)  NOT NULL,   --     BBR abbreviation (LAL, BOS...)
    team_name           VARCHAR,                --     full name
    city                VARCHAR,                --     city
    conference          VARCHAR,                --     East | West
    division            VARCHAR,                --     division
    wins                INTEGER,                --     historic wins
    losses              INTEGER,                --     historic losses
    win_loss_pct        NUMERIC(5,3),           --     win % (0–1)
    playoff_appearances INTEGER,
    division_titles     INTEGER,
    conference_titles   INTEGER,
    championships       INTEGER,

    CONSTRAINT pk_dim_team PRIMARY KEY (team_key),
    CONSTRAINT uq_dim_team_abbr UNIQUE (team_abbr)
);
```

---

### `analytics_marts.fct_player_season_stats`

```sql
CREATE TABLE analytics_marts.fct_player_season_stats (
    fact_key            VARCHAR     NOT NULL,   -- PK  MD5(player_name, season)
    player_key          VARCHAR     NOT NULL,   -- FK  → dim_player.player_key
    team_key            VARCHAR,                -- FK  → dim_team.team_key
    player_name         VARCHAR     NOT NULL,
    team_abbr           VARCHAR,
    position            VARCHAR,
    season              VARCHAR(7)  NOT NULL,   --     e.g. '2025-26'

    -- Participation
    games_played        INTEGER,
    games_started       INTEGER,
    minutes_per_game    NUMERIC(6,1),

    -- Field goals
    fg_per_game         NUMERIC(5,1),
    fga_per_game        NUMERIC(5,1),
    fg_pct              NUMERIC(5,3),
    three_pt_per_game   NUMERIC(5,1),
    three_pt_attempted  NUMERIC(5,1),
    three_pt_pct        NUMERIC(5,3),
    two_pt_per_game     NUMERIC(5,1),
    two_pt_attempted    NUMERIC(5,1),
    two_pt_pct          NUMERIC(5,3),
    efg_pct             NUMERIC(5,3),

    -- Free throws
    ft_per_game         NUMERIC(5,1),
    fta_per_game        NUMERIC(5,1),
    ft_pct              NUMERIC(5,3),

    -- Rebounds
    off_reb_per_game    NUMERIC(5,1),
    def_reb_per_game    NUMERIC(5,1),
    total_reb_per_game  NUMERIC(5,1),

    -- Other
    assists_per_game       NUMERIC(5,1),
    steals_per_game        NUMERIC(5,1),
    blocks_per_game        NUMERIC(5,1),
    turnovers_per_game     NUMERIC(5,1),
    personal_fouls_per_game NUMERIC(5,1),
    points_per_game        NUMERIC(5,1),

    CONSTRAINT pk_fct_season_stats PRIMARY KEY (fact_key),
    CONSTRAINT fk_fct_season_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key),
    CONSTRAINT fk_fct_season_team
        FOREIGN KEY (team_key) REFERENCES analytics_marts.dim_team(team_key)
);
```

---

### `analytics_marts.fct_player_advanced_stats`

```sql
CREATE TABLE analytics_marts.fct_player_advanced_stats (
    fact_key            VARCHAR     NOT NULL,   -- PK  MD5(player_name, season, season_type)
    player_key          VARCHAR     NOT NULL,   -- FK  → dim_player.player_key
    team_key            VARCHAR,                -- FK  → dim_team.team_key
    player_name         VARCHAR     NOT NULL,
    team_abbr           VARCHAR,
    position            VARCHAR,
    season              VARCHAR(7)  NOT NULL,
    season_type         VARCHAR(8)  NOT NULL,   --     'regular' | 'playoffs'

    -- Participation
    games_played        INTEGER,
    minutes_played      INTEGER,

    -- Efficiency
    per                 NUMERIC(6,1),           --     Player Efficiency Rating
    ts_pct              NUMERIC(5,3),           --     True Shooting %
    three_p_ar          NUMERIC(5,3),           --     3-Point Attempt Rate
    ftr                 NUMERIC(5,3),           --     Free Throw Rate
    usg_pct             NUMERIC(5,1),           --     Usage Rate %

    -- Rebounding rates
    orb_pct             NUMERIC(5,1),
    drb_pct             NUMERIC(5,1),
    trb_pct             NUMERIC(5,1),

    -- Playmaking / defense rates
    ast_pct             NUMERIC(5,1),
    stl_pct             NUMERIC(5,1),
    blk_pct             NUMERIC(5,1),
    tov_pct             NUMERIC(5,1),

    -- Win Shares
    offensive_win_shares  NUMERIC(6,1),
    defensive_win_shares  NUMERIC(6,1),
    win_shares            NUMERIC(6,1),
    ws_per_48             NUMERIC(6,3),

    -- Box Plus/Minus
    obpm                NUMERIC(6,1),
    dbpm                NUMERIC(6,1),
    bpm                 NUMERIC(6,1),
    vorp                NUMERIC(6,1),

    CONSTRAINT pk_fct_advanced_stats PRIMARY KEY (fact_key),
    CONSTRAINT fk_fct_adv_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key),
    CONSTRAINT fk_fct_adv_team
        FOREIGN KEY (team_key) REFERENCES analytics_marts.dim_team(team_key)
);
```

---

### `analytics_marts.fct_player_game_log`

```sql
CREATE TABLE analytics_marts.fct_player_game_log (
    game_player_key     VARCHAR     NOT NULL,   -- PK  MD5(bbr_id, game_date, team_abbr)
    player_key          VARCHAR,                -- FK  → dim_player.player_key
    team_key            VARCHAR,                -- FK  → dim_team.team_key
    opponent_team_key   VARCHAR,                -- FK  → dim_team.team_key (opponent)
    bbr_id              VARCHAR     NOT NULL,   --     BBR identifier
    player_name         VARCHAR,
    season              VARCHAR(7)  NOT NULL,
    game_date           DATE        NOT NULL,
    game_year           INTEGER,
    team_abbr           VARCHAR,
    opponent_abbr       VARCHAR,
    home_away           VARCHAR(4),             --     'home' | 'away'
    result              VARCHAR(1),             --     'W' | 'L'
    point_diff          INTEGER,                --     game margin
    games_started       INTEGER,                --     1 = starter | 0 = bench

    -- Playing time
    minutes_played      NUMERIC(6,2),           --     decimal (e.g. 32.23)
    minutes_played_str  VARCHAR,                --     original "MM:SS" string

    -- Shooting
    fg                  NUMERIC(5,1),
    fga                 NUMERIC(5,1),
    fg_pct              NUMERIC(5,3),
    three_p             NUMERIC(5,1),
    three_pa            NUMERIC(5,1),
    three_p_pct         NUMERIC(5,3),
    ft                  NUMERIC(5,1),
    fta                 NUMERIC(5,1),
    ft_pct              NUMERIC(5,3),

    -- Rebounds
    orb                 NUMERIC(5,1),
    drb                 NUMERIC(5,1),
    trb                 NUMERIC(5,1),

    -- Other
    ast                 NUMERIC(5,1),
    stl                 NUMERIC(5,1),
    blk                 NUMERIC(5,1),
    tov                 NUMERIC(5,1),
    pf                  NUMERIC(5,1),
    pts                 NUMERIC(5,1),
    game_score          NUMERIC(6,1),           --     Hollinger Game Score
    plus_minus          INTEGER,

    CONSTRAINT pk_fct_game_log PRIMARY KEY (game_player_key),
    CONSTRAINT fk_fct_gl_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key),
    CONSTRAINT fk_fct_gl_team
        FOREIGN KEY (team_key) REFERENCES analytics_marts.dim_team(team_key),
    CONSTRAINT fk_fct_gl_opponent
        FOREIGN KEY (opponent_team_key) REFERENCES analytics_marts.dim_team(team_key)
);
```

---

### `analytics_marts.fct_draft_class`

```sql
CREATE TABLE analytics_marts.fct_draft_class (
    draft_pick_key      VARCHAR     NOT NULL,   -- PK  MD5(draft_year, pick)
    player_key          VARCHAR,                -- FK  → dim_player.player_key (nullable)
    draft_year          INTEGER     NOT NULL,   --     draft year (1986–2025)
    round               INTEGER,                --     1 or 2
    pick                INTEGER     NOT NULL,   --     overall pick number
    drafting_team       VARCHAR,                -- ref → dim_team.team_abbr
    player_name         VARCHAR     NOT NULL,
    college             VARCHAR,

    -- Career volume
    career_seasons      INTEGER,
    career_games        INTEGER,
    career_minutes      INTEGER,
    career_points       INTEGER,
    career_reb          INTEGER,
    career_ast          INTEGER,

    -- Career percentages
    career_fg_pct       NUMERIC(5,3),
    career_3p_pct       NUMERIC(5,3),
    career_ft_pct       NUMERIC(5,3),

    -- Career per-game averages
    pg_mp               NUMERIC(5,1),
    pg_pts              NUMERIC(5,1),
    pg_trb              NUMERIC(5,1),
    pg_ast              NUMERIC(5,1),

    -- Career advanced metrics
    win_shares          NUMERIC(6,1),
    ws_per_48           NUMERIC(6,3),
    bpm                 NUMERIC(6,1),
    vorp                NUMERIC(6,1),

    -- Derived
    reached_3_seasons   BOOLEAN,

    CONSTRAINT pk_fct_draft PRIMARY KEY (draft_pick_key),
    CONSTRAINT fk_fct_draft_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key)
);
```

---

### `analytics_marts.fct_player_contract`

```sql
CREATE TABLE analytics_marts.fct_player_contract (
    contract_key        VARCHAR     NOT NULL,   -- PK  MD5(player_name)
    player_key          VARCHAR,                -- FK  → dim_player.player_key
    team_key            VARCHAR,                -- FK  → dim_team.team_key
    player_name         VARCHAR     NOT NULL,
    team_abbr           VARCHAR,

    -- Salaries per season (BBR string — "$12,345,678")
    -- For numeric: replace(replace(salary_2025_26,'$',''),',','')::bigint
    salary_2024_25      VARCHAR,
    salary_2025_26      VARCHAR,
    salary_2026_27      VARCHAR,
    salary_2027_28      VARCHAR,
    salary_2028_29      VARCHAR,

    -- Contract details
    signed_using        VARCHAR,                --     CBA mechanism
    guaranteed          VARCHAR,                --     guaranteed amount

    CONSTRAINT pk_fct_contract PRIMARY KEY (contract_key),
    CONSTRAINT fk_fct_contract_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key),
    CONSTRAINT fk_fct_contract_team
        FOREIGN KEY (team_key) REFERENCES analytics_marts.dim_team(team_key)
);
```

---

## 3. Key map — summary

```
dim_player ────────────────────────────────────── dim_team
│  PK: player_key                                  PK: team_key
│  NK: player_name (unique)                        NK: team_abbr (unique)
│  NK: bbr_id (unique)                             │
│  FK: current_team_abbr → dim_team.team_abbr ─────┘
│
├── fct_player_season_stats
│    PK: fact_key  (MD5 player_name + season)
│    FK: player_key → dim_player
│    FK: team_key  → dim_team
│
├── fct_player_advanced_stats
│    PK: fact_key  (MD5 player_name + season + season_type)
│    FK: player_key → dim_player
│    FK: team_key  → dim_team
│
├── fct_player_game_log
│    PK: game_player_key  (MD5 bbr_id + game_date + team_abbr)
│    FK: player_key       → dim_player
│    FK: team_key         → dim_team  (player's team)
│    FK: opponent_team_key → dim_team  (opposing team)
│
├── fct_player_contract
│    PK: contract_key  (MD5 player_name)
│    FK: player_key    → dim_player
│    FK: team_key      → dim_team
│
└── fct_draft_class
     PK: draft_pick_key  (MD5 draft_year + pick)
     FK: player_key      → dim_player  (nullable)
     ref: drafting_team  → dim_team.team_abbr (no formal FK — team may no longer exist)
```

---

## 4. Integrity notes

| Situation | Behavior |
|---|---|
| Traded player | `dim_player` keeps 1 row with the latest team; facts use `player_key` as usual |
| Draftee who never played | `fct_draft_class.player_key` is NULL — intentional LEFT JOIN |
| Historic team in the draft | `drafting_team` has no formal FK — defunct teams (SEA, NJN) don't exist in `dim_team` |
| Playoffs not scraped | `fct_player_advanced_stats` only has `season_type = 'regular'` until the playoff scrape runs |
| Salary unavailable | `salary_*` columns stay NULL — BBR omits unconfirmed future amounts |
