-- int_player__fantasy_categories
-- Grain: 1 row per player × game.
--
-- Isolates the 7 Bandeja de 3 league categories from the game log and derives
-- STOCKS (stl + blk). Keeps `tov` as a regular category — the inversion
-- ("less is better") is applied in the z-score calculation, not here.
--
-- This is the base for the valuation aggregations (fct_player_fantasy_value_season
-- and _recent). Pure projection: no filtering or aggregation, just slicing and renaming.

with game_log as (
    select * from {{ ref('fct_player_game_log') }}
),

final as (
    select
        -- Keys
        game_player_key,
        player_key,
        bbr_id,
        player_name,
        season,

        -- Context
        game_date,
        minutes_played,

        -- The league's 7 categories
        pts,                       -- 1. Points
        trb,                       -- 2. Rebounds
        ast,                       -- 3. Assists
        stl + blk    as stocks,    -- 4. STOCKS = steals + blocks
        three_p,                   -- 5. Threes
        plus_minus,                -- 6. Plus/Minus
        tov,                       -- 7. Turnovers (inverted — handled in the z-score)

        -- STOCKS components kept for traceability
        stl,
        blk

    from game_log
)

select * from final
