# 10. Métodos de projeção estudados — filtro brutal e o que foi adotado (Rodada 6, Fase 4)

> Fan-out de pesquisa web (2026-07-11): 5 temas cobertos, 26 métodos coletados
> (bruto em [10_metodos_estudados_RASCUNHO.md](10_metodos_estudados_RASCUNHO.md)).
> **Tema não coberto:** valor empírico de pick de draft — o agente de pesquisa
> travou; mitigação: já temos curva EMPÍRICA própria (produção por pick nas
> classes 2016+ e preço real de pick nas trades da liga — `FADraft.pick_curve`/
> `pick_price`, doc metrics_engine 04). Fica pra próxima rodada de estudo.
>
> Critério do filtro: serve pra liga 7-cat H2H (4+ de 7) punt-TOV dynasty de 24
> times, com dados que JÁ temos (BBR + gamelogs + college) e esforço <1 dia.

## 10.1 ADOTADO AGORA (implementado nesta rodada, com antes/depois)

### A. Ajuste de +/- por mudança de time (inspiração: família RAPM/EPM — o +/- é contexto)

- **O quê:** `PM_pg` de quem trocou de time NBA em julho recebe metade do delta de
  saldo médio por jogo entre time novo e antigo (saldo derivado dos gamelogs;
  shrinkage 0,5 = heurística — o papel individual também muda).
  `Engine._apply_nba_context_overrides`.
- **Antes → depois (VA 7-cat):** Claxton −1,94 → **−1,25** (saiu do BRK −10,0);
  Ja 1,65 → **2,42** (POR ≫ MEM); Herro 1,99 → **0,98** (rebuild MIL);
  Ware 0,51 → **−0,50** (rebuild também cobra). Baseline do sim: 60,9% → **65,2%**.
- **Limitação honesta:** o saldo usado é o da temporada 2025-26 do time de DESTINO
  (proxy — o elenco novo do destino não tem histórico). Pro Ware, p.ex., o MIL
  pós-Giannis será pior que o MIL medido; a direção está certa, a magnitude é
  aproximada.

### B. FA board ciente de contexto 2026-27

- **O quê:** o score do `fa_board` multiplica pelo `role_mult` do seed
  `nba_context_overrides` (sign-safe), além do desconto de lesão da liga.
- **Antes → depois:** Butler caía como nº 1 do board (score 2,06, "saúde 100%",
  cego ao LCA) → agora score 0,31 (ctx 0,15). Vučević descontado (0,75) vira o
  nº 1 com 0,67 — ou seja, **o board finalmente diz a verdade: a FA está rasa** e
  reforço real vem de troca/leilão dos $0.

## 10.2 ADOTAR NA PRÓXIMA RODADA (alto valor, esforço médio — backlog priorizado)

| # | Método | Por quê serve | Esforço |
|---|---|---|---|
| 1 | **G-score (Rosenof)** — ponderar cada categoria pela variância SEMANAL em H2H (z-score superestima cats voláteis; 3PM/STOCKS são voláteis, REB/PTS estáveis) | nosso sim é determinístico em totais — é exatamente o erro que o G-score corrige; mudaria pesos e "vitórias por um fio" | ~1 dia (temos gamelogs pra variância semanal) |
| 2 | **Padding/shrinkage de 3P% (Medvedovsky/Blackport)** — taxa_regredida = (acertos + P×média_liga)/(tentativas + P); thresholds KR-21 por stat | z_3PM de amostra pequena é ruído (flag G<25 vira correção quantitativa); afeta predicts de jovens e prospectos | ~½ dia |
| 3 | **Simple Projection System (B-Ref/Marcel)** — taxas por minuto das 3 últimas temporadas com pesos 6/3/1 + regressão à média + ajuste de idade | upgrade natural do Predicts v2 quando tivermos 2+ temporadas de gamelogs (hoje só 2025-26 — **bloqueado por dado**) | ~1 dia quando houver dado |
| 4 | **FT% como preditor de 3P% para rookies** | melhora a projeção 3PM da classe de draft (temos FT% college) | ~½ dia |
| 5 | **Calendário de playoffs fantasy (semanas 18-23)** — nº de jogos por time NBA nas semanas de mata-mata | tie-breaker de FA/trade no meio da temporada; precisa do calendário NBA 2026-27 (ainda não publicado) | ~½ dia quando sair |

## 10.3 DESCARTADO (e por quê)

- **CARMELO/RAPTOR/DARKO completos** — exigem RAPM/EPM por posse (dados de
  tracking que não temos) ou infra bayesiana diária; o retorno sobre o nosso
  k-NN de comps + aging paramétrica não paga o custo. (O ESPÍRITO deles — comps +
  regressão + idade — já está no Domínio B e no Predicts v2.)
- **BORD$/SCHOENE completos** — valoração em dólares NBA, não em categorias
  fantasy; nosso cap fantasy tem preço próprio (pick_price/trades da liga).
- **Streaming semanal agressivo** — em liga dynasty de 24 times o waiver é raso
  demais (a própria pesquisa ressalvou); o que sobrevive é o item 5 acima
  (planejar playoffs) e "GP semanal" como tie-breaker.
- **Back-to-back/descanso** — efeito real (~2 pts/100) mas irrelevante na escala
  de decisão de offseason; reavaliar só se a liga tiver lineup diário.
- **Punt-math de 9 cats** — a matemática publicada é de ligas 8/9-cat; a nossa é
  7 com punt-TOV já decidido. O que aproveitamos está na tese §17.4 do doc 09
  (TOV como tie-breaker), sustentada pela correlação AST↔TOV (+0,78) da pesquisa.

## 10.4 Aprendizado de processo

O achado mais valioso da rodada não veio da pesquisa: veio de auditoria de regra
(**o motor jogava com 6 das 7 categorias** — runbook #34). Antes de sofisticar
método, conferir se o modelo joga o MESMO jogo da liga.
