# Camada Fantasy — Domínio B: Scouting de Draft (detalhado)

> **Status:** rascunho de design (ideação). Nenhum modelo criado.
> **Pré-requisitos:** [01_escopo](01_escopo_camada_fantasy.md), [02_modelo_conceitual](02_modelo_conceitual.md).

---

## 1. O problema central

Estatística de college **não prevê NBA diretamente**, por três distorções:
- **Minutos:** estrelas de college jogam 35+ min; calouros NBA jogam menos.
- **Ritmo (pace):** jogo de college tem ritmo/posses diferentes.
- **Nível de competição:** D1 (e suas conferências) ≠ NBA.

Por isso, antes de qualquer comparação, normalizamos e contextualizamos.

## 2. Como a comparação histórica vira projeção

Para cada prospecto **passado**: `(perfil em college) → (desfecho NBA)`.
Para um prospecto da **classe atual**: achamos os históricos de perfil mais parecido (**comps**, dentro da mesma posição/arquétipo) e olhamos como renderam → projeção.

---

## 3. Decisões deste domínio (decision log)

| ID | Decisão | Racional |
|---|---|---|
| **D-10** | Normalizar estatísticas de college para **por-40-minutos** | Remove a distorção de minutos; padrão de análise de prospecto; simples |
| **D-11** | Desfecho NBA medido = **carreira inteira** (média) | Escolha do Henri — estável. *Caveat aceito: dilui com anos de declínio; revisitar se necessário* |
| **D-12** | Prospecto representado pela **última temporada de college + trajetória** (evolução ano a ano) | Reflete o jogador mais atual e captura sinal de desenvolvimento |
| **D-13** | Comps restritos à **mesma posição/arquétipo** | Comps mais interpretáveis e justos (armador com armadores) |
| **D-26** | **`class` (Fr=1…Sr=4) como proxy de idade** em contexto E na distância dos comps | Reconhecimento confirmou que o CBB Reference não traz idade; `class` é o único sinal de senioridade, sempre disponível e ordinal. Substitui "idade" em D-21 e no contexto. *Caveat: granularidade menor que idade real; aceito.* |
| **D-27** | **Coletar histórico college por escola × temporada** (não página-por-jogador) | A página escola-temporada traz todos os ~14 jogadores (per-40 + advanced + roster) E o SOS do time numa requisição; muito menos requests pra cobrir todo mundo. Carreira por-jogador é remontada por nome depois. |

**Contexto incluído por padrão:** **senioridade** (`class` Fr/So/Jr/Sr — proxy de idade, ver D-26), eficiência (TS%), uso (usage), força de calendário (SOS), posição.

> **Limitação estrutural:** Plus/Minus não existe em college → scouting trabalha com **6 categorias** (pts, reb, ast, STOCKS, 3PM, TOV), não 7.

> **Limitação estrutural 2:** o CBB Reference **não publica idade/data de nascimento** de jogadores de college (reconhecimento 2026-06-19). Usamos `class` (Fr/So/Jr/Sr) como proxy de senioridade (D-26).

---

## 4. Pipeline detalhado (Fase 1 — NCAA)

```
scrape College Basketball Reference (NCAA, MULTI-temporada)
   │
   ▼
stg_cbb__player_season         (grão: jogador × temporada college; stats brutos limpos)
   │
   ▼
int_prospect__college_stats    (grão: jogador × temporada college)
   • 6 categorias normalizadas por-40-min
   • contexto: idade, TS%, usage, SOS, posição
   │
   ├──────────────────────────────────────────────┐
   ▼                                               ▼
(prospectos HISTÓRICOS)                    (prospectos da CLASSE ATUAL)
   │                                               │
   │   bridge_college_to_nba                       │
   │   (nome auto + seed college_nba_id_overrides) │
   │        │                                      │
   │        ▼                                      │
   │   fct_player_season_stats (carreira NBA)      │
   ▼        ▼                                      │
fct_college_to_nba_outcomes                        │
   (perfil college "última+trajetória" +           │
    desfecho NBA = valor fantasy 6-cat,            │
    média de carreira)                             │
   │                                               │
   └──────────────► fct_prospect_scouting ◄────────┘
                    • perfil do prospecto atual (por-40 + contexto + trajetória)
                    • k comps históricos mais próximos (mesma posição)
                    • projeção = desfecho médio dos comps
```

### Detalhe por modelo

| Modelo | Grão | Conteúdo |
|---|---|---|
| `stg_cbb__player_season` | jogador × temporada college | Stats brutos NCAA limpos (todas as temporadas disponíveis). |
| `int_prospect__college_stats` | jogador × temporada college | 6 categorias **por-40-min** + contexto (idade, TS%, usage, SOS, posição). |
| `bridge_college_to_nba` | jogador college ↔ NBA | Casamento por nome + `college_nba_id_overrides` (seed manual de ambíguos). |
| `fct_college_to_nba_outcomes` | prospecto histórico | Perfil college (última temporada + trajetória) **+** desfecho NBA (valor fantasy 6-cat, **média de carreira**). Espinha dorsal. |
| `fct_prospect_scouting` | prospecto da classe atual | Perfil atual + **k comps** (mesma posição) + projeção pela média dos comps. |
| `college_nba_id_overrides` | par ambíguo | Seed manual de correções de identidade. |
| `current_draft_class` (provável) | prospecto elegível | Seed manual listando a classe do ano (ver §5). |

