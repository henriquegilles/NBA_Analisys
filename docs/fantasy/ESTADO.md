# Camada Fantasy — Estado e Retomada

> **COMECE POR AQUI ao retomar o Domínio B.** Doc de handoff: o que existe, o que
> falta, e os comandos exatos pra continuar. Os detalhes de *design* ficam nos
> docs numerados (00–04); aqui é só **estado acionável**.
>
> Última atualização: **2026-06-21** (seção Git: backbone mergeado no master).

---

## TL;DR

Domínio A (valoração da minha franquia) está **construído e validado**. Domínio B
(scouting de draft) está **funcionando de ponta a ponta**: seed college → staging
→ perfil do prospecto → comps (k-NN) → desfecho NBA → **projeção** de prospecto
novo pela média dos comps. Tudo no master, validado ao vivo. A 1ª versão do
desfecho NBA usa o seed `draft` que já existia (médias de carreira pts/reb/ast +
WS/BPM/VORP — D-29); a única melhoria pendente é a **carreira NBA 6-cat completa**
(falta stocks/3PM/TOV de carreira), que exigiria um scraper de páginas de jogador.

---

## Status por domínio

| Domínio | Estado | Detalhe |
|---|---|---|
| **A — minha franquia** | ✅ construído + validado (master) | `int_player__fantasy_categories`, `fct_player_fantasy_value_season`/`_recent`. 86 testes verdes (2026-06-19). |
| **B — scouting (pipeline completo)** | ✅ construído + validado ao vivo | seed → staging → `int_prospect__college_stats` → `int_prospect__comps` → `int_prospect__nba_bridge` → `fct_college_to_nba_outcomes` → `fct_prospect_scouting`. Todos com testes verdes. |
| **B — desfecho NBA 6-cat completo** | 🟡 melhoria futura | 1ª versão usa o seed `draft` (3 cats + WS/BPM/VORP — D-29). Para as 6 categorias de carreira (faltam stocks/3PM/TOV) seria preciso um scraper de páginas de jogador da NBA. |

---

## Domínio B — o que existe (mapa de arquivos)

| Arquivo | Papel |
|---|---|
| `src/scraping/college.py` | Scraper Selenium do College Basketball Reference, por **escola × temporada** (D-27). Parse por `data-stat`, merge das 3 tabelas por `cbb_id`. |
| `seeds/college_player_seasons.csv` | Saída do scraper (gitignorado, **regenerável**). 841 player-seasons. Grão: jogador × temporada college. |
| `models/staging/cbb/stg_cbb__player_season.sql` | Staging: limpa/tipa o seed. Mantém `class` cru (ordinal vai no intermediate). |
| `models/staging/cbb/_cbb__sources.yml` | Schema + testes (`not_null`, `accepted_values` em `class`, unicidade `cbb_id × season`). |
| `models/intermediate/int_prospect__college_stats.sql` | Perfil do prospecto: 6 cat por-40 + `class_rank` (D-26) + arquétipo G/F/C (D-28) + trajetória padronizada (D-24). Piso de minutos 200 (knob `min_minutes`). 530 linhas. |
| `models/intermediate/int_prospect__comps.sql` | k=8 vizinhos por distância euclidiana sobre features padronizadas (D-21), mesmo arquétipo c/ fallback. 315 prospectos × 8. |
| `models/intermediate/int_prospect__nba_bridge.sql` | Ponte college→NBA (D-09): nome + janela de ano do draft. Desfecho de carreira do seed `draft` (D-29). |
| `models/marts/fantasy/fct_college_to_nba_outcomes.sql` | Espinha dorsal: perfil college + desfecho NBA de carreira. 96 prospectos históricos. |
| `models/marts/fantasy/fct_prospect_scouting.sql` | **Produto**: projeção do prospecto = média dos desfechos dos comps. 243 prospectos. |
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

1. ✅ ~~Pipeline college→NBA completo~~ — seed → staging → perfil → comps → ponte → outcomes → projeção. Feito e validado 2026-06-19.
2. **Melhoria — carreira NBA 6-cat completa:** scraper de páginas de jogador da NBA (todas as temporadas) p/ trazer stocks/3PM/TOV de carreira e fechar as 6 categorias do desfecho. Hoje são 3 cats + WS/BPM/VORP (D-29).
3. **Seed de overrides `college_nba_id_overrides`** (D-09): resolver os xarás ambíguos da ponte (n_matches>1).
4. **Escalar o backbone:** mais escolas/temporadas no `college.py` → mais comps e mais outcomes históricos.

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

- **Mergeado no `master`** (HEAD `81f9e87d`, 2026-06-20). O backbone college→NBA
  veio nos commits `c56f6b30` (college_stats) → `ced2a498` (comps) →
  `af58bd1b` (ponte + outcomes + projeção). A branch `feat/cbb-college-scouting`
  já cumpriu o papel.
- Seed fica **fora do commit** (gitignorado, regenerável) — convenção do projeto.
