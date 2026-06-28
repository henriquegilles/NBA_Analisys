# Camada Fantasy — Melhorias de Método do Scouting (design)

> **Status:** Melhoria 1 **IMPLEMENTADA** (2026-06-27); Melhoria 2 segue no backlog
> (depende do backtest leave-one-out). Saiu da auditoria 2026-06-22, que confirmou
> escopo↔implementação alinhados e apontou estas duas melhorias.
> **Pré-requisitos:** [03_dominio_b_scouting](03_dominio_b_scouting.md), [ESTADO](ESTADO.md).

Hoje `fct_prospect_scouting` projeta um prospecto como a **média simples** dos
desfechos NBA dos seus `k=8` comps. Duas fragilidades aparecem nos dados:

1. A projeção sai **com a mesma cara** quer ela se apoie em 8 comps próximos e com
   carreira NBA, quer em 2 comps distantes e via fallback de arquétipo.
2. A **média simples** trata um comp coladinho (distância 0.3) igual a um comp
   distante (distância 3.0).

---

## Melhoria 1 — Sinal de confiança na projeção  ✅ IMPLEMENTADA (2026-06-27)

> Construída em `fct_prospect_scouting` (D-31): colunas `confidence`
> (alta/media/baixa), `coverage_6cat`, `mean_comp_distance`. Limiares de distância
> calibrados pelos **tercis reais** (t33=1.43, t67=1.78). Distribuição: 29 alta /
> 178 media / 535 baixa. Face validity ok — unicórnios (Holmgren, Embiid) caem em
> `baixa` (sem bons análogos); armadores arquetípicos (Maxey, Herro) em `alta`.

### Problema
A projeção não comunica **quão confiável** ela é. Os contadores existem
(`n_comps_with_outcome`, `n_comps_with_6cat`), mas não viram um sinal legível.

### Design proposto
Adicionar ao mart um campo `confidence ∈ {alta, média, baixa}`, derivado de sinais
**já disponíveis** + um a trazer de cima (`distance`, que vive em
`int_prospect__comps`):

| Sinal | Fonte | Leitura |
|---|---|---|
| Cobertura 6-cat = `n_comps_with_6cat / k` | já no mart | quantos comps têm carreira NBA raspada; baixo = evidência fina |
| `used_archetype_fallback` | já no mart | comps vieram de outro arquétipo ⇒ menos fiável |
| Distância média dos k comps | trazer de `int_prospect__comps` | cluster apertado = bons análogos; distante = extrapolação |
| `n_comps_with_outcome` | já no mart | quantos comps chegaram à NBA |

**Regra (calibrável):**
- **baixa** se `n_comps_with_6cat < 3` **OU** `used_archetype_fallback` **OU** distância média > `limiar_alto`.
- **alta** se `n_comps_with_6cat ≥ 6` **E** não fallback **E** distância média < `limiar_baixo`.
- **média** caso contrário.

**Saída nova:** `confidence` (enum) + `coverage_6cat` (razão) + `mean_comp_distance`.

### Knobs em aberto
- `limiar_baixo` / `limiar_alto` da distância — calibrar pelos **tercis da
  distribuição real** de distâncias (não cravar número arbitrário).
- Pesos relativos dos sinais (hoje é regra booleana; poderia virar score).

---

## Melhoria 2 — Projeção ponderada por distância

### Problema
Média simples dá o mesmo peso ao comp mais parecido e ao mais distante. O comp
colado deveria pesar mais.

### Design proposto
Ponderação por **inverso da distância**:

```
w_i        = 1 / (distance_i + ε)
proj_cat   = Σ_i (w_i · outcome_i,cat) / Σ_i w_i
```

- `ε` (suavização) evita explosão quando `distance ≈ 0` (match quase exato) e
  controla quão "agressiva" é a ponderação. Recomendo `ε = mediana das distâncias`
  (data-driven, livre de escala).
- **NULL-aware:** pra cada categoria, renormaliza os pesos só sobre os comps que
  têm aquela categoria — consistente com o `avg()` atual que ignora NULL.
- Manter as colunas atuais de média simples como `proj_*_unweighted` pra
  **comparação**, não trocar o default no escuro.

### Trade-off
- `ε → 0`: a projeção colapsa no vizinho mais próximo (overfit a uma carreira
  ruidosa). `ε` grande demais: vira a média simples de volta.
- Alternativa mais suave: kernel gaussiano `w_i = exp(−(d_i/h)²)` com largura `h`.
  Inverso-da-distância é mais simples; o kernel é mais liso. Começar pelo simples.

### Como escolher o default (validação fundamentada)
Como já temos a espinha dorsal histórica (`fct_college_to_nba_outcomes`), dá pra
**backtestar** com leave-one-out: prever o desfecho de um prospecto histórico a
partir dos seus comps (ponderado vs. simples) e medir o erro vs. o real.
**Adotar como default o que tiver menor erro.** Sem isso, a ponderação fica como
coluna alternativa, não como verdade.

---

## Resumo / priorização

| Melhoria | Esforço | Valor | Pré-condição | Status |
|---|---|---|---|---|
| 1 — Sinal de confiança | baixo | **alto** (evita confiar cego em projeção fina) | trazer `distance` ao mart | ✅ feito 2026-06-27 (D-31) |
| 2 — Projeção ponderada | médio | médio | backtest leave-one-out p/ justificar o default | backlog |

> Ambas são **mudanças de modelo (código)** — ficam no backlog enquanto o chat
> está em modo design. Quando for construir, a Melhoria 1 vem antes (barata e de
> alto valor); a Melhoria 2 só troca o default **depois** do backtest.
