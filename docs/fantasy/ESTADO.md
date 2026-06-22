# Camada Fantasy — Estado e Retomada

> **COMECE POR AQUI ao retomar o Domínio B.** Doc de handoff: o que existe, o que
> falta, e os comandos exatos pra continuar. Os detalhes de *design* ficam nos
> docs numerados (00–04); aqui é só **estado acionável**.
>
> Última atualização: **2026-06-21** (D-30 6-cat + D-09 overrides + backbone
> escalado p/ 18 escolas × 15 temporadas; tudo raspado/validado ao vivo, no master).

---

## TL;DR

Domínio A (valoração da minha franquia) está **construído e validado**. Domínio B
(scouting de draft) está **funcionando de ponta a ponta**: seed college → staging
→ perfil do prospecto → comps (k-NN) → desfecho NBA → **projeção** de prospecto
novo pela média dos comps. Tudo no master, validado ao vivo.

**6-cat completa (D-30, 2026-06-21):** o desfecho NBA agora fecha as 6 categorias
da Bandeja de 3 — pts/reb/ast vêm do seed `draft` (D-29) e **stl/blk (→stocks),
3PM e TOV** vêm de `nba_careers.py` (linha *Career* da página de cada jogador),
juntos pelo **slug NBA `bbr_id`** que o `draft.py` passou a capturar. Código + SQL
mergeados, e o **scrape foi executado e validado ao vivo** (2026-06-21): draft
2553 picks (1986–2025, `bbr_id` 100%) + **279 carreiras 6-cat** (backbone escalado
p/ 18 escolas × 15 temporadas em 2026-06-21); `dbt build` PASS=40 com as 6 cats
fluindo (Outcomes 279, Scouting 742). Ex.: Shai
Gilgeous-Alexander 25.3 pts / 2.2 stocks / 1.4 3PM / 2.3 tov.

> ⚠️ **Os seeds são gitignored/regeneráveis** — o repo NÃO carrega esses dados.
> Num clone novo (ou se zerar o banco) é preciso **re-rodar o scrape** (passos 5-6
> em "Como retomar"). Na máquina onde foi executado, já está populado.

---

## Status por domínio

| Domínio | Estado | Detalhe |
|---|---|---|
| **A — minha franquia** | ✅ construído + validado (master) | `int_player__fantasy_categories`, `fct_player_fantasy_value_season`/`_recent`. 86 testes verdes (2026-06-19). |
| **B — scouting (pipeline completo)** | ✅ construído + validado ao vivo | seed → staging → `int_prospect__college_stats` → `int_prospect__comps` → `int_prospect__nba_bridge` → `fct_college_to_nba_outcomes` → `fct_prospect_scouting`. Todos com testes verdes. |
| **B — desfecho NBA 6-cat completo** | ✅ construído + validado ao vivo (2026-06-21) | `nba_careers.py` + `stg_bbr__nba_careers` + ponte/outcomes/scouting trazem stocks/3PM/TOV via slug `bbr_id` (D-30). Scrape executado (escalado 18 escolas × 15 temporadas, 2026-06-21): 279 carreiras, 6 cats fluindo (Outcomes 279, Scouting 742), `dbt build` PASS=40. **Seeds gitignored → re-rodar o scrape em clone novo.** |

---

## Domínio B — o que existe (mapa de arquivos)

