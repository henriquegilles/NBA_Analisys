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

**Contexto incluído por padrão:** idade, eficiência (TS%), uso (usage), força de calendário (SOS), posição.

> **Limitação estrutural:** Plus/Minus não existe em college → scouting trabalha com **6 categorias** (pts, reb, ast, STOCKS, 3PM, TOV), não 7.

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
| **Distância dos comps** | ✅ Decidido (D-21): **euclidiana sobre features padronizadas** (por-40 6-cat + idade + eficiência + SOS). |
| **k (número de comps)** | ✅ Decidido (D-21): **k ≈ 8–10**. |
| **Limiar do fallback de arquétipo** | Quantos vizinhos mínimos antes de cair pro arquétipo grosso? Definir ao construir. |
| **Disponibilidade de pace/usage/SOS** | Confirmar o que o College Basketball Reference fornece limpo. |

---

## 6. Próximos passos

- [ ] Resolver encoding de trajetória e granularidade de arquétipo.
- [ ] Definir a métrica de distância dos comps e o k.
- [ ] Confirmar quais campos de contexto o CBB Reference fornece.
- [ ] (Quando for construir) planejar a coleta de histórico multi-temporada.
