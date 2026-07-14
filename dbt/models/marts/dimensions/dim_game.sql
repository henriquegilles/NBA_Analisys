-- dim_game
-- Grain: 1 row per game.
-- Central game-context entity, separate from player stats.
--
-- Why this matters:
--   Without dim_game, game attributes (result, margin, opponent) are
--   repeated ~24 times in fct_player_game_log (once per player on the floor).
--   That makes COUNT(DISTINCT game_date) incorrect for counting games when
--   two teams play on the same day.
--
-- Source: derived from int_games__from_gamelogs (player game log data).
-- Once box_scores.py is active, this dimension can be enriched
-- with venue, arena_timezone, and game_status.

with games as (
    select * from {{ ref('int_games__from_gamelogs') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_id(['g.game_date', 'g.home_team_abbr']) }}            as game_key,

        -- Dates and season
        g.game_date,
        g.season,
        extract(year from g.game_date)::integer             as game_year,

        -- Teams (FKs to dim_team)
        g.home_team_abbr,
        g.away_team_abbr,
        ht.team_key                                         as home_team_key,
        at_.team_key                                        as away_team_key,

        -- Result from the home team's perspective
        g.home_result,
        g.home_point_diff

        -- Future: venue, arena_timezone, tipoff_utc, game_status, attendance

    from games g
    left join dim_team ht  on g.home_team_abbr = ht.team_abbr
    left join dim_team at_ on g.away_team_abbr = at_.team_abbr
)

select * from final
