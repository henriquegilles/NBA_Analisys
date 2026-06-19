# Camada Fantasy — Modelo Conceitual

> **Status:** rascunho de design (ideação). Nenhum modelo foi criado — este documento descreve a arquitetura proposta.
> **Pré-requisito:** ver [01_escopo_camada_fantasy.md](01_escopo_camada_fantasy.md) para objetivo, restrições e casos de uso.

---

## 1. Princípio de arquitetura

A camada fantasy **não duplica dados**. Ela **consome** os marts de NBA já existentes (`fct_player_game_log`, `fct_player_season_stats`, `dim_player`, `fct_draft_class`, etc.) e adiciona modelos novos por cima, seguindo a mesma convenção dbt: `stg_` → `int_` → marts.

Os modelos novos viveriam em `models/marts/fantasy/` (+ `models/staging/cbb/` e `models/intermediate/` para o scouting).

---

## 2. Diagrama de alto nível

```
  WAREHOUSE NBA (já existe)
  seeds → stg_bbr__* → int_* → dim_player / dim_team / dim_game
                              fct_player_game_log / fct_player_season_stats / fct_draft_class ...
        │
        ▼
╔═══════════════════════════ DOMÍNIO A — minha franquia ═══════════════════════════╗
║  fct_player_game_log ──→ ✨int_player__fantasy_categories                         ║
║                            (isola as 7 cats; STOCKS=stl+blk; TOV marcado          ║
║                             invertido; grão = jogador × jogo)                     ║
║                                  │                                                ║
║                    ┌─────────────┴─────────────┐                                 ║
║                    ▼                            ▼                                 ║
║   ✨fct_player_fantasy_value_recent   ✨fct_player_fantasy_value_season           ║
║     (z-score por cat + agregado,        (z-score por cat + agregado,             ║
║      últimos N jogos)                    temporada cheia)                         ║
║                    │                            │                                 ║
║  ✨seed my_roster → ✨dim_my_roster ────────────┴─→ ✨fct_my_team_category_profile║
║                                                       (forças/fraquezas)          ║
║                                                            │                      ║
║                                          consumidores: avaliação de trocas,       ║
║                                          alvos de FA  → análises/exposures         ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════ DOMÍNIO B — scouting de draft ════════════════════════╗
║  ✨scrape NCAA (cbb) → ✨stg_cbb__player_season → ✨int_prospect__college_stats   ║
║                                                          │                        ║
║  dim_player + fct_player_season_stats ─→ ✨bridge_college_to_nba (identidade)     ║
║  (desfecho NBA)                      │         ▲                                  ║
║                                      │   ✨seed college_nba_id_overrides          ║
║                                      ▼         (correções manuais)                ║
║                          ✨fct_college_to_nba_outcomes (espinha dorsal histórica) ║
║                                      │                                            ║
║                                      ▼                                            ║
║                          ✨fct_prospect_scouting                                  ║
║                          (score híbrido 6-cat + contexto + comps históricos)      ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```
✨ = modelo/seed novo da camada fantasy.

---

## 3. Inventário de modelos propostos

### Domínio A — minha franquia

| Modelo | Tipo | Grão | Fonte | Papel |
|---|---|---|---|---|
| `int_player__fantasy_categories` | intermediate | jogador × jogo | `fct_player_game_log` | Isola as 7 categorias; deriva STOCKS = stl+blk; mantém TOV marcado como invertido. Base das agregações. |
| `fct_player_fantasy_value_recent` | mart (fact) | jogador | `int_player__fantasy_categories` | **Z-score por categoria** + valor agregado, sobre os **últimos N jogos**. |
| `fct_player_fantasy_value_season` | mart (fact) | jogador | `int_player__fantasy_categories` | Z-score por categoria + valor agregado, sobre a **temporada cheia**. |
| `my_roster` | seed | jogador do meu time | manual (fonte a definir) | Meu elenco (nome + posição [+ contrato-fantasy?]). |
| `dim_my_roster` | mart (dim) | jogador do meu time | `my_roster` + `dim_player` | Meu elenco enriquecido (join com identidade NBA). |
| `fct_my_team_category_profile` | mart (fact) | meu time × categoria | `dim_my_roster` + marts de valoração | **Forças/fraquezas**: perfil agregado do meu elenco vs. referência da liga. |

**Consumidores (não são marts-base):** avaliação de trocas e alvos de FA são **análises/exposures** consultando os marts de valoração — não tabelas persistidas próprias. (Alvos de FA é limitado: sem dados da liga, aproxima como "melhores fora do meu time".)

### Domínio B — scouting de draft

| Modelo | Tipo | Grão | Fonte | Papel |
|---|---|---|---|---|
| `stg_cbb__player_season` | staging | jogador × temporada college | scrape College Basketball Reference (NCAA) | Stats de temporada de college, limpos. |
| `int_prospect__college_stats` | intermediate | prospecto × temporada college | `stg_cbb__player_season` | 6 categorias sourceáveis + contexto (eficiência, uso, idade, nível de competição). |
| `bridge_college_to_nba` | mart (bridge) | jogador college ↔ jogador NBA | nomes + `college_nba_id_overrides` | **Resolução de identidade**: casa automático por nome + correções manuais. |
| `college_nba_id_overrides` | seed | par ambíguo | manual | Correções de casamento (homônimos, grafias). |
| `fct_college_to_nba_outcomes` | mart (fact) | prospecto histórico | `int_prospect__college_stats` + `bridge` + `fct_player_season_stats` | **Espinha dorsal histórica**: stats college + desfecho NBA. Base das comparações. |
| `fct_prospect_scouting` | mart (fact) | prospecto da classe atual | `int_prospect__college_stats` + `fct_college_to_nba_outcomes` | **Score híbrido** (proxy 6-cat + contexto) + comps históricos mais próximos. |

> **Nota:** Plus/Minus (categoria 6 da liga) **não existe** em college → o scouting trabalha com **6 categorias**, não 7. Limitação assumida.

---

## 4. Decisões deste documento (decision log)

| ID | Decisão | Racional |
|---|---|---|
| **D-07** | Valoração por **z-score por categoria** (vs. média/desvio da liga), somável num valor agregado | Padrão de fantasy; torna categorias comparáveis; resolve o TOV invertido como z-score negativo |
| **D-08** | **Dois marts de valoração separados** (`_recent` e `_season`), não um só | Escolha do Henri — mais modular |
| **D-09** | Identidade college→NBA via **ponte automática por nome + seed de correções manuais** | Cobre a maioria automaticamente e trata ambiguidades sem virar trabalho manual gigante |

---

## 5. Pontos em aberto (herdados + novos)

- **"N" da forma recente** — quantos jogos (ex.: 10, 15)? Decidir ao detalhar o Domínio A.
- **Referência da liga pro z-score** — "liga" = todos os jogadores NBA com X minutos? Definir o universo de cálculo.
- **Fonte do meu roster** — a definir (possível imagem do time → seed manual).
- **Contexto do scouting** — quais métricas exatas (TS%, usage, idade, strength of schedule) e de onde vêm.
- **Lógica de "comps"** — como definir prospectos históricos "parecidos" (distância em quais dimensões).

---

## 6. Próximos passos

- [ ] Detalhar **Domínio A** — agregações, janela N, universo do z-score, cálculo do perfil do meu time.
- [ ] Detalhar **Domínio B** — métricas de contexto, lógica de comps, modelo do histórico.
