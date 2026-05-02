# Modelo de Dados — NBA Analytics

---

## 1. Modelo Lógico

O modelo lógico descreve as **entidades de negócio**, seus atributos em linguagem natural e os **relacionamentos** entre elas, independente de tecnologia.

### Entidades e relacionamentos

```
┌─────────────────────┐         ┌──────────────────────┐
│     JOGADOR         │         │        TIME          │
│─────────────────────│         │──────────────────────│
│ PK  jogador_id      │◄────────│ PK  time_id          │
│     nome            │   joga  │     abreviação        │
│     bbr_id          │   em    │     nome_completo     │
│     posição         │         │     cidade            │
│     idade           │         │     conferência       │
│ FK  time_atual_id   │         │     divisão           │
│     conferência     │         │     vitórias_hist.    │
│     divisão         │         │     campeonatos       │
└─────────────────────┘         └──────────────────────┘
          │                               │
          │ tem                           │ tem
          │                               │
          ▼                               ▼
┌──────────────────────────────────────────────────────────┐
│              ESTATÍSTICAS POR TEMPORADA                  │
│  (grain: jogador × temporada)                            │
│──────────────────────────────────────────────────────────│
│ PK  stat_key                                             │
│ FK  jogador_id → JOGADOR                                 │
│ FK  time_id    → TIME                                    │
│     temporada  (ex: 2025-26)                             │
│     jogos, minutos, pontos, rebotes, assistências...     │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│          ESTATÍSTICAS AVANÇADAS POR TEMPORADA            │
│  (grain: jogador × temporada × tipo_temporada)           │
│──────────────────────────────────────────────────────────│
│ PK  adv_key                                              │
│ FK  jogador_id  → JOGADOR                                │
│ FK  time_id     → TIME                                   │
│     temporada                                            │
│     tipo_temporada  (regular | playoffs)                 │
│     PER, TS%, WS, BPM, VORP...                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│               GAME LOG (PARTIDA POR JOGADOR)             │
│  (grain: jogador × partida)                              │
│──────────────────────────────────────────────────────────│
│ PK  game_player_key                                      │
│ FK  jogador_id      → JOGADOR                            │
│ FK  time_id         → TIME  (time do jogador)            │
│ FK  adversario_id   → TIME  (time adversário)            │
│     data_partida                                         │
│     resultado  (W | L)                                   │
│     casa_fora  (home | away)                             │
│     minutos, pontos, game_score, +/-...                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                CONTRATO DO JOGADOR                       │
│  (grain: jogador — snapshot atual)                       │
│──────────────────────────────────────────────────────────│
│ PK  contrato_key                                         │
│ FK  jogador_id  → JOGADOR                                │
│ FK  time_id     → TIME                                   │
│     salário_2024_25, salário_2025_26...                  │
│     mecanismo_cba  (Bird Rights, MLE, Rookie Scale...)   │
│     valor_garantido                                      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  DRAFT (ESCOLHA)                         │
│  (grain: ano_draft × número_da_escolha)                  │
│──────────────────────────────────────────────────────────│
│ PK  draft_pick_key                                       │
│ FK  jogador_id     → JOGADOR  (null se nunca jogou)      │
│     ano_draft                                            │
│     rodada  (1 | 2)                                      │
│     número_da_escolha                                    │
│     time_selecionador                                    │
│     faculdade                                            │
│     vitórias_carreira, BPM, VORP carreira...             │
└──────────────────────────────────────────────────────────┘
```

### Cardinalidades

| Relacionamento | Tipo | Observação |
|---|---|---|
| JOGADOR → TIME (atual) | N:1 | Cada jogador pertence a 1 time; um time tem N jogadores |
| JOGADOR → ESTATÍSTICAS POR TEMPORADA | 1:N | Uma linha por temporada que o jogador esteve ativo |
| JOGADOR → ESTATÍSTICAS AVANÇADAS | 1:N | Uma linha por temporada × tipo (regular/playoffs) |
| JOGADOR → GAME LOG | 1:N | Uma linha por jogo disputado na temporada |
| JOGADOR → CONTRATO | 1:1 | Snapshot atual do contrato |
| JOGADOR → DRAFT | 1:1 (opt.) | Nem todo draftado chega à NBA; jogadores não draftados não têm linha |
| TIME → GAME LOG (adversário) | 1:N | Um time aparece como adversário em N linhas de game log |

