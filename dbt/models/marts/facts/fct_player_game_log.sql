-- fct_player_game_log
-- Grain: 1 row per player × game.
-- Source: BBR individual game log pages.
--
-- game_key → FK to dim_game (the game entity: who played whom, game result)
-- player_key → FK via bbr_id (stable — does not break on BBR name corrections)
--
-- Player attributes kept as degenerate dimensions (Kimball):
--   home_away, result, games_started — they are from the player's point of view
--   and frequently queried without needing a JOIN to dim_game.
--
-- point_diff was moved to dim_game (a game measure, not a player measure).

with logs as (
    select * from {{ ref('stg_bbr__player_gamelogs') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

dim_game as (
    select * from {{ ref('dim_game') }}
),

final as (
    select
        -- PK: bbr_id + game_date — a player does not play twice on the same day
        {{ generate_id(['l.bbr_id', 'l.game_date']) }}               as game_player_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,
        opp.team_key                                        as opponent_team_key,
        dg.game_key,

        -- Natural identifiers
        l.bbr_id,
        l.player_name,
        l.season,

        -- Game context (degenerate dimensions — from the player's point of view)
        l.game_date,
        l.team_abbr,
        l.opponent_abbr,
        l.home_away,                -- 'home' | 'away' (player's perspective)
        l.result,                   -- 'W' | 'L'       (player's team perspective)
        l.games_started,            -- 1 = starter | 0 = bench

        -- Playing time
        l.minutes_played,           -- decimal (e.g. 32.23)
        l.minutes_played_str,       -- original "MM:SS" string for display

        -- Field goals
        l.fg,
        l.fga,
        l.fg_pct,
        l.three_p,
        l.three_pa,
        l.three_p_pct,

        -- Free throws
        l.ft,
        l.fta,
        l.ft_pct,

        -- Rebounds
        l.orb,
        l.drb,
        l.trb,

        -- Other
        l.ast,
        l.stl,
        l.blk,
        l.tov,
        l.pf,
        l.pts,

        -- Composite metric
        -- Game Score (Hollinger): summarizes the performance in one number
        -- pts + 0.4*fg − 0.7*fga − 0.4*(fta−ft) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk − 0.4*pf − tov
        l.game_score,
        l.plus_minus

    from logs l
    left join dim_player dp on l.bbr_id        = dp.bbr_id
    left join dim_team   dt  on l.team_abbr     = dt.team_abbr
    left join dim_team   opp on l.opponent_abbr = opp.team_abbr
    left join dim_game   dg  on l.game_date     = dg.game_date
        and (
            (l.home_away = 'home' and l.team_abbr     = dg.home_team_abbr)
            or
            (l.home_away = 'away' and l.opponent_abbr = dg.home_team_abbr)
        )
)

select * from final
