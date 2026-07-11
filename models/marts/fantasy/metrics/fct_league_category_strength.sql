{{ config(materialized='view') }}
-- Força de cada franquia por categoria (soma dos z do top-10 por VA punt-TOV).
-- Alimenta o "rival scan": quem vence cada categoria.
with ranked as (
    select *,
        row_number() over (partition by franchise_id order by va_punt_tov desc nulls last) as core_rank
    from {{ ref('int_fantasy__roster_valuation') }}
    where not unmatched
),
top10 as (select * from ranked where core_rank <= 10),
agg as (
    select
        franchise_id, franchise_name,
        round(sum(z_pts)::numeric,1)    as pts,
        round(sum(z_reb)::numeric,1)    as reb,
        round(sum(z_ast)::numeric,1)    as ast,
        round(sum(z_stocks)::numeric,1) as stocks,
        round(sum(z_three_p)::numeric,1) as three_pm,
        round(sum(z_tov)::numeric,1)    as tov_inv,
        round(sum(va_punt_tov)::numeric,1) as total_va
    from top10
    group by 1,2
)
select *,
    -- desempate por franchise_id: com amostra pequena (CI) os totais arredondados
    -- empatam e rank() duplicaria o league_rank (o teste unique quebraria)
    row_number() over (order by total_va desc, franchise_id) as league_rank
from agg
order by total_va desc
