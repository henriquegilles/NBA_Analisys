-- stg_bbr__player_gamelogs
-- Per-player per-game stats scraped from BBR individual game log pages.
-- Grain: one row per player × game.
--
-- Differences from box score scraping:
--   • Includes opponent, game result, Game Score (GmSc)
--   • minutes_decimal already converted to numeric (MM:SS → decimal)
--   • Source is ~500 player pages instead of ~1,230 game pages

with source as (
    select * from {{ ref('player_gamelogs') }}
),

cleaned as (
    select
        trim("bbr_id")                                              as bbr_id,
        trim("player_name")                                         as player_name,
        trim("season"::text)                                        as season,

        -- Game context
        "Date"::date                                                as game_date,
        upper(trim("team"))                                         as team_abbr,
        upper(trim("opponent"))                                     as opponent_abbr,
        trim("home_away")                                           as home_away,

        -- Result: BBR stores as "W (+12)" or "L (-5)"
        case
            when trim("game_result") ilike 'W%' then 'W'
            when trim("game_result") ilike 'L%' then 'L'
            else null
        end                                                         as result,

        nullif(
            regexp_replace(trim("game_result"), '[^0-9\-\+]', '', 'g'), ''
        )::integer                                                  as point_diff,

        nullif(trim("games_started"::text), '')::integer            as games_started,
        trim("minutes_played"::text)                                as minutes_played_str,
        nullif(trim("minutes_decimal"::text), '')::numeric(6,2)     as minutes_played,

        -- Shooting
        nullif(trim("FG"::text),         '')::numeric(5,1)          as fg,
        nullif(trim("FGA"::text),        '')::numeric(5,1)          as fga,
        nullif(trim("fg_pct"::text),     '')::numeric(5,3)          as fg_pct,
        nullif(trim("three_p"::text),    '')::numeric(5,1)          as three_p,
        nullif(trim("three_pa"::text),   '')::numeric(5,1)          as three_pa,
        nullif(trim("three_p_pct"::text),'')::numeric(5,3)          as three_p_pct,
        nullif(trim("ft"::text),         '')::numeric(5,1)          as ft,
        nullif(trim("fta"::text),        '')::numeric(5,1)          as fta,
        nullif(trim("ft_pct"::text),     '')::numeric(5,3)          as ft_pct,

        -- Rebounds
        nullif(trim("orb"::text),        '')::numeric(5,1)          as orb,
        nullif(trim("drb"::text),        '')::numeric(5,1)          as drb,
        nullif(trim("trb"::text),        '')::numeric(5,1)          as trb,

        -- Other
        nullif(trim("ast"::text),        '')::numeric(5,1)          as ast,
        nullif(trim("stl"::text),        '')::numeric(5,1)          as stl,
        nullif(trim("blk"::text),        '')::numeric(5,1)          as blk,
        nullif(trim("tov"::text),        '')::numeric(5,1)          as tov,
        nullif(trim("pf"::text),         '')::numeric(5,1)          as pf,
        nullif(trim("pts"::text),        '')::numeric(5,1)          as pts,
        nullif(trim("game_score"::text), '')::numeric(6,1)          as game_score,
        nullif(trim("plus_minus"::text), '')::integer               as plus_minus

    from source
    where "player_name" is not null
      and trim("player_name") != ''
      and "Date" is not null
)

select * from cleaned
