# Camada Fantasy — Visão Geral

Design da camada analítica que apoia decisões na liga de fantasy **Bandeja de 3** (Liga B.D.3, fantasy.ciengos.com), construída por cima do warehouse de NBA já existente.

> **Status (2026-06-27):** design fechado (D-01…D-33); **Domínio A construído e
> validado**; **Domínio B completo de ponta a ponta** (college→comps→ponte→outcomes→projeção,
> 6-cat, escalado p/ 18 escolas × 15 temporadas). Auditoria 2026-06-22 confirmou
> implementação ↔ escopo alinhados. Para o estado acionável e como retomar, veja **[ESTADO.md](ESTADO.md)** — comece por lá.
>
> Estes documentos numerados capturam **escopo, modelo e decisões** (design).
> Discussão iniciada em 2026-06-18.

---

## Em uma frase

Uma **ferramenta de análise/decisão para a minha franquia** (não uma réplica do motor da liga), alimentada pelos stats da NBA que o projeto já scrapeia, mais um módulo de **scouting de draft** baseado em estatística de college.

---

## Documentos

| Doc | Conteúdo |
|---|---|
| **[ESTADO](ESTADO.md)** | **Estado acionável + como retomar.** Comece por aqui ao continuar. |
| [01_escopo_camada_fantasy](01_escopo_camada_fantasy.md) | Objetivo, as 7 categorias, restrição do site congelado, casos de uso, faseamento |
| [02_modelo_conceitual](02_modelo_conceitual.md) | Princípio de arquitetura, diagrama geral, inventário de modelos |
| [03_dominio_b_scouting](03_dominio_b_scouting.md) | Scouting de draft: normalização, histórico college→NBA, comps |
| [04_dominio_a_minha_franquia](04_dominio_a_minha_franquia.md) | Marts de valoração (z-score), forças/fraquezas do meu elenco |
| [05_melhorias_scouting](05_melhorias_scouting.md) | Backlog de método: sinal de confiança + projeção ponderada (design) |

---

## Os dois domínios

- **Domínio A — minha franquia:** valoração de jogadores por categoria (z-score), forças/fraquezas do elenco, avaliação de trocas, alvos de FA. Usa as **7 categorias** (com +/-).
- **Domínio B — scouting de draft:** avaliação de prospectos via proxy das **6 categorias** (sem +/- em college) + contexto + comparação com histórico college→NBA. Fontes faseadas: NCAA → G-League → Internacional.

---

## Restrição que molda tudo

O **site Ciengos está congelado** — sem export do estado da liga. Logo:
- ✅ Tudo que depende só de stats NBA é viável.
- ❌ Análises que dependem dos rosters das outras 23 franquias ficam bloqueadas (FA só aproxima "melhores fora do meu time"; forças/fraquezas só vs. baseline médio).

---

## Decision log consolidado (D-01 a D-33)

### Escopo (doc 01)
| ID | Decisão |
|---|---|
| D-01 | Propósito = ferramenta de análise/decisão, não réplica do motor |
| D-02 | Foco = só a minha franquia |
| D-03 | Janela = forma recente E temporada, lado a lado |
| D-04 | Scouting = híbrido comparativo (6 cats + contexto + histórico) |
| D-05 | Modelar base histórica college→NBA como espinha dorsal |
| D-06 | Fasear fontes: NCAA → G-League → Internacional (seed manual) |

### Modelo conceitual (doc 02)
| ID | Decisão |
|---|---|
| D-07 | Valoração por z-score por categoria (somável) |
| D-08 | Dois marts de valoração separados (_recent e _season) |
| D-09 | Identidade college→NBA: ponte automática + correções manuais |

### Domínio B — scouting (doc 03)
| ID | Decisão |
|---|---|
| D-10 | Normalizar college para por-40-minutos |
| D-11 | Desfecho NBA = carreira inteira (média) |
| D-12 | Prospecto = última temporada + trajetória |
| D-13 | Comps na mesma posição/arquétipo |

### Domínio A — minha franquia (doc 04)
| ID | Decisão |
|---|---|
| D-14 | Z-score sobre médias por-jogo; jogos como contexto |
| D-15 | Pool de referência com piso de minutos/jogos |
| D-16 | Forma recente = últimos 15 jogos |
| D-17 | Perfil de forças/fraquezas sobre o roster inteiro |

