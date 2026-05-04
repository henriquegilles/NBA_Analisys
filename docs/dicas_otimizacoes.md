# Dicas e Otimizações — Pós-Pipeline

> Análise dos resultados dos testes e do estado atual do projeto.
> Itens ordenados por impacto — do mais crítico ao cosmético.

---

## 🔴 Crítico — Resolver antes da próxima execução real

### 1. Substituir `bbr_id` sintéticos pelos reais

**Situação atual:**
Os `bbr_id` em `players.csv` foram gerados por algoritmo (convenção BBR aproximada).
Eles não coincidem com os IDs reais do Basketball Reference.

**Impacto:**
- O `fct_player_game_log` usa `bbr_id` para JOIN com `dim_player`. Quando o scraper de
  gamelogs rodar, os IDs dos logs **não vão casar** com os sintéticos — todos os JOINs
  retornarão NULL.
- A `player_key` (surrogate key baseada em `bbr_id`) será diferente da gerada com IDs reais,
  quebrando qualquer análise histórica acumulada.

**Ação:**
Quando o Cloudflare do BBR liberar:
```bash
cd src/scraping && python players.py
dbt seed --profiles-dir .dbt --full-refresh --select players
dbt run --profiles-dir .dbt --full-refresh
dbt test --profiles-dir .dbt
```

---

### 2. Adicionar detecção de Cloudflare no `common/browser.py`

**Situação atual:**
O scraper não detecta o challenge page e retorna erro genérico de parsing ("Table not found").

**Ação recomendada — adicionar ao `fetch_page()` ou `build_driver()`:**
```python
def _check_cloudflare(driver) -> bool:
    """Returns True if BBR served a Cloudflare challenge page."""
    title = BeautifulSoup(driver.page_source, "lxml").title
    return title is not None and ("momento" in title.text.lower() or "just a moment" in title.text.lower())

# Usar em cada scraper após fetch:
if _check_cloudflare(driver):
    driver.quit()
    raise RuntimeError("BBR retornou challenge page (Cloudflare). Tente novamente em alguns minutos.")
```

Isso substitui o erro confuso `ValueError: Table #per_game_stats not found` por uma mensagem
clara e acionável.

---

## 🟡 Importante — Resolver na próxima sprint

### 3. Corrigir warning de precisão no `dim_team`

**Situação atual:**
```
Detected columns with numeric type and unspecified precision/scale, this can lead
to unintended rounding: ['win_loss_pct']
```

O campo `win_loss_pct` é definido como `numeric` no contrato do YAML, mas a tabela física
usa `numeric` sem precisão — o PostgreSQL pode arredondar silenciosamente para 0 casas decimais.

**Ação em `models/staging/bbr/stg_bbr__teams.sql` — já tem precisão:**
```sql
nullif(trim("wl_pct"::text),'')::numeric(5,3) as win_loss_pct
```
A origem já tem `numeric(5,3)`. O warning vem do `enforce_contract` em `_marts__models.yml`.
Atualizar o data_type no YAML:
```yaml
- name: win_loss_pct
  data_type: numeric(5,3)   # ← especificar precisão
```

---

### 4. ✅ Scraper de gamelogs executado

**Resolvido.** `player_gamelogs.py` rodou e gerou 26.611 linhas (518 jogadores, temporada 2025-26).
Pipeline: 20/20 modelos, 90/90 testes passando.

Tabelas ainda sem dados reais (scrapers não executados):

| Seed | Depende de |
|---|---|
| `contracts.csv` | nenhum |
| `players_advanced_stats.csv` | nenhum |
| `draft.csv` | nenhum |

---

### 5. Snapshots — Rodar pela primeira vez

**Situação atual:**
Os snapshots `player_contract_snapshot` e `player_roster_snapshot` foram criados mas nunca
rodaram. Não há histórico de mudanças capturado.

**Ação:**
```bash
dbt snapshot --profiles-dir .dbt
```
Agendar para rodar junto com o `dbt run` toda segunda-feira (já no schedule do Dagster).
A primeira execução captura o estado atual como linha inicial de cada SCD.

---

### 6. ✅ Adicionar `--season` aos scrapers que ainda não suportam

**Resolvido.** `player_gamelogs.py` e `advanced_stats.py` agora aceitam `--season 2025-26`
via `argparse`. O Dagster passa o `partition_key` como `--season` e os scripts convertem
corretamente para o formato interno (`YYYY-YY` → ano final inteiro).

---

## 🟢 Melhorias — Boas práticas para implementar gradualmente

### 7. Adicionar `dbt compile` ao CI antes de `dbt run`

**Situação atual:**
O CI roda `dbt seed → dbt run → dbt test`. Um erro de sintaxe SQL só aparece no `dbt run`.