---

## 2. Modelo Físico

O modelo físico detalha as **tabelas reais no PostgreSQL** (schema `analytics_marts`), com tipos de dados, PKs e FKs.

### Convenções

- Surrogate keys: `VARCHAR` gerado por `MD5(campos_naturais)` via macro `generate_surrogate_key()`
- Percentuais: `NUMERIC(5,3)` — armazenados como decimal (0–1), ex: 0.512
- Salários: `VARCHAR` — o BBR formata como `"$12,345,678"`; parse em análise
- Datas: `DATE`
- Temporada: `VARCHAR(7)` — formato `"YYYY-YY"`, ex: `"2025-26"`

---

### `analytics_marts.dim_player`

```sql
CREATE TABLE analytics_marts.dim_player (
    player_key          VARCHAR     NOT NULL,   -- PK  MD5(player_name)
    player_name         VARCHAR     NOT NULL,   --     nome completo
    bbr_id              VARCHAR,                --     identificador BBR (ex: jamesle01)
    position            VARCHAR,                --     posição (G, F, C)
    age                 INTEGER,                --     idade
    current_team_abbr   VARCHAR,                -- FK  → dim_team.team_abbr
    current_team_name   VARCHAR,                --     nome do time
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
    team_abbr           VARCHAR(3)  NOT NULL,   --     abreviação BBR (LAL, BOS...)
    team_name           VARCHAR,                --     nome completo
    city                VARCHAR,                --     cidade
    conference          VARCHAR,                --     East | West
    division            VARCHAR,                --     divisão
    wins                INTEGER,                --     vitórias históricas
    losses              INTEGER,                --     derrotas históricas
    win_loss_pct        NUMERIC(5,3),           --     % vitórias (0–1)
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
    season              VARCHAR(7)  NOT NULL,   --     ex: '2025-26'

    -- Participação
    games_played        INTEGER,
    games_started       INTEGER,
    minutes_per_game    NUMERIC(6,1),

    -- Arremessos de quadra
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

    -- Lances livres
    ft_per_game         NUMERIC(5,1),
    fta_per_game        NUMERIC(5,1),
    ft_pct              NUMERIC(5,3),

    -- Rebotes
    off_reb_per_game    NUMERIC(5,1),
    def_reb_per_game    NUMERIC(5,1),
    total_reb_per_game  NUMERIC(5,1),

    -- Outros
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

    -- Participação
    games_played        INTEGER,
    minutes_played      INTEGER,

    -- Eficiência
    per                 NUMERIC(6,1),           --     Player Efficiency Rating
    ts_pct              NUMERIC(5,3),           --     True Shooting %
    three_p_ar          NUMERIC(5,3),           --     3-Point Attempt Rate
    ftr                 NUMERIC(5,3),           --     Free Throw Rate
    usg_pct             NUMERIC(5,1),           --     Usage Rate %

    -- Taxas de rebote
    orb_pct             NUMERIC(5,1),
    drb_pct             NUMERIC(5,1),
    trb_pct             NUMERIC(5,1),

    -- Taxas de criação / defesa
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
    opponent_team_key   VARCHAR,                -- FK  → dim_team.team_key (adversário)
    bbr_id              VARCHAR     NOT NULL,   --     identificador BBR
    player_name         VARCHAR,
    season              VARCHAR(7)  NOT NULL,
    game_date           DATE        NOT NULL,
    game_year           INTEGER,
    team_abbr           VARCHAR,
    opponent_abbr       VARCHAR,
    home_away           VARCHAR(4),             --     'home' | 'away'
    result              VARCHAR(1),             --     'W' | 'L'
    point_diff          INTEGER,                --     margem do jogo
    games_started       INTEGER,                --     1 = titular | 0 = reserva

    -- Tempo de jogo
    minutes_played      NUMERIC(6,2),           --     decimal (ex: 32.23)
    minutes_played_str  VARCHAR,                --     string original "MM:SS"

    -- Arremessos
    fg                  NUMERIC(5,1),
    fga                 NUMERIC(5,1),
    fg_pct              NUMERIC(5,3),
    three_p             NUMERIC(5,1),
    three_pa            NUMERIC(5,1),
    three_p_pct         NUMERIC(5,3),
    ft                  NUMERIC(5,1),
    fta                 NUMERIC(5,1),
    ft_pct              NUMERIC(5,3),

    -- Rebotes
    orb                 NUMERIC(5,1),
    drb                 NUMERIC(5,1),
    trb                 NUMERIC(5,1),

    -- Outros
    ast                 NUMERIC(5,1),
    stl                 NUMERIC(5,1),
    blk                 NUMERIC(5,1),
    tov                 NUMERIC(5,1),
    pf                  NUMERIC(5,1),
    pts                 NUMERIC(5,1),
    game_score          NUMERIC(6,1),           --     Game Score de Hollinger
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
    draft_year          INTEGER     NOT NULL,   --     ano do draft (1986–2025)
    round               INTEGER,                --     1 ou 2
    pick                INTEGER     NOT NULL,   --     número geral
    drafting_team       VARCHAR,                -- ref → dim_team.team_abbr
    player_name         VARCHAR     NOT NULL,
    college             VARCHAR,

    -- Volume de carreira
    career_seasons      INTEGER,
    career_games        INTEGER,
    career_minutes      INTEGER,
    career_points       INTEGER,
    career_reb          INTEGER,
    career_ast          INTEGER,

    -- Percentuais de carreira
    career_fg_pct       NUMERIC(5,3),
    career_3p_pct       NUMERIC(5,3),
    career_ft_pct       NUMERIC(5,3),

    -- Médias por jogo na carreira
    pg_mp               NUMERIC(5,1),
    pg_pts              NUMERIC(5,1),
    pg_trb              NUMERIC(5,1),
    pg_ast              NUMERIC(5,1),

    -- Métricas avançadas de carreira
    win_shares          NUMERIC(6,1),
    ws_per_48           NUMERIC(6,3),
    bpm                 NUMERIC(6,1),
    vorp                NUMERIC(6,1),

    -- Derivado
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

    -- Salários por temporada (string BBR — "$12,345,678")
    -- Para numérico: replace(replace(salary_2025_26,'$',''),',','')::bigint
    salary_2024_25      VARCHAR,
    salary_2025_26      VARCHAR,
    salary_2026_27      VARCHAR,
    salary_2027_28      VARCHAR,
    salary_2028_29      VARCHAR,

    -- Detalhes do contrato
    signed_using        VARCHAR,                --     mecanismo CBA
    guaranteed          VARCHAR,                --     valor garantido

    CONSTRAINT pk_fct_contract PRIMARY KEY (contract_key),
    CONSTRAINT fk_fct_contract_player
        FOREIGN KEY (player_key) REFERENCES analytics_marts.dim_player(player_key),
    CONSTRAINT fk_fct_contract_team
        FOREIGN KEY (team_key) REFERENCES analytics_marts.dim_team(team_key)
);
```

---

## 3. Mapa de chaves — resumo

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
│    FK: team_key         → dim_team  (time do jogador)
│    FK: opponent_team_key → dim_team  (time adversário)
│
├── fct_player_contract
│    PK: contract_key  (MD5 player_name)
│    FK: player_key    → dim_player
│    FK: team_key      → dim_team
│
└── fct_draft_class
     PK: draft_pick_key  (MD5 draft_year + pick)
     FK: player_key      → dim_player  (nullable)
     ref: drafting_team  → dim_team.team_abbr (sem FK formal — time pode não existir mais)
```

---

## 4. Notas de integridade

| Situação | Comportamento |
|---|---|
| Jogador trocado | `dim_player` tem 1 linha com o último time; fatos usam `player_key` normalmente |
| Draftado que nunca jogou | `fct_draft_class.player_key` é NULL — LEFT JOIN intencional |
| Time histórico no draft | `drafting_team` não tem FK formal — times extintos (SEA, NJN) não existem em `dim_team` |
| Playoffs não scrapeados | `fct_player_advanced_stats` só tem `season_type = 'regular'` enquanto playoffs não rodar |
| Salário não disponível | Colunas salary_* ficam NULL — BBR omite valores futuros não confirmados |