### Refinamentos (discussão de fechamento)
| ID | Decisão |
|---|---|
| D-18 | Cap/contratos-fantasy **incluídos**, via seed manual `fantasy_contracts` (anda com `my_roster`); torna trocas/FA cientes do cap. *Dependência: site congelado → manual* |
| D-19 | Pool da forma recente **recomputado** sobre os últimos 15 jogos |
| D-20 | Pesos das categorias **iguais** (default) |
| D-21 | Comps por **distância euclidiana sobre features padronizadas, k ≈ 8–10** |
| D-22 | Perfil do time expõe **média E soma** dos z-scores. ✅ **Resolvido (2026-06-22): `z_total` (soma) é o default oficial**, `z_mean` fica como leitura auxiliar — rankeiam idêntico (corr 1.0, ver [analise_d22](analise_d22_ztotal_vs_zmean.md)) |
| D-23 | Arquétipo **fino (5 posições)**, com **fallback para arquétipo grosso quando vizinhos < k** |
| D-24 | Trajetória = **delta padronizado (por-40 + eficiência) vs. ano anterior + flag** (melhorando/estável/piorando) |
| D-25 | Fonte de posições **a definir** via análise web futura; **BBR como hipótese de trabalho** por ora |
| D-26 | **`class` (Fr=1…Sr=4) como proxy de idade** no Domínio B (contexto + distância dos comps); CBB Reference não publica idade. Ajusta D-21. *(reconhecimento 2026-06-19)* |
| D-27 | Coletar histórico college **por escola × temporada** (todos os jogadores + SOS numa requisição), não página-por-jogador *(reconhecimento 2026-06-19)* |
| D-28 | **Arquétipo = G/F/C** (guard/wing/big), não 5 posições — CBB Reference só classifica nesses 3 níveis. Ajusta D-23. *(validação de dados 2026-06-19)* |
| D-29 | **Desfecho NBA (1ª versão) vem do seed `draft`** (médias de carreira pg_pts/trb/ast + WS/BPM/VORP), não de scraper novo — desbloqueia o backbone. Cobre 3 das 6 categorias; carreira 6-cat completa = futuro. *(2026-06-19)* |
| D-30 | **Desfecho NBA 6-cat completo** via `nba_careers.py`: raspa a linha *Career* da página de cada jogador (stl/blk→stocks, 3PM, TOV — o que o `draft` não traz). Junção pelo **slug NBA `bbr_id`** (capturado dos hrefs no `draft.py`), não por nome+ano — chave canônica sem ambiguidade. Escopo do scrape = só os ~96 matches da ponte (não os ~2400 draftados), recalculados em pandas. `LEFT JOIN` na ponte: carreira ainda não raspada ⇒ cats novas NULL. Fecha D-29. *(2026-06-21)* |
| D-33 | **Sinal de confiança na projeção** (Melhoria 1, doc 05): `confidence` (alta/media/baixa) + `coverage_6cat` + `mean_comp_distance` no `fct_prospect_scouting`. Limiares de distância calibrados pelos **tercis reais** (t33=1.43, t67=1.78), não arbitrários. Unicórnios (Holmgren/Embiid) → baixa; arquétipos com bons análogos → alta. *(2026-06-27)* |

### Formalização de knobs (auditoria 2026-06-22)
| ID | Decisão |
|---|---|
| D-31 | **Piso de minutos do college = 200 min/temporada** (`int_prospect__college_stats`, knob `min_minutes`) — corta walk-ons/redshifts cujos per-40/TS%/usage explodem; análogo ao D-15 do Domínio A *(estava só no SQL; formalizado)* |
| D-32 | **Knobs de janela e trajetória:** forma recente exige **≥10 dos 15 jogos** (e ≥12 mpg) pra entrar; banda de trajetória = **0.5 dp** pra classificar "estável" (`traj_band`) *(estava só no SQL; formalizado)* |

---

## Roadmap por fases

| Fase | Entrega |
|---|---|
| **1** | Domínio A (valoração só com stats NBA) + Domínio B framework + NCAA + base histórica college→NBA |
| **2** | Ingestão do meu roster (fonte a definir) → forças/fraquezas, trocas, FA aproximada; scouting G-League |
| **3** | Scouting Internacional (seed manual dos top prospectos) |

---

## Pontos em aberto (consolidado)

**Dependências de dados**
- Histórico multi-temporada **college** — ✅ viável e mapeado (reconhecimento 2026-06-19, ver doc 03 §7); `src/scraping/college.py` construído (por escola × temporada, D-27). **Carreiras NBA** — ✅ resolvido via `nba_careers.py` (linha *Career* da página do jogador, junção pelo slug `bbr_id`, D-30); falta só a **execução ao vivo** do scrape (re-raspar `draft.py` + `nba_careers.py`).
- Fonte do meu roster — site congelado; possível imagem do time → seed manual.
- Definição da "classe atual" de draft — provável seed manual.
- ~~Confirmar campos que o College Basketball Reference fornece limpos~~ — ✅ feito: per-40, TS%, usage, posição, `class`, BPM/WS prontos; SOS é nível de time; **idade não existe** (→ D-26).

**Decisões finas — resolvidas na auditoria 2026-06-22**
- ✅ Pisos do pool (Domínio A): 15 jogos / 12 mpg (season), 10/15 / 12 mpg (recent) — D-32.
- ✅ Perfil média vs. soma: `z_total` é o default oficial (D-22 resolvido).
- ✅ Fallback de arquétipo: limiar = vizinhos da mesma classe < k(=8) → abre p/ todos (já implementado, D-23).
- ✅ Piso de minutos do college: 200 (D-31).

**Melhorias de método (backlog, ver [05_melhorias_scouting](05_melhorias_scouting.md))**
- Sinal de confiança na projeção de prospecto (alta/média/baixa).
- Projeção ponderada por distância (vs. média simples atual).

**Escopo / dados a confirmar**
- Estrutura do seed `fantasy_contracts` (salário + duração) — definir junto com a fonte do roster.
- Fonte definitiva de posições — **análise web futura** dos melhores sites (hipótese: BBR é o mais completo). Não confundir `fantasy_contracts` com `dim_player_contract` (= salário real NBA).
