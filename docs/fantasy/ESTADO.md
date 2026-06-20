# Camada Fantasy — Estado e Retomada

> **COMECE POR AQUI ao retomar o Domínio B.** Doc de handoff: o que existe, o que
> falta, e os comandos exatos pra continuar. Os detalhes de *design* ficam nos
> docs numerados (00–04); aqui é só **estado acionável**.
>
> Última atualização: **2026-06-19**.

---

## TL;DR

Domínio A (valoração da minha franquia) está **construído e validado**. Domínio B
(scouting de draft) teve o **lado college destravado**: scraper NCAA + seed (841
linhas) + staging existem e passaram validação *offline*. **Dois bloqueios reais
seguem abertos:** (1) o `dbt run/test` ao vivo nunca rodou porque o Postgres não
sobe nesta máquina sem ação manual (Docker/WSL — ver runbook #23); (2) o desfecho
NBA do backbone exige **carreiras NBA multi-temporada**, que ainda não coletamos.

---

## Status por domínio

| Domínio | Estado | Detalhe |
|---|---|---|
| **A — minha franquia** | ✅ construído + validado (master) | `int_player__fantasy_categories`, `fct_player_fantasy_value_season`/`_recent`. 86 testes verdes (2026-06-19). |
| **B — scouting (lado college)** | ✅ construído + validado ao vivo | scraper + seed + staging na branch `feat/cbb-college-scouting`. `dbt run` PASS=1, `dbt test` PASS=5 (2026-06-19). |
| **B — scouting (desfecho NBA)** | 🔴 bloqueado em dados | precisa de carreiras NBA multi-temporada (D-11 = média de carreira). Scrapers NBA atuais só pegam a temporada corrente. |

---

## Domínio B — o que existe (mapa de arquivos)

| Arquivo | Papel |
|---|---|
| `src/scraping/college.py` | Scraper Selenium do College Basketball Reference, por **escola × temporada** (D-27). Parse por `data-stat`, merge das 3 tabelas por `cbb_id`. |
| `seeds/college_player_seasons.csv` | Saída do scraper (gitignorado, **regenerável**). 841 player-seasons. Grão: jogador × temporada college. |
| `models/staging/cbb/stg_cbb__player_season.sql` | Staging: limpa/tipa o seed. Mantém `class` cru (ordinal vai no intermediate). |
| `models/staging/cbb/_cbb__sources.yml` | Schema + testes (`not_null`, `accepted_values` em `class`, unicidade `cbb_id × season`). |
| `docs/fantasy/03_dominio_b_scouting.md` | Design completo + **§7 reconhecimento** (mapa de campos do CBB Reference). |

### Escopo atual do scrape (e como expandir)
Definido em **constantes no topo de `src/scraping/college.py`**:
- `SCHOOLS` = `duke, kentucky, kansas, north-carolina, ucla, gonzaga` (6 escolas que alimentam a NBA).
- `SEASONS` = `2016..2025` (temporadas 2015-16 a 2024-25; o ano é o **final**).
- **Para escalar o backbone:** edite essas duas listas e rode de novo. Slug da escola = como aparece na URL `/cbb/schools/<slug>/men/<ano>.html`. Smoke test: `python college.py --max-pages 4`.

### Validações já feitas (2026-06-19)
| Validação | Como repetir | Resultado |
|---|---|---|
| `dbt parse` (sintaxe/refs/yml) | `dbt parse --profiles-dir .dbt` | ✅ |
| Qualidade do seed (pandas) | ler `seeds/college_player_seasons.csv` | 0 dup `cbb_id×season`; `class ∈ {FR,SO,JR,SR}`; 0 nulls nas chaves |
| `dbt run` + `dbt test` AO VIVO | `dbt run/test --select stg_cbb__player_season` | ✅ run PASS=1, test PASS=5 (2026-06-19); query live confirmou `rsci_rank` extraído e per-40 ok |

> **Achado a tratar no intermediate:** walk-ons/redshirts com ~0 min geram per-40/TS%/usage extremos ou nulos (TS% até 1.5). Aplicar **piso de minutos** (análogo ao D-15 do Domínio A) antes de comps/distância.

---

## Próximos passos (ordem sugerida)

1. ✅ ~~Subir o DB e rodar a validação ao vivo do staging~~ — feito 2026-06-19 (run PASS=1, test PASS=5).
2. **Modelar `int_prospect__college_stats`** ← **próximo passo**: ordinal de `class` (D-26, FR=1…SR=4), arquétipo (D-23), trajetória (D-24), **piso de minutos**, contexto (TS%, usage, SOS).
3. **Coletar carreiras NBA multi-temporada** (gargalo do backbone) → permite `fct_college_to_nba_outcomes` (perfil college + desfecho NBA D-11).
4. **`bridge_college_to_nba`** (nome + seed de overrides) e **`fct_prospect_scouting`** (comps por distância euclidiana, k≈8–10 — D-21).

---

## Como retomar (comandos)

```bash
# 1. Ambiente
source .venv/bin/activate

# 2. Subir o Postgres (NÃO é serviço local nesta máquina — é Docker).
#    Requer Docker Desktop com WSL Integration ligada. Ver runbook #23.
docker compose up -d postgres

# 3. (Opcional) Regerar o seed college — ~12 min de Selenium
cd src/scraping && python college.py && cd ../..

# 4. Validar o staging cbb ao vivo
dbt seed --profiles-dir .dbt --select college_player_seasons
dbt run  --profiles-dir .dbt --select stg_cbb__player_season
dbt test --profiles-dir .dbt --select stg_cbb__player_season
```

---

## Dependências de dados (status)

| Dependência | Status |
|---|---|
| Histórico **college** multi-temporada | ✅ mapeado e coletado (slice de 6 escolas; escalável) |
| **Carreiras NBA** multi-temporada (desfecho D-11) | 🔴 **aberto — gargalo do backbone.** Scrapers NBA atuais só pegam a temporada corrente. |
| Fonte do meu roster (Domínio A fase 2) | 🔴 site Ciengos congelado → provável seed manual |
| "Classe atual" de draft | 🔴 provável seed manual |

---

## Decisões-chave deste bloco (log completo no [00_README](00_README.md))

- **D-26** — `class` (FR=1…SR=4) como **proxy de idade** (CBB Reference não publica idade).
- **D-27** — coletar college **por escola × temporada** (pega todos + SOS numa requisição).
- Reconhecimento detalhado dos campos do CBB Reference: [03_dominio_b_scouting §7](03_dominio_b_scouting.md#7-reconhecimento-do-cbb-reference-2026-06-19).

## Git

- Branch: **`feat/cbb-college-scouting`** · commit `97622637` · **não mergeado no master**.
- Seed fica **fora do commit** (gitignorado, regenerável) — convenção do projeto.