| Arquivo | Papel |
|---|---|
| `src/scraping/college.py` | Scraper Selenium do College Basketball Reference, por **escola × temporada** (D-27). Parse por `data-stat`, merge das 3 tabelas por `cbb_id`. |
| `seeds/college_player_seasons.csv` | Saída do scraper (gitignorado, **regenerável**). 3733 player-seasons (18 escolas × 15 temporadas, escalado 2026-06-21). Grão: jogador × temporada college. |
| `models/staging/cbb/stg_cbb__player_season.sql` | Staging: limpa/tipa o seed. Mantém `class` cru (ordinal vai no intermediate). |
| `models/staging/cbb/_cbb__sources.yml` | Schema + testes (`not_null`, `accepted_values` em `class`, unicidade `cbb_id × season`). |
| `models/intermediate/int_prospect__college_stats.sql` | Perfil do prospecto: 6 cat por-40 + `class_rank` (D-26) + arquétipo G/F/C (D-28) + trajetória padronizada (D-24). Piso de minutos 200 (knob `min_minutes`). 530 linhas. |
| `models/intermediate/int_prospect__comps.sql` | k=8 vizinhos por distância euclidiana sobre features padronizadas (D-21), mesmo arquétipo c/ fallback. 315 prospectos × 8. |
| `src/scraping/draft.py` | Draft (40 temporadas). **Reescrito p/ parse por `data-stat`** (a BBR mudou o superheader e quebrou o `read_html` — runbook #25); **captura `bbr_id`** (slug NBA do href) — chave da carreira (D-30). |
| `src/scraping/nba_careers.py` | Scraper da **carreira NBA 6-cat** (D-30): lê draft+college, calcula o conjunto-alvo (matches da ponte) em pandas, raspa a linha *Career* da página de cada jogador. `--max-pages` p/ smoke, `--all` p/ todos os draftados. |
| `seeds/nba_player_careers.csv` | Saída do scraper (gitignorado, regenerável). Grão: 1 linha por jogador NBA. pg_stl/blk/fg3/tov de carreira. |
| `models/staging/bbr/stg_bbr__nba_careers.sql` | Staging: limpa/tipa o seed de carreiras. |
| `seeds/college_nba_id_overrides.csv` | **Seed manual VERSIONADO** (D-09): `cbb_id → slug NBA canônico` p/ xarás que a janela de ano não desambigua. Hoje: 1 linha (Justin Jackson). |
| `models/intermediate/int_prospect__nba_bridge.sql` | Ponte college→NBA: nome + janela de ano do draft + **override D-09** (`n_matches` recomputado depois). pts/reb/ast do `draft` (D-29) + **stl/blk/3PM/TOV via LEFT JOIN da carreira pelo slug `bbr_id`** (D-30). |
| `models/marts/fantasy/fct_college_to_nba_outcomes.sql` | Espinha dorsal: perfil college + desfecho NBA de carreira. 96 prospectos históricos. |
| `models/marts/fantasy/fct_prospect_scouting.sql` | **Produto**: projeção do prospecto = média dos desfechos dos comps. 742 prospectos (escalado 2026-06-21). |
| `docs/fantasy/03_dominio_b_scouting.md` | Design completo + **§7 reconhecimento** (mapa de campos do CBB Reference). |

### Escopo atual do scrape (e como expandir)
Definido em **constantes no topo de `src/scraping/college.py`**:
- `SCHOOLS` = 18 escolas (núcleo: duke, kentucky, kansas, north-carolina, ucla, gonzaga; expansão 2026-06-21: arizona, villanova, michigan-state, texas, florida, auburn, southern-california, tennessee, alabama, baylor, arkansas, connecticut).
- `SEASONS` = `2011..2025` (temporadas 2010-11 a 2024-25; o ano é o **final**).
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

1. ✅ ~~Pipeline college→NBA completo~~ — seed → staging → perfil → comps → ponte → outcomes → projeção. Feito e validado 2026-06-19.
2. ✅ ~~Carreira NBA 6-cat completa~~ — `nba_careers.py` + staging + ponte/outcomes/scouting (D-30). Scrape executado e validado ao vivo 2026-06-21 (279 carreiras, 6 cats fluindo, `dbt build` PASS=40). Em clone novo, re-rodar o scrape (passos 5-6 em "Como retomar").
3. ✅ ~~Seed de overrides `college_nba_id_overrides`~~ (D-09): xará Justin Jackson (UNC 2017 vs. Maryland 2018) resolvido → `jacksju01`. 0 ambíguos restantes; outcomes 96→97. Validado 2026-06-21.
4. ✅ ~~Escalar o backbone~~ — feito 2026-06-21: 6→18 escolas, 10→15 temporadas (`college.py`). 3733 player-seasons, 279 outcomes, 742 projeções. Escalar mais é só editar `SCHOOLS`/`SEASONS` e re-rodar college + nba_careers.

> **CI verde (2026-06-19):** o CI agora roda dbt de ponta a ponta com amostras
> consistentes em `ci/sample_seeds/` (geradas por `ci/make_sample_seeds.py`;
> regenerar se mudar schema de seed). De passagem, foram corrigidos modelos
> defasados pré-existentes: `stg_bbr__draft` (round derivado do pick + filtro de
> linhas-lixo), `stg_bbr__contracts` (salários 2025-26..2030-31) e
> `dim_player_contract` (dedup).

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

# 5. CARREIRA NBA 6-cat (D-30) — executar o scrape ao vivo:
cd src/scraping
python draft.py            # re-raspa o draft p/ capturar o slug bbr_id (~2-3 min)
python nba_careers.py      # raspa a carreira só dos ~96 matches da ponte (~5 min)
#   smoke test: python nba_careers.py --max-pages 4
cd ../..

# 6. Rebuild com as carreiras + regenerar amostras do CI
dbt build --profiles-dir .dbt --full-refresh --select +fct_prospect_scouting stg_bbr__draft
python ci/make_sample_seeds.py   # captura draft.bbr_id + nba_player_careers reais
```

> **Importante (D-30):** o `nba_careers.py` depende de o `draft.csv` já ter a
> coluna `bbr_id` — por isso rode `draft.py` ANTES. Como o schema do `draft`
> mudou (coluna nova), o primeiro `dbt seed`/`build` precisa de `--full-refresh`
> (runbook #3/#9).

---

## Dependências de dados (status)

| Dependência | Status |
|---|---|
| Histórico **college** multi-temporada | ✅ coletado: 18 escolas × 15 temporadas, 3733 player-seasons (escalado 2026-06-21) |
| **Carreiras NBA** (desfecho 6-cat, D-30) | ✅ **resolvido e raspado** via `nba_careers.py` (279 carreiras, 2026-06-21). Seeds gitignored → re-rodar em clone novo. |
| Fonte do meu roster (Domínio A fase 2) | 🔴 site Ciengos congelado → provável seed manual |
| "Classe atual" de draft | 🔴 provável seed manual |

---

## Decisões-chave deste bloco (log completo no [00_README](00_README.md))

- **D-26** — `class` (FR=1…SR=4) como **proxy de idade** (CBB Reference não publica idade).
- **D-27** — coletar college **por escola × temporada** (pega todos + SOS numa requisição).
- Reconhecimento detalhado dos campos do CBB Reference: [03_dominio_b_scouting §7](03_dominio_b_scouting.md#7-reconhecimento-do-cbb-reference-2026-06-19).

## Git

- **Mergeado no `master`** (HEAD `81f9e87d`, 2026-06-20). O backbone college→NBA
  veio nos commits `c56f6b30` (college_stats) → `ced2a498` (comps) →
  `af58bd1b` (ponte + outcomes + projeção). A branch `feat/cbb-college-scouting`
  já cumpriu o papel.
- Seed fica **fora do commit** (gitignorado, regenerável) — convenção do projeto.
