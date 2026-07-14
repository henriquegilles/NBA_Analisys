-- fct_my_roster
-- Grain: 1 row per player on my roster (Bandeja de 3).
--
-- Links the roster (seed my_roster, D-02/Phase 2) to the per-category NBA
-- valuation (fct_player_fantasy_value_season) and to the fantasy contracts
-- (seed fantasy_contracts, D-18). A player with no 2025-26 NBA stats
-- (rookie/prospect) gets `has_nba_value` = false and NULL z-scores → check
-- scouting (Domain B). Base for the team strengths/weaknesses profile (D-17)
-- and the cap situation.

with roster as (
    select
        trim("player_name"::text)              as player_name,
        trim("positions"::text)                as positions,
        nullif(trim("is_rookie"::text), '')::int as is_rookie
    from {{ ref('my_roster') }}
),

contracts as (
    select
        trim("player_name"::text)                   as player_name,
        nullif(trim("salary_y1"::text), '')::bigint as salary_y1,
        nullif(trim("salary_y2"::text), '')::bigint as salary_y2,
        nullif(trim("salary_y3"::text), '')::bigint as salary_y3
    from {{ ref('fantasy_contracts') }}
),

value as (
    select
        player_name, games_played, minutes_per_game, is_reference_pool,
        pts_pg, trb_pg, ast_pg, stocks_pg, three_p_pg, plus_minus_pg, tov_pg,
        z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov, z_total
    from {{ ref('fct_player_fantasy_value_season') }}
)

select
    r.player_name,
    r.positions,
    r.is_rookie,
    (v.player_name is not null)              as has_nba_value,

    -- NBA valuation (last season) — NULL if rookie/no stats
    v.games_played,
    v.minutes_per_game,
    v.pts_pg, v.trb_pg, v.ast_pg, v.stocks_pg, v.three_p_pg, v.plus_minus_pg, v.tov_pg,
    v.z_pts, v.z_trb, v.z_ast, v.z_stocks, v.z_three_p, v.z_plus_minus, v.z_tov,
    v.z_total,

    -- Fantasy contracts (cap)
    c.salary_y1,
    c.salary_y2,
    c.salary_y3

from roster r
left join value v     on lower(v.player_name) = lower(r.player_name)
left join contracts c on lower(c.player_name) = lower(r.player_name)
