# Fase 2.5 — Free Agency 2.0 & Draft Board 2.0

> Adendo focado em **decisão acionável de offseason** (Free Agency + Draft 2026).
> Tudo roda **offline** (lê seeds do último scrape, sem DB) via `dashboard/fa_draft_engine.py`
> e aparece nas abas **🎯 FA 2.0** e **🏆 Draft 2.0** do app Streamlit.
> Saídas persistidas em `dashboard/data_cache/` (item k) — o app lê o cache, não recomputa do zero.

---

## Free Agency 2.0

| # | Item | Método | Resultado (Lobos) |
|---|---|---|---|
| e | **Pool de FA real** | jogadores valorados **fora dos 24 rosters** (anti-join por `key` normalizada) | pool limpo, sem quem já tem dono |
| f | **Valor sobre reposição posicional** | `VA − nível de reposição` do grupo (G/W/B); reposição = média VA do **top-3 FA** do grupo | reposição G=2.41 · W=1.02 · B=1.23 |
| g | **Pesos da simulação** | H2H sim: winrate = média sobre 23 rivais de (levo ≥4 de 6 cats). Peso da cat = `winrate(cat+1σ) − base` | **base 21.7%**; alavancas: **3PM +0.13** · AST/TOV +0.087 · REB +0.043 · PTS/STOCKS 0.0 |
| h | **Concorrência rival** | franquias com cap livre **E** fracas numa cat disputam FA dela | urgência por categoria |
| i | **Waiver watch** | franquias **acima do limite de roster** vão cortar bons jogadores | alvos de waiver |
| j | **Desconto de lesão** | multiplicador `injury_disc` sobre o score final | atenua lesionado |

**Score de FA:** `0.5·(VA − reposição) + 0.5·fit_sim`, vezes `injury_disc`.
`fit_sim` = média z ponderada pelos **pesos da simulação** (normalizados p/ somar 1) → premia
quem pontua nas categorias que **de fato viram confronto** pro Lobos (3PM na frente).

> **Leitura estratégica:** a simulação confirma quantitativamente a tese punt-TOV + fix-3PM —
> somar 1σ de **3PM** sobe o winrate +13pp, enquanto PTS/STOCKS não movem a agulha (já estou
> na frente nelas). O board de FA pondera nisso automaticamente.

## Draft Board 2.0

| # | Item | Método | Resultado |
|---|---|---|---|
| a | **Curva de pick** | produção histórica (`pg_pts+trb+ast`) por **nº de pick**, classes 2016+, suavizada (janela 5) | #1=27.5 · #5=22.1 · #10=16.1 · #30=11.9 · #60=7.5 |
| b | **Talento × oportunidade** | curva × `opp_mult` (situação NBA 2026: rebuild=minutos) × `(1+0.5·vácuo)` do meu elenco | Dybantsa (pick 1, WAS rebuild, opp 1.40) → 39.7 |
| c | **Surplus de contrato** | rookie custa ~$5M (1ª) / ~$2.5M (2ª) → produção barata = surplus alto | ver "vale comprar" |
| d | **Preço real de pick** | minera `fantasy_trades.csv`: soma `valor_jogador` dos outros ativos em trades com pick | **1ª rodada $34.0M** (n=30) · **2ª $14.1M** (n=43) |

**Vale COMPRAR uma pick? (c×d):** cruza produção esperada do slot (curva) com o preço real.
1ª rodada só compensa se o slot projeta **≥14** de produção (≈ top-15); late-1st (#20-30) =
"só se barato"; 2ª rodada rende bem por custar só ~$14M.

> **Nota (item a, blend 50/50):** a projeção usa **só a curva de pick** por ora. O blend
> 50/50 com os comps do scouting (`fct_prospect_scouting`) fica pendente até o DB subir —
> declarado, não esquecido.

---

## Como rodar

```bash
cd dashboard
python -c "from fa_draft_engine import FADraft; print(FADraft().build_all())"  # gera o cache
streamlit run app.py         # painel unificado (Rodada 6 Fase 2) — abas FA 2.0 / Draft 2.0
```

Dado pós-trocas: re-scrape com `python src/scraping/fantasy_gm.py` (nunca dois Selenium juntos).

## Erros pegos e corrigidos (revisão durante)

| Erro | Onde | Correção |
|---|---|---|
| `fit_sim` minúsculo (pesos ~0.1) diluía o score | `fa_board` | normalizar pesos p/ somar 1 antes da média z |
| `simulate_weights` retorna dict, app esperava DataFrame | app | reconstruir DataFrame do dict no `load_advanced` |
| `background_gradient` exige matplotlib (fora do venv) | aba Cap | trocado por `Styler.map` condicional (sem matplotlib) → app portátil |
| import relativo (`fantasy_engine`) quebra fora de `dashboard/` | engine | rodar a partir de `dashboard/` (documentado) |