**Melhoria:**
```yaml
# .github/workflows/ci.yml
- run: dbt compile --profiles-dir .dbt  # falha rápido em erros de Jinja/SQL
- run: dbt seed --profiles-dir .dbt
- run: dbt run --profiles-dir .dbt
- run: dbt test --profiles-dir .dbt
```

---

### 8. ✅ Remover o macro customizado `generate_surrogate_key`

**Resolvido.** Nenhum modelo SQL referenciava o macro — foi deletado diretamente.
`macros/generate_surrogate_key.sql` removido; todos os modelos já usam `generate_id()`.

---

### 9. ✅ Adicionar testes singulares de negócio em `tests/`

**Resolvido.** Três testes criados em `tests/` — falham se retornarem linhas:

| Arquivo | Regra verificada |
|---|---|
| `assert_pts_non_negative.sql` | `pts >= 0` em `fct_player_game_log` |
| `assert_minutes_valid.sql` | `0 ≤ minutes_played ≤ 60` (cobre até 3 prorrogações) |
| `assert_win_shares_reasonable.sql` | `win_shares ≤ 25` por temporada em `fct_player_advanced_stats` |

Todos passaram na primeira execução (`dbt test --select assert_*`).

---

### 10. Adicionar `dbt source freshness` quando o pipeline for regular

**Situação atual:**
`_bbr__sources.yml` não tem bloco `freshness:`. Não há SLA monitorado — se o scraper falhar
por 2 semanas, ninguém sabe até olhar manualmente os dados.

**Melhoria:**
```yaml
sources:
  - name: analytics_raw
    freshness:
      warn_after: {count: 8, period: day}
      error_after: {count: 14, period: day}
    loaded_at_field: _dbt_loaded_at
```
Isso requer adicionar `_dbt_loaded_at TIMESTAMP DEFAULT now()` como coluna nas seeds, ou
usar uma tabela de controle de carga.

---

### 10. Limitar concorrência do Dagster para scrapers Selenium

**Situação atual:**
O `nba_pipeline_job` pode disparar `scrape_players`, `scrape_stats`, `scrape_teams` e
`scrape_contracts` em paralelo (sem dependência entre eles no DAG). Isso abre múltiplas
sessões Chrome simultâneas, aumentando o risco de rate limit do BBR.

**Melhoria em `orchestration/definitions.py`:**
```python
nba_pipeline_job = define_asset_job(
    name="nba_pipeline",
    config={"execution": {"config": {"multiprocess": {"max_concurrent": 1}}}},
    ...
)
```
Com `max_concurrent=1`, os scrapers rodam sequencialmente — mais lento, mas muito menos
chance de bloqueio por rate limit.

---

### 11. Considerar `materialized: incremental` para `fct_player_game_log`

**Situação atual:**
`fct_player_game_log` é `materialized: table`. A cada `dbt run`, todos os registros são
reconstruídos do zero. Com dados de uma temporada (~25.000 linhas), isso é aceitável.
Com múltiplas temporadas históricas, o custo cresce linearmente.

**Melhoria futura:**
```sql
{{ config(
    materialized='incremental',
    unique_key=['bbr_id', 'game_date'],
    on_schema_change='sync_all_columns'
) }}

{% if is_incremental() %}
  where game_date > (select max(game_date) - interval '3 days' from {{ this }})
{% endif %}
```
O lookback de 3 dias garante que correções tardias do BBR sejam aplicadas nos últimos jogos.

---

## Resumo de prioridades pós-pipeline

| # | Item | Impacto | Esforço |
|---|---|---|---|
| 1 | Substituir bbr_id sintéticos | 🔴 FK chain quebrada | Rodar scraper |
| 2 | Detectar Cloudflare no browser.py | 🔴 Erros opacos | 10 min |
| 3 | Corrigir precision `win_loss_pct` | 🟡 Warning silencioso | 5 min |
| 4 | ~~Scraper de gamelogs executado~~ | ✅ 26.611 linhas, 90/90 testes | — |
| 5 | Rodar `dbt snapshot` pela primeira vez | 🟡 Sem histórico SCD | 2 min |
| 6 | Adicionar `--season` aos scrapers | 🟡 Particionamento Dagster inoperante | 30 min |
| 7 | `dbt compile` no CI | 🟢 Feedback mais rápido | 5 min |
| 8 | ~~Remover macro wrapper~~ | ✅ Feito | — |
| 9 | ~~Testes singulares de negócio~~ | ✅ Feito | — |
| 13 | ~~Surrogate keys como varchar MD5~~ | ✅ Colisões eliminadas, 90/90 testes | — |
| 10 | `dbt source freshness` | 🟢 Observabilidade | 30 min |
| 11 | Concorrência Dagster `max_concurrent=1` | 🟢 Reduz rate limit | 5 min |
| 12 | Incremental para `fct_player_game_log` | 🟢 Escala histórica | 2h |
