# Camada Fantasy — Domínio A: Minha Franquia (detalhado)

> **Status:** rascunho de design (ideação). Nenhum modelo criado.
> **Pré-requisitos:** [01_escopo](01_escopo_camada_fantasy.md), [02_modelo_conceitual](02_modelo_conceitual.md).

---

## 1. Objetivo

Marts que apoiam as decisões semanais de GM sobre a **minha** franquia: valorar jogadores, ver forças/fraquezas do elenco, avaliar trocas e alvos de FA.

> **Diferença vs. scouting:** aqui o **Plus/Minus existe** (é dado da NBA) → o Domínio A usa as **7 categorias completas** (pts, reb, ast, STOCKS, 3PM, +/-, TOV).

---

## 2. Como o z-score é calculado

Para cada categoria, mede-se quantos desvios-padrão o jogador está vs. a média de um **pool de referência**; somam-se as 7 num **valor único**. O **TOV entra invertido** (menos turnover → z positivo).

Decisões que definem o cálculo:

| ID | Decisão | Racional |
|---|---|---|
| **D-14** | Z-score sobre **médias por-jogo**; "jogos disputados" exposto como **contexto** à parte | Separa qualidade (rate) de disponibilidade (volume); não esconde informação num número só |
| **D-15** | Pool de referência = jogadores acima de um **piso de minutos/jogos** | Evita que o fim do banco afunde a média e infle todos os z-scores |
| **D-16** | Janela "forma recente" = **últimos 15 jogos** | Equilíbrio entre captar a fase atual e ter amostra suficiente |
| **D-17** | Perfil de forças/fraquezas calculado sobre o **roster inteiro** (12–18) | Visão da profundidade do elenco por categoria; mais simples |

> **Restrição (site congelado):** forças/fraquezas só podem ser medidas **vs. um baseline médio da liga** (time hipotético médio = média do pool), nunca vs. um adversário real.

---

## 3. Pipeline detalhado

```
fct_player_game_log
   │
   ▼
int_player__fantasy_categories        (grão: jogador × jogo)
   • 7 categorias isoladas; STOCKS = stl+blk; TOV mantido (marcado invertido)
   • minutos + flags de jogo (contexto)
   │
   ├───────────────────────────────┬───────────────────────────────┐
   ▼ (janela: últimos 15 jogos)     ▼ (janela: temporada cheia)     │
fct_player_fantasy_value_recent   fct_player_fantasy_value_season   │
   • médias por-jogo das 7 cats      • idem, sobre a temporada       │
   • z-score por cat vs. pool        • z-score por cat vs. pool      │
   • valor agregado (soma dos z)     • valor agregado                │
   • jogos disputados (contexto)     • jogos disputados (contexto)   │
                          │                       │                  │
   seed my_roster ─→ dim_my_roster ──────────────┴──────────────────┘
                          │
                          ▼
              fct_my_team_category_profile      (grão: meu time × categoria)
                 • agrega os z-scores do meu roster por categoria
                 • positivo = força, negativo = fraqueza (vs. pool médio)
                 │
                 ▼
   consumidores (análises/exposures, não marts-base):
     • avaliação de trocas — simular roster com X↔Y e recomparar o perfil
     • alvos de FA — ranquear "melhores fora do meu time" pelas minhas fraquezas
```

### Detalhe por modelo

| Modelo | Grão | Conteúdo |
|---|---|---|
| `int_player__fantasy_categories` | jogador × jogo | As 7 categorias de `fct_player_game_log`; STOCKS=stl+blk; TOV marcado invertido; minutos/flags como contexto. |
| `fct_player_fantasy_value_season` | jogador | Médias por-jogo (temporada) + z-score por cat (vs. pool) + valor agregado + jogos disputados. |
| `fct_player_fantasy_value_recent` | jogador | Idem, sobre os **últimos 15 jogos**. |
| `my_roster` | jogador do meu time | Seed manual (fonte a definir: possível imagem do time). |
| `dim_my_roster` | jogador do meu time | `my_roster` + `dim_player` (identidade/posição NBA). |
| `fct_my_team_category_profile` | meu time × categoria | Soma/média dos z-scores do roster por categoria; positivo=força, negativo=fraqueza. |

---

## 4. Pontos em aberto

| Tema | Situação |
|---|---|
| **Pisos exatos do pool** | Quais valores (ex.: ≥20 min/jogo e ≥10 jogos)? Definir ao construir. |
| **Pool por janela** | O pool da "forma recente" é recomputado sobre os últimos 15 jogos, ou reusa o pool da temporada? (recomputar é mais correto, mais custoso) |
| **Pesos das categorias** | Padrão = peso igual entre as 7. Eventual customização (ex.: valorizar STOCKS) fica pra depois. |
| **Agregação do perfil** | Soma vs. média dos z-scores do roster por categoria — definir. |
| **Fonte do meu roster** | A definir (possível transcrição de imagem → seed). |
| **Disponibilidade futura** | Projeção de jogos/calendário não é modelada (sem dados de schedule confiáveis). "Jogos disputados" é histórico, não previsão. |

---

## 5. Próximos passos

- [ ] Definir pisos do pool e se a janela recente recomputa o pool.
- [ ] Definir agregação do perfil do time (soma vs. média).
- [ ] (Quando houver roster) desenhar as análises de troca e de alvos de FA.
