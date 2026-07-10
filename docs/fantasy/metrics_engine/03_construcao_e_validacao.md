# Fase 3-5 — Construção, GitHub e Protótipo (+ validação)

> Fecha o ciclo ponta a ponta: o que foi construído, como validar quando o DB subir,
> e os erros pegos/corrigidos durante (revisão contínua + preditiva).

---

## Fase 3 — Construção (views dbt)

Criado (materializado como **view** = métrica "em tempo real", recalcula a cada query):

| Camada | Arquivo | Papel |
|---|---|---|
| macro | `macros/norm_name.sql` | normalização de nome (join sem bug de acento) |
| staging | `models/staging/fantasy/stg_fantasy__{rosters,franchises,standings,draft_class}.sql` | tipa, normaliza, $ em $M, dedup |
| intermediate | `models/intermediate/int_fantasy__roster_valuation.sql` | roster × valoração 7-cat + VA punt-TOV |
| mart | `models/marts/fantasy/metrics/vw_my_roster_metrics.sql` | meu time por categoria |
| mart | `.../fct_league_category_strength.sql` | 24 times × categoria (rival scan) |
| mart | `.../fct_fa_targets.sql` | FA disponíveis + fit + match |
| mart | `.../fct_draft_board.sql` | prospecto × projeção × oportunidade |
| mart | `.../fct_team_cap.sql` | cap por franquia |
| seed | `seeds/nba_landing_spots.csv` | time NBA **final** + tier de oportunidade (corrige draft-night) |
| testes | `.../_metrics__models.yml` | guardrails (unidade, unicidade, confiança) |

## Fase 4 — GitHub / portfólio

- `README.md`: nova seção **🏀 Fantasy Decision Engine** + at-a-glance atualizado.
- `LICENSE` (MIT) + badge.
- `.gitignore`: `nba_landing_spots.csv` versionado (seed manual, como `team_info`).

## Fase 5 — Protótipo (FA + Draft)

- `dashboard/fantasy_engine.py` — **engine reproduzível** (consolida os scripts pandas
  ad-hoc de `/tmp` num módulo versionado; lê seeds, **sem DB**).
- `dashboard/fantasy_gm_tool.py` — **app Streamlit** com abas Meu time · FA · Draft · Liga · Cap.
  - Rodar: `streamlit run dashboard/fantasy_gm_tool.py`
  - Atualizar dado pós-trocas: `python src/scraping/fantasy_gm.py` (re-scrape).

---

## Erros pegos e corrigidos (revisão durante)

| Erro | Onde | Correção |
|---|---|---|
| Fan-out de merge inflou o cap ($222M) | engine | dedup de stats/rosters por chave (max jogos) |
| `norm()` mantinha espaços → landing spots não casava | engine | regex remove todo não-alfanumérico (igual à macro dbt) |
| `nullif(salario,'')` quebraria (numeric vs texto) | staging | `::text` antes do nullif (robusto ao tipo inferido) |
| Alias de `z_reb` com lateral join inválido | fct_fa_targets | `z_trb as z_reb` direto |

## Validação pendente (quando subir o Docker)

O engine + app foram **testados ao vivo** (leem seeds). As **views dbt não** (DB caiu).
Passos pra validar:

```bash
# 1. subir o banco
docker compose up -d postgres        # (ou reabrir Docker Desktop + WSL integration)

# 2. seed + build da camada fantasy
source .venv/bin/activate
dbt seed --profiles-dir .dbt --select nba_landing_spots
dbt run  --profiles-dir .dbt --select stg_fantasy__* int_fantasy__* \
         vw_my_roster_metrics fct_league_category_strength fct_fa_targets \
         fct_draft_board fct_team_cap

# 3. testes (guardrails)
dbt test --profiles-dir .dbt --select fct_team_cap fct_fa_targets fct_draft_board
```

**Riscos preditivos a checar no primeiro run:**
- Seeds fantasy podem precisar de `column_types` no `seeds/schema.yml` se a inferência
  divergir (salários/ids). Casts `::text` já mitigam.
- `fct_draft_board` só cobre prospectos com projeção em `fct_prospect_scouting` (75/94) —
  os sem college ficam de fora (esperado, declarado).

## Estado final — end-to-end

```
FantasyGM API ─(fantasy_gm.py)→ seeds ─(dbt: stg→int→marts/views)→ métricas em tempo real
                                  │                                        │
                                  └────(fantasy_engine.py)──→ Streamlit GM Tool (FA/Draft)
```

O propósito (usando o Lobos): **de "meio de tabela, fundo em 3 categorias" a contender**
— agora com a decisão **reproduzível e visual**, não mais em scripts soltos.
