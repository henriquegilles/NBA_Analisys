# Brief da Rodada 6 — execução autônoma (noite de 2026-07-11)

Regras gerais: nunca perguntar nada ao Henri. Decisão de implementação = sua. Decisão de
REGRA DE NEGÓCIO (troca real, lance, corte, renovação, gasto de pick, mudança de
estratégia) NUNCA é executada — vira entrada em `docs/fantasy/PENDENCIAS_VALIDACAO.md`
com: contexto, recomendação única, 2 alternativas, custo de errar em cada direção, prazo.
Commit ao fim de cada fase (padrão das rodadas). CI verde inegociável (dbt seed/compile/
run/test). Agentes à vontade. Honestidade: toda conclusão carrega evidência (nº do sim,
fonte web, ou "heurística — não verificado"); resultado do sim na casa de 1 confronto
(±4,3pp) = empate técnico, dizer isso.

## FASE 0 — Fundação e qualidade de dados
- Re-rodar scraper FantasyGM se FGM_EMAIL/FGM_PASS existirem (senão: pendência no topo).
  Rebuild completo: seeds → dbt (`+models/marts/fantasy`) → dbt test → `FADraft().build_all()`.
- Auditoria de frescor por seed: o que está desatualizado vs julho (Giannis/Herro/Ware→MIL,
  Ja→POR, Claxton→CHI, Vučević→ORL...). Criar seed versionado de overrides de contexto NBA
  (time atual por jogador afetado), aplicar no motor, cada override com fonte.
- Aceite: dbt test 100% + tabela de frescor + overrides commitados.

## FASE 1 — Predicts v2
- Consolidar por jogador do elenco: VA, Dynasty, Development, Floor/Ceiling, Min/Usage
  Upside, CV, sensibilidade a minutos + NOVO: (a) ajuste de contexto 2026-27 (reports das
  rodadas 4-5), (b) aging curve (pico 26-28, declínio >30, calibrada no draft.csv),
  (c) flag de amostra (G<25 = ruído).
- Validação direcional obrigatória: Butler≈0 (LCA), Vučević↓ (banco), Claxton +~1 (titular),
  Ware↑ (rebuild). Contra-intuitivo → explicar ou corrigir.
- Aceite: artefato reproduzível (view dbt ou método do engine) + 4 casos documentados.

## FASE 2 — Painel unificado
- Fundir app.py + fantasy_gm_tool.py: um app, abas, zero perda de funcionalidade, lógica
  comum extraída. Fallback: sem Postgres, abas de seed funcionam; abas de DB avisam
  (nunca stacktrace). Abas novas: "Predicts" (Fase 1) e "Guerra" (eu vs rival, dropdown).
- Validar TODAS as abas com streamlit.testing.v1.AppTest.
- Revisão de pares nº 1: /code-review; corrigir CONFIRMED.
- Aceite: AppTest verde em todas as abas + entrypoint único documentado no CLAUDE.md.

## FASE 3 — Rodada 6: inteligência competitiva e plano de temporada (doc 09)
- Perfil dos 23 rivais: força por categoria, VA total, idade média ponderada (janela:
  contender/mid/rebuild), cap, picks, excedente/carência, "o que ele quer que eu tenho /
  o que eu quero que ele tem". Matriz de parceiros de troca por peça minha.
- Upgrade do sim: margem por categoria (distância em z por rival) — separar vitória
  folgada de vitória por um fio; listar confrontos "por um fio" e o que os blindaria.
- Trades ranqueadas (jogadores E picks): dWin, margem nas cats decisivas, custo, tradeoff,
  horizonte (curto/médio/longo), gatilho ("faça se X"). Incluir consolidação de guards
  (Ja como peça) e o cenário "não fazer nada" como baseline.
- Árvore CONDICIONAL do leilão: Herro fecha + Wiggins ≤$8M → plano A; Herro não fecha →
  plano B (Lendeborg na 10, orçamento realocado); Quickley disputado >$18M → plano C.
  Cada ramo com orçamento fechado.
- Metas 2026-27 mensuráveis: winrate alvo, 4 cats-âncora (>70% das semanas), marcos com
  data (leilão/draft/deadline), critério de abortar/pivotar.
- Ranking de substituibilidade por posição: substituto interno, externo atingível, custo.
- Métricas de desenvolvimento por jovem (Ware, Watson, picks): 2-3 indicadores com limiar
  "no caminho / vender".
- Reports NBA: waivers/dispensas/assinaturas dos últimos 15 dias → atualizar anti-targets
  das rodadas 4-5 com data.

## FASE 4 — Estudo aplicado (time-box ~3h de agentes)
- Fan-out: métodos de projeção dynasty H2H-cats (aging curves, regressão TS%/3P% à média,
  valor empírico de pick, punt ótimo, schedule/streaming effects, modelos tipo
  BORIS/CARMELO adaptados) + analistas respeitados. Método + evidência + aplicabilidade.
- Filtro brutal: só entra o que serve pra liga 6-cat H2H punt-TOV dynasty de 24 times com
  dados que já temos (ou scrapeáveis do BBR). Documentar em
  `docs/fantasy/10_metodos_estudados.md` (adotar agora / backlog / descartado + porquê).
- Implementar as 2-3 melhorias de maior retorno/menor risco com teste antes/depois do
  impacto nos predicts/sim. Resto → backlog priorizado com esforço.

## FASE 5 — Fechamento adversarial
- Revisão de pares nº 2 (/code-review) no acumulado; corrigir CONFIRMED.
- Agente cético: "derrube as 5 recomendações mais importantes" — o que cair é corrigido
  ou rebaixado a hipótese.
- Varredura de contradições no doc 09 (§1-§10 vs rodadas 4-6): conselho morto ganha nota
  de revogação (Butler, Vučević, regra da pick 19...).
- Atualizar playbook executivo (1 página) pro estado final.
- Commit final. Topo do PENDENCIAS_VALIDACAO.md: resumo de 1 página, 3-5 decisões pra
  manhã em ordem de urgência (recomendação + custo de adiar). Fechar listando o que NÃO
  foi feito e por quê — sem maquiar.