---

## 5. Pontos em aberto

| Tema | Situação |
|---|---|
| **Dados históricos multi-temporada** | **Dependência crítica.** Scrapers atuais pegam só a temporada atual. O backbone exige histórico de college E de carreiras NBA. Custo novo de coleta. |
| **Definição da "classe atual"** | Fato externo (quem é elegível no draft do ano). Provável **seed manual** `current_draft_class`. |
| **Encoding de "trajetória"** | ✅ Decidido (D-24): delta padronizado (por-40 + eficiência) vs. ano anterior **+ flag** (melhorando/estável/piorando). |
| **Granularidade do arquétipo** | ✅ Decidido (D-23): **fino (5 posições)**, com **fallback para arquétipo grosso (guard/wing/big) quando vizinhos < k**. |
| **Distância dos comps** | ✅ Decidido (D-21, ajustado por D-26): **euclidiana sobre features padronizadas** (por-40 6-cat + **senioridade `class`** + eficiência + SOS). |
| **k (número de comps)** | ✅ Decidido (D-21): **k ≈ 8–10**. |
| **Limiar do fallback de arquétipo** | Quantos vizinhos mínimos antes de cair pro arquétipo grosso? Definir ao construir. |
| **Disponibilidade de pace/usage/SOS** | ✅ **Confirmado no reconhecimento (2026-06-19)** — ver §7. usage e TS% vêm na tabela `players_advanced`; SOS vem no meta da página escola-temporada (nível de time, join por `time × temporada`); pace puro não vem rotulado (há ORtg/DRtg). |
| **Idade** | ✅ **Confirmado indisponível** — CBB Reference não publica idade/nascimento. Proxy = `class` (D-26). |

---

## 6. Próximos passos

- [x] Resolver encoding de trajetória e granularidade de arquétipo. *(D-23, D-24)*
- [x] Definir a métrica de distância dos comps e o k. *(D-21; idade → `class` via D-26)*
- [x] Confirmar quais campos de contexto o CBB Reference fornece. *(reconhecimento 2026-06-19, §7)*
- [x] (Quando for construir) planejar a coleta de histórico multi-temporada. *(D-27: por escola × temporada)*
- [x] **Construir `src/scraping/college.py`** (Selenium, por escola × temporada) — feito 2026-06-19; reusa `common/browser.py` + `common/parsing.py`; parseia por `data-stat`; merge das 3 tabelas por `cbb_id`; escreve `seeds/college_player_seasons.csv`. Validado com Zion 2018-19 (per-40, class, SOS conferem).
- [x] Definir o universo de escolas × temporadas a raspar — escopo inicial em constantes no topo de `college.py`: 6 escolas que alimentam a NBA (duke, kentucky, kansas, north-carolina, ucla, gonzaga) × temporadas 2016–2025. Escalar editando `SCHOOLS`/`SEASONS`.
- [x] `stg_cbb__player_season` (+ schema yml com testes) — feito; lê o seed, tipa, mantém `class` cru (ordinal vai no intermediate).
- [ ] Modelar `int_prospect__college_stats` (ordinal de `class` D-26, arquétipo, trajetória D-24) → ponte → `fct_college_to_nba_outcomes`.
  - **Aplicar piso de minutos** (análogo ao D-15 do Domínio A): a validação do seed (841 linhas, 2026-06-19) mostrou walk-ons/redshirts com ~0 min gerando per-40/TS%/usage extremos ou nulos (TS% até 1.5, usage até 64.6). Filtrar essa cauda antes de comps/distância.
- [ ] Resolver carreiras NBA multi-temporada (desfecho D-11 = média de carreira) — segunda metade da dependência de dados, ainda em aberto.

---

## 7. Reconhecimento do CBB Reference (2026-06-19)

Feito via o Selenium stealth do projeto (HTTP simples leva 403, igual à NBA). Fonte: páginas de jogador (`/cbb/players/<slug>.html`) e de escola-temporada (`/cbb/schools/<escola>/men/<ano>.html`).

**Tabelas por jogador (mesmas IDs nas duas páginas; 1 linha por temporada):**

| Tabela (`id`) | Conteúdo relevante |
|---|---|
| `players_per_min` | **Per-40-min já pronto** (D-10 não precisa de cálculo): `pts/trb/ast/stl/blk/fg3/tov_per_min`, `pos`, `class`, `conf_abbr`. |
| `players_advanced` | `ts_pct`, `usg_pct`, `bpm/obpm/dbpm`, `ws`, `per`, `*_pct` (reb/ast/stl/blk/tov). |
| `players_per_game` / `players_totals` / `players_per_poss` | Alternativas; `per_poss` traz `off_rtg`/`def_rtg`. |

**Página escola-temporada (grão do scrape — D-27):** traz as tabelas acima com **todos os jogadores do time** + tabela `roster` (`height`, `weight`, `hometown`, `high_school`, `rsci`) + no **meta**: `SOS`, `SRS`, `ORtg`, `DRtg`, `PS/G`, `PA/G`.

**Header da página de jogador:** posição, altura/peso, cidade, HS, RSCI Top 100, e **info de draft** (round/pick/ano) — útil pra `bridge_college_to_nba`. **Sem idade/nascimento** (→ D-26).

**Gaps confirmados:** idade não existe (proxy `class`); SOS é nível de time (join por `time × temporada`); pace puro não vem rotulado.
