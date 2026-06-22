# Plano de Robustez dos Modelos (testes + documentação)

> **Origem:** auditoria de cobertura de testes/docs dos 30 modelos (2026-06-22).
> **Status:** PLANO — nada foi aplicado ainda. **Executar e validar em outro chat.**
> Modo: este chat era de design; a edição/validação ficou explicitamente pra depois.

## Resumo da auditoria

A cobertura geral está **boa**: a maioria dos marts já tem PK testada (`unique`+`not_null`),
FKs com `relationships`, e bom uso de `accepted_values`/`dbt_utils.unique_combination_of_columns`.
Os buracos são **pontuais** — abaixo, em ordem de prioridade.

> ⚠️ **Convenção do projeto:** os yml usam a chave **`data_tests:`** (não `tests:`).
> Os snippets abaixo já seguem isso.

---

## Tier 1 — Testes de qualidade (alto valor, baixo risco)

### 1.1 `stg_bbr__nba_careers` não tem entrada no yml
**Arquivo:** `models/staging/bbr/_bbr__sources.yml` (na seção `models:`).
**Por quê:** modelo sem PK testada nem docs (0/10 colunas). `bbr_id` é único (1 linha por jogador NBA).
**Colar:**
```yaml
  - name: stg_bbr__nba_careers
    description: >
      Grão: 1 linha por jogador NBA (linha "Career" da página do BBR).
      Fornece stl/blk(→stocks), 3PM e TOV de carreira que o seed `draft` não
      traz — usado pela ponte college→NBA (D-30) via slug bbr_id.
    columns:
      - name: bbr_id
        description: "PK — slug NBA do jogador no Basketball Reference"
        data_tests:
          - unique
          - not_null
      - name: player_name
        description: Nome do jogador
        data_tests:
          - not_null
      - name: career_games
        description: "Jogos na carreira (pode ser null — BBR nem sempre repete G nessa linha)"
      - name: pg_pts
        description: Pontos por jogo na carreira
      - name: pg_trb
        description: Rebotes por jogo na carreira
      - name: pg_ast
        description: Assistências por jogo na carreira
      - name: pg_stl
        description: Roubos por jogo na carreira
      - name: pg_blk
        description: Tocos por jogo na carreira
      - name: pg_fg3
        description: Cestas de 3 por jogo na carreira
      - name: pg_tov
        description: Turnovers por jogo na carreira
```

### 1.2 `int_games__from_gamelogs` — PK composta sem teste de unicidade
**Arquivo:** `models/intermediate/_int__models.yml`, no bloco `int_games__from_gamelogs`.
**Por quê:** grão é (game_date, home_team_abbr) mas só tem `not_null` por coluna; nada prova unicidade.
**Colar** (teste a nível de modelo, **depois** do bloco `columns:`, alinhado com `- name:`):
```yaml
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - game_date
            - home_team_abbr
```

### 1.3 `team_key` sem teste `relationships` em 2 facts
**Arquivos:** `models/marts/_marts__models.yml`, blocos `fct_player_season_stats` e `fct_player_advanced_stats`.
**Por quê:** `team_key` é FK pra `dim_team` mas não é validada (os outros FKs do mesmo modelo são).
`team_key` é **nullable** (linha TOT de jogador trocado não existe em `dim_team`) → usar `where`.
**Substituir** o atual `- name: team_key` (hoje só nome+descrição) por:
```yaml
      - name: team_key
        description: "FK → dim_team.team_key (null na linha TOT de jogador trocado)"
        data_tests:
          - relationships:
              to: ref('dim_team')
              field: team_key
              config:
                where: "team_key is not null"
```
> Padrão idêntico ao já usado em `fct_draft_class.player_key` neste mesmo arquivo.

### 1.4 `int_player_advanced_stats__deduped` não tem entrada no yml
**Arquivo:** `models/intermediate/_int__models.yml` (adicionar bloco novo).
**Por quê:** é um modelo de **dedup** sem teste que prove que deduplicou (0/17 colunas documentadas).
Grão = (player_name, season, season_type).
**Colar:**
```yaml
  - name: int_player_advanced_stats__deduped
    description: >
      Remove linhas duplicadas de jogadores trocados nas advanced stats,
      mantendo só a linha agregada (TOT/NTM) por temporada e season_type.
      Mesma lógica de int_player_stats__season_totals.
    columns:
      - name: player_name
        description: Nome do jogador
        data_tests:
          - not_null
      - name: season
        description: "Temporada no formato YYYY-YY"
        data_tests:
          - not_null
      - name: season_type
        description: "regular | playoffs"
        data_tests:
          - accepted_values:
              values: ['regular', 'playoffs']
      - name: per
        description: Player Efficiency Rating
      - name: ts_pct
        description: True Shooting %
      - name: win_shares
        description: Win Shares acumuladas
      - name: bpm
        description: Box Plus/Minus
      - name: vorp
        description: Value Over Replacement Player
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - player_name
            - season
            - season_type
```

