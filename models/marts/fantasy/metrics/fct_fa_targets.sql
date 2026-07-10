{{ config(materialized='view') }}
-- Alvos de Free Agency: jogadores da valoração NBA que NÃO estão contratados
-- (rosterados com salário > 0). Inclui os $0 dos rosters (vão pra FA).
-- Flag de match: usa o rank de força da liga como proxy de "playoff" (só playoff dá match).
with val as (
    select
        player_name,
        {{ norm_name('player_name') }} as player_key,
        (z_total - z_tov)             as va_punt_tov,
        z_pts,
        z_trb as z_reb,
        z_ast, z_stocks, z_three_p, z_tov
    from {{ ref('fct_player_fantasy_value_season') }}
    where is_reference_pool           -- só jogadores de rotação
),
rostered as (select player_key, franchise_id, franchise_name, salary_y1_m from {{ ref('stg_fantasy__rosters') }}),
paid as (select distinct player_key from rostered where salary_y1_m > 0),
fa_bound as (select player_key, franchise_id, franchise_name from rostered where salary_y1_m = 0),
strength as (select franchise_id, league_rank from {{ ref('fct_league_category_strength') }})
select
    v.player_name,
    round(v.va_punt_tov::numeric,2) as value_punt_tov,
    round(v.z_ast::numeric,2)       as z_ast,
    round(v.z_three_p::numeric,2)   as z_3pm,
    round(v.z_stocks::numeric,2)    as z_stocks,
    -- fit ponderado p/ necessidades (AST+3PM valem 1.5x)
    round((v.z_pts + v.z_reb + v.z_stocks + 1.5*v.z_ast + 1.5*v.z_three_p)::numeric,2) as fit_score,
    fb.franchise_name as held_by,
    coalesce(s.league_rank <= 8, false) as holder_can_match  -- proxy playoff
from val v
left join paid p    on v.player_key = p.player_key
left join fa_bound fb on v.player_key = fb.player_key
left join strength s  on fb.franchise_id = s.franchise_id
where p.player_key is null           -- não está contratado
order by fit_score desc
