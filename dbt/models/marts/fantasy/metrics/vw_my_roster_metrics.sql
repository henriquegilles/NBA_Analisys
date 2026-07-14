{{ config(materialized='view') }}
-- Metrics for MY roster (Lobos Comunistas, franchise_id 528).
-- Direct source for the "my team" panel in the dashboard.
select
    player_name, pos_1 as position, salary_y1_m,
    round(va_punt_tov::numeric, 2)   as value_punt_tov,
    round(z_pts::numeric,2)  as z_pts,
    round(z_reb::numeric,2)  as z_reb,
    round(z_ast::numeric,2)  as z_ast,
    round(z_stocks::numeric,2) as z_stocks,
    round(z_three_p::numeric,2) as z_3pm,
    round(z_tov::numeric,2)  as z_tov,
    is_injured, is_restricted, unmatched
from {{ ref('int_fantasy__roster_valuation') }}
where franchise_id = 528
order by value_punt_tov desc nulls last