---

## Tier 2 — Documentação (preencher descrições faltantes)

Não muda comportamento; melhora legibilidade e o `dbt docs`. Prioridade pelos 0%/baixos.

| Modelo | Cobertura hoje | Ação |
|---|---|---|
| `stg_bbr__nba_careers` | 0% | ✅ resolvido junto com 1.1 |
| `int_player_advanced_stats__deduped` | 0% | ✅ resolvido junto com 1.4 |
| `int_prospect__nba_bridge` | 12% (2/17) | Documentar as colunas restantes (snippet abaixo) |
| `fct_player_game_log` | 55% | Documentar as ~9 colunas de box score sem descrição (fg, fga, three_p, ft, orb/drb, stl, blk, tov, pf, team_abbr, opponent_abbr, games_started) |
| `fct_player_season_stats` | 55% | Documentar as médias por-jogo restantes (rebotes, assist, roubos, tocos, turnovers, faltas) |
| `fct_player_advanced_stats` | 53% | Documentar as taxas (orb_pct…tov_pct, ws_per_48, obpm, dbpm) |
| `stg_bbr__player_stats` | 21% | Documentar colunas de shooting/rebote/etc. (baixa prioridade — staging) |
| `stg_bbr__teams` | 15% | Documentar colunas de franquia/títulos (baixa prioridade — staging) |

**Snippet p/ `int_prospect__nba_bridge`** (expandir o bloco existente em `_int__models.yml`):
```yaml
      - name: player_name
        description: Nome do prospecto (college)
      - name: college_school
        description: Escola do prospecto
      - name: last_college_season
        description: "Última temporada de college usada na ponte"
      - name: nba_bbr_id
        description: "Slug NBA casado (via nome+janela de ano + overrides D-09)"
      - name: draft_year
        description: Ano do draft NBA do match
      - name: pick
        description: Número da escolha no draft
      - name: reached_nba
        description: "true se o prospecto chegou à NBA"
      - name: nba_pg_pts
        description: "Pontos/jogo de carreira (do seed draft, D-29)"
      - name: nba_pg_trb
        description: Rebotes/jogo de carreira
      - name: nba_pg_ast
        description: Assistências/jogo de carreira
      - name: nba_pg_stl
        description: "Roubos/jogo de carreira (da carreira raspada, D-30)"
      - name: nba_pg_blk
        description: Tocos/jogo de carreira
      - name: nba_pg_stocks
        description: "stocks/jogo (stl+blk) de carreira"
      - name: nba_pg_fg3
        description: Cestas de 3/jogo de carreira
      - name: nba_pg_tov
        description: Turnovers/jogo de carreira
```

---

## Tier 3 — Naming/normalização: **NÃO fazer agora** (decisão)

O auditor sinalizou "inconsistências": `per_40` vs `per_game`, `ws` vs `win_shares`,
`current_team_abbr` vs `team_abbr`. **Não renomear**, porque:
- `per_40` (college) vs `per_game` (NBA) é **intencional** — normalizações diferentes.
- Renomear coluna quebra todos os `ref()` downstream por ganho **cosmético** → risco > benefício.
- O certo é **documentar a convenção** (Tier 2), não mexer no schema.

## Não tocar: staging "sem PK"

`stg_bbr__players`, `stg_bbr__player_stats`, `stg_bbr__teams`, `stg_bbr__contracts` **não devem**
ganhar teste `unique` — têm linhas duplicadas **de propósito** (BBR repete jogador trocado,
linhas "TOT"). A deduplicação é feita nos `int_*__deduped`. Um `unique` ali falharia corretamente.

---

## Como validar (no outro chat)

Os seeds estão no disco (gitignorados mas presentes nesta máquina). Banco = **Docker**.

```bash
source .venv/bin/activate
docker compose up -d postgres          # runbook #23 (não é serviço local)
dbt deps --profiles-dir .dbt            # garante dbt_utils

# Build + test só dos modelos afetados (+ upstreams):
dbt build --profiles-dir .dbt --select \
  +stg_bbr__nba_careers \
  +int_games__from_gamelogs \
  +int_player_advanced_stats__deduped \
  +fct_player_season_stats \
  +fct_player_advanced_stats
```

**Checagens esperadas:**
- `stg_bbr__nba_careers`: `unique`/`not_null` em `bbr_id` passam (confirma 1 linha/jogador).
- `int_games__from_gamelogs`: `unique_combination_of_columns` passa (sem doubleheader).
- `int_player_advanced_stats__deduped`: `unique_combination` passa (dedup funcionou).
- `team_key` relationships passam (com o `where` ignorando os TOT null).

Se algum falhar, é **achado real** — investigar (não relaxar o teste sem entender).

> Lembrar de manter o CI verde: se mudar schema de seed, regerar amostras com
> `python ci/make_sample_seeds.py` (ver ESTADO.md).
