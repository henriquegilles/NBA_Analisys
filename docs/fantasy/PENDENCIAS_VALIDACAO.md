# Pendências de Validação — Rodada 6 (noite de 2026-07-11)

> Decisões de **regra de negócio** que eu (Claude) não executo sozinho. Cada entrada:
> contexto, recomendação única, alternativas, custo de errar em cada direção, prazo.
> O resumo executivo de 1 página será escrito no TOPO ao final da Fase 5.

<!-- RESUMO_EXECUTIVO_PLACEHOLDER — preenchido na Fase 5 -->

---

## P-01 — Dados da liga possivelmente defasados: scraper FantasyGM não rodou (sem credenciais)

- **Contexto:** o brief pedia re-rodar `src/scraping/fantasy_gm.py` antes de tudo, mas
  `FGM_EMAIL`/`FGM_PASS` não estão no ambiente desta sessão. Toda a Rodada 6 usa os
  seeds fantasy da última coleta (ver tabela de frescor na Fase 0 do doc 09).
- **Recomendação:** de manhã, exportar as credenciais e rodar o scraper + rebuild
  (`python src/scraping/fantasy_gm.py && dbt build --profiles-dir .dbt --select +models/marts/fantasy`),
  depois conferir se alguma conclusão da Rodada 6 muda (em especial rosters de rivais e
  standings — o resto é estável).
- **Alternativas:** (a) aceitar os dados atuais se você sabe que não houve movimentação
  na liga desde a última coleta; (b) pedir a outro membro da liga um print dos rosters
  recentes pra conferência manual.
- **Custo de errar:** se rodar de novo à toa → ~10 min. Se NÃO rodar e houve trade/waiver
  na liga → perfis de rivais e sugestões de troca da Fase 3 podem mirar jogadores que já
  mudaram de dono (retrabalho da análise, risco de propor troca inválida).
- **Prazo:** antes de agir em qualquer sugestão de troca da Fase 3.
