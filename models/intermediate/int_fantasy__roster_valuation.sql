{{ config(materialized='view') }}
-- Meu/liga: cada jogador rosterado × valoração NBA (por nome normalizado).
-- Deriva VA punt-TOV = z_total - z_tov (métrica central do contexto Bandeja de 3).
with roster as (
    select * from {{ ref('stg_fantasy__rosters') }}
),
val as (
    select
        {{ norm_name('player_name') }} as player_key,
        z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov, z_total,
        pts_pg, trb_pg, ast_pg, stocks_pg, three_p_pg, tov_pg
    from {{ ref('fct_player_fantasy_value_season') }}
)
select
    r.franchise_id, r.franchise_name, r.owner_name,
    r.player_name, r.player_key, r.pos_1, r.nba_player_id,
    r.salary_y1_m, r.is_injured, r.is_restricted,
    v.z_pts, v.z_trb as z_reb, v.z_ast, v.z_stocks, v.z_three_p, v.z_plus_minus, v.z_tov,
    v.z_total,
    (v.z_total - v.z_tov)               as va_punt_tov,
    v.pts_pg, v.trb_pg, v.ast_pg, v.three_p_pg,
    (v.player_key is null)              as unmatched  -- novato/sem stats 25-26
from roster r
left join val v on r.player_key = v.player_key
