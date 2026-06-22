# Análise D-22 — `z_total` vs `z_mean` (escolha do agregado do valor fantasy)

> Decisão adiada no design (D-22): o perfil expõe **soma E média** dos z-scores
> das 7 categorias; faltava escolher qual é o *default*. Esta nota traz a análise
> de dados pra fechar a decisão. **Análise feita 2026-06-21.**
>
> ✅ **RESOLVIDO (2026-06-22):** `z_total` (soma) é o **default oficial**; `z_mean`
> fica como leitura auxiliar. Registrado no [00_README](00_README.md) (D-22).

## Achado (sobre dados reais)

Sobre o pool de referência de `fct_player_fantasy_value_season` (397 jogadores):

| Métrica | Valor |
|---|---|
| `corr(z_total, z_mean)` | **1.000000** |
| Posições com rank diferente entre os dois | **0** |
| Razão `z_total / z_mean` | **exatamente 7.0** para todos |

**Por quê:** todos os jogadores do pool têm as **7 categorias preenchidas**
(stats NBA completos), então `z_total = soma dos 7 z` e `z_mean = z_total / 7`.
Sendo uma constante multiplicativa, os dois **ordenam os jogadores de forma
idêntica**. A escolha **não altera nenhum ranking, comparação de time ou alvo
de troca/FA** — é só escala e interpretação.

> A diferença só apareceria se algum jogador tivesse categoria **NULL** (z
> faltante). Aí `soma` penalizaria quem tem menos categorias e `média` não. No
> Domínio A (NBA, dados completos) isso não ocorre. Se um dia entrar jogador com
> categoria ausente, revisitar.

## Recomendação

**Usar `z_total` (soma) como default**, mantendo `z_mean` exposto:

- É a **convenção** dos sistemas de valor fantasy por z-score (ex.: Hashtag
  Basketball) — "valor total" = soma das categorias. Familiar pra quem joga.
- Soma é aditiva: o valor do time = soma dos valores dos jogadores, o que casa
  com as análises de troca/cap da Fase 2.
- `z_mean` fica como leitura auxiliar ("quantos desvios acima da média por
  categoria, em média") — útil pra explicar, não pra ordenar.

**Nenhuma mudança de modelo é necessária** pra adotar isso (ambos já existem); é
só convenção de qual coluna exibir no front/relatório. Se concordar, o passo é
apenas documentar `z_total` como o oficial (e, se quiser, esconder `z_mean` da
saída final).

## Ligações

- Modelos: `fct_player_fantasy_value_season`, `fct_player_fantasy_value_recent`
  (ambos expõem `z_total` e `z_mean`).
- Decisão original: [00_README](00_README.md) D-22; contexto em
  [04_dominio_a_minha_franquia](04_dominio_a_minha_franquia.md).
