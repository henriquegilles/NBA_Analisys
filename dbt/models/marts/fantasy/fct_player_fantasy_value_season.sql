-- fct_player_fantasy_value_season
-- Grain: 1 row per player. Fantasy value over the FULL SEASON.
--
-- For each of the 7 categories, computes the player's z-score (how many
-- standard deviations above/below the league mean), summable into an aggregate.
-- Turnovers enter inverted: less TOV than the mean → positive z (D-07).
--
-- Reference pool (D-15): "rosterable" players — >= 15 games played
-- AND >= 12 minutes/game. The mean and stddev of each category come ONLY from
-- that pool, preventing low-minute players from distorting the scale.
-- The z-score is computed for EVERYONE; is_reference_pool flags who set the bar.
--
-- Category weights are equal (D-20). We expose both the sum AND the mean of the
-- z-scores (D-22) — the final aggregate choice is deferred.

{% set min_games = 15 %}
{% set min_mpg   = 12 %}

with categories as (
    select * from {{ ref('int_player__fantasy_categories') }}
    where minutes_played is not null      -- only games actually played (drops DNPs)
),

-- Per-game averages for each player over the season
per_player as (
    select
        player_key,
        bbr_id,
        player_name,
        season,
        count(*)              as games_played,
        avg(minutes_played)   as minutes_per_game,
        avg(pts)              as pts_pg,
        avg(trb)              as trb_pg,
        avg(ast)              as ast_pg,
        avg(stocks)           as stocks_pg,
        avg(three_p)          as three_p_pg,
        avg(plus_minus)       as plus_minus_pg,
        avg(tov)              as tov_pg
    from categories
    group by player_key, bbr_id, player_name, season
),

-- Flags who enters the reference calculation (rosterable pool)
flagged as (
    select
        *,
        (games_played >= {{ min_games }} and minutes_per_game >= {{ min_mpg }})
            as is_reference_pool
    from per_player
),

-- Mean and standard deviation of each category, ONLY over the reference pool
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

-- Z-score per category (nullif guards against zero stddev)
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

        -- Keys / identity
        player_key,
        bbr_id,
        player_name,
        season,

        -- Pool context
        games_played,
        minutes_per_game,
        is_reference_pool,

        -- Per-game averages of the 7 categories (z-score input, useful for display)
        pts_pg,
        trb_pg,
        ast_pg,
        stocks_pg,
        three_p_pg,
        plus_minus_pg,
        tov_pg,

        -- Z-score per category
        z_pts,
        z_trb,
        z_ast,
        z_stocks,
        z_three_p,
        z_plus_minus,
        z_tov,

        -- Aggregates (D-22: sum AND mean; final choice deferred)
        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov)
            as z_total,
        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov) / 7.0
            as z_mean

    from z
)

select * from final
