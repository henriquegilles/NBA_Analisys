-- int_games__from_gamelogs
-- Derives unique game entities from the individual game logs.
-- Grain: 1 row per game (game_date × home_team_abbr).
--
-- Since the BBR game log is per player, each game appears ~12 times per team.
-- We use DISTINCT here to extract only the GAME attributes, not the player's.
--
-- Home/away logic:
--   home_away = 'home' → team_abbr is the home team
--   home_away = 'away' → team_abbr is the visitor; opponent_abbr is the home team
--
-- Limitation: point_diff and result come from the player's point of view and
-- are converted to the home team's perspective.

with logs as (
    select * from {{ ref('stg_bbr__player_gamelogs') }}
    where home_away is not null
      and team_abbr is not null
      and opponent_abbr is not null
),

games as (
    select distinct
        game_date,
        season,

        case when home_away = 'home' then team_abbr
             else opponent_abbr
        end                                                     as home_team_abbr,

        case when home_away = 'away' then team_abbr
             else opponent_abbr
        end                                                     as away_team_abbr,

        -- Home team result (W = home team won)
        case
            when home_away = 'home' and result = 'W' then 'W'
            when home_away = 'home' and result = 'L' then 'L'
            when home_away = 'away' and result = 'W' then 'L'
            when home_away = 'away' and result = 'L' then 'W'
        end                                                     as home_result,

        -- Margin from the home team's perspective (positive = home team won)
        case
            when home_away = 'home' then point_diff
            when home_away = 'away' then -point_diff
        end                                                     as home_point_diff

    from logs
)

select * from games
