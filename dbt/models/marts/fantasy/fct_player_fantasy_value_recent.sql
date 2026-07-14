-- fct_player_fantasy_value_recent
-- Grain: 1 row per player. Fantasy value over RECENT FORM (last 15 games).
--
-- Same z-score logic as fct_player_fantasy_value_season, but the window is
-- only each player's last N=15 games (D-16). The reference pool is
-- RECOMPUTED over that window (D-19) — means and stddevs come from the
-- last-15-game averages, not the full season.
--
-- Pool floor: at least 10 of the last 15 games played AND >= 12 min/game
-- (the window is short, so we require real presence for the form to be reliable).
-- Equal weights (D-20); exposes both sum AND mean (D-22).

{% set window_n  = 15 %}
{% set min_games = 10 %}
{% set min_mpg   = 12 %}

with categories as (
    select * from {{ ref('int_player__fantasy_categories') }}
    where minutes_played is not null      -- only games actually played (drops DNPs)
),

-- Ranks each player's games from most recent to oldest
ranked as (
    select
        *,
        row_number() over (partition by bbr_id order by game_date desc) as game_recency
    from categories
),

-- Keeps only the last N games per player
recent_games as (
    select * from ranked
    where game_recency <= {{ window_n }}
),

-- Per-game averages for each player WITHIN the recent window
per_player as (
    select
        player_key,
        bbr_id,
        player_name,
        season,
        count(*)              as games_in_window,
        avg(minutes_played)   as minutes_per_game,
        avg(pts)              as pts_pg,
        avg(trb)              as trb_pg,
        avg(ast)              as ast_pg,
        avg(stocks)           as stocks_pg,
        avg(three_p)          as three_p_pg,
        avg(plus_minus)       as plus_minus_pg,
        avg(tov)              as tov_pg
    from recent_games
    group by player_key, bbr_id, player_name, season
),

flagged as (
    select
        *,
        (games_in_window >= {{ min_games }} and minutes_per_game >= {{ min_mpg }})
            as is_reference_pool
    from per_player
),

-- Reference pool recomputed over the recent-window averages
pool_stats as (
    select
        avg(pts_pg)        as pts_mean,        stddev_samp(pts_pg)        as pts_std,
        avg(trb_pg)        as trb_mean,        stddev_samp(trb_pg)        as trb_std,
        avg(ast_pg)        as ast_mean,        stddev_samp(ast_pg)        as ast_std,
        avg(stocks_pg)     as stocks_mean,     stddev_samp(stocks_pg)     as stocks_std,
        avg(three_p_pg)    as three_p_mean,    stddev_samp(three_p_pg)    as three_p_std,
        avg(plus_minus_pg) as plus_minus_mean, stddev_samp(plus_minus_pg) as plus_minus_std,
        avg(tov_pg)        as tov_mean,        stddev_samp(tov_pg)        as tov_std
    from flagged
    where is_reference_pool
),

z as (
    select
        f.*,
        (f.pts_pg        - p.pts_mean)        / nullif(p.pts_std, 0)        as z_pts,
        (f.trb_pg        - p.trb_mean)        / nullif(p.trb_std, 0)        as z_trb,
        (f.ast_pg        - p.ast_mean)        / nullif(p.ast_std, 0)        as z_ast,
        (f.stocks_pg     - p.stocks_mean)     / nullif(p.stocks_std, 0)     as z_stocks,
        (f.three_p_pg    - p.three_p_mean)    / nullif(p.three_p_std, 0)    as z_three_p,
        (f.plus_minus_pg - p.plus_minus_mean) / nullif(p.plus_minus_std, 0) as z_plus_minus,
        -- Turnovers inverted
        (p.tov_mean      - f.tov_pg)          / nullif(p.tov_std, 0)        as z_tov
    from flagged f
    cross join pool_stats p
),

final as (
    select
        {{ generate_id(['bbr_id', 'season']) }}  as fantasy_value_key,

        player_key,
        bbr_id,
        player_name,
        season,

        games_in_window,
        minutes_per_game,
        is_reference_pool,

        pts_pg,
        trb_pg,
        ast_pg,
        stocks_pg,
        three_p_pg,
        plus_minus_pg,
        tov_pg,

        z_pts,
        z_trb,
        z_ast,
        z_stocks,
        z_three_p,
        z_plus_minus,
        z_tov,

        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov)
            as z_total,
        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov) / 7.0
            as z_mean

    from z
)

select * from final
