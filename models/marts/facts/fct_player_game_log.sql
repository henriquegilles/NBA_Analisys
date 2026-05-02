-- fct_player_game_log
-- Grain: one row per player × game.
-- Source: BBR individual game log pages (not box score index).
--
-- Richer than box score scraping:
--   • opponent_abbr  → matchup analysis, back-to-back detection
--   • result / point_diff → performance in wins vs losses
--   • game_score     → Hollinger single-number efficiency per game
--   • home_away      → home/away splits
--
-- Typical use cases:
--   SELECT player_name, avg(pts), avg(game_score)
--   FROM fct_player_game_log
--   WHERE season = '2025-26' AND result = 'W'
--   GROUP BY 1 ORDER BY 2 DESC

with logs as (
    select * from {{ ref('stg_bbr__player_gamelogs') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_surrogate_key(['l.bbr_id', 'l.game_date', 'l.team_abbr']) }} as game_player_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,
        opp.team_key                                    as opponent_team_key,

        -- Identifiers
        l.bbr_id,
        l.player_name,
        l.season,

        -- Game context
        l.game_date,
        extract(year from l.game_date)::integer         as game_year,
        l.team_abbr,
        l.opponent_abbr,
        l.home_away,
        l.result,
        l.point_diff,
        l.games_started,

        -- Playing time
        l.minutes_played,       -- decimal (e.g. 32.23)
        l.minutes_played_str,   -- original string "MM:SS" for display

        -- Shooting
        l.fg,
        l.fga,
        l.fg_pct,
        l.three_p,
        l.three_pa,
        l.three_p_pct,
        l.ft,
        l.fta,
        l.ft_pct,

        -- Rebounds
        l.orb,
        l.drb,
        l.trb,

        -- Other box score stats
        l.ast,
        l.stl,
        l.blk,
        l.tov,
        l.pf,
        l.pts,

        -- Composite metrics
        l.game_score,           -- Hollinger: pts + 0.4*fg - 0.7*fga - 0.4*(fta-ft) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov
        l.plus_minus

    from logs l
    left join dim_player dp using (player_name)
    left join dim_team   dt  on l.team_abbr     = dt.team_abbr
    left join dim_team   opp on l.opponent_abbr = opp.team_abbr
)

select * from final
