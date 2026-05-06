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

        -- Game context (normaliza BRK/CHO/PHO para BKN/CHA/PHX)
        "game_date"::date                                           as game_date,
        {{ normalize_team_abbr('"team"') }}                         as team_abbr,
        {{ normalize_team_abbr('"opponent"') }}                     as opponent_abbr,
        trim("home_away")                                           as home_away,

        -- Result: BBR uses "W (+12)"/"L (-5)" or "W, 128-110"/"L, 109-119" formats
        case
            when trim("game_result") ilike 'W%' then 'W'
            when trim("game_result") ilike 'L%' then 'L'
            else null
        end                                                         as result,

        -- Extract point differential — handles both BBR result formats:
        --   "W (+12)" / "L (-5)"  → diff is the number in parentheses
        --   "W, 128-110"          → diff = first score - second score
        case
            when trim("game_result") ~ '\([+-]?\d+\)' then
                (regexp_match(trim("game_result"), '\(([+-]?\d+)\)'))[1]::integer
            when trim("game_result") ~ '\d+-\d+' then
                (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[1]::integer
                - (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[2]::integer
            else null
        end                                                         as point_diff,

        -- BBR marks starters with '*', non-starters with empty string
        case when trim("games_started"::text) = '*' then 1 else 0 end   as games_started,
        trim("minutes_played"::text)                                as minutes_played_str,
        nullif(trim("minutes_decimal"::text), '')::numeric(6,2)     as minutes_played,

        -- Shooting
        -- nullif + regex guard: handles empty string AND BBR non-play markers ("Suspended", etc.)
        (case when trim("FG"::text)          ~ '^-?[0-9]+\.?[0-9]*$' then trim("FG"::text)          end)::numeric(5,1) as fg,
        (case when trim("FGA"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("FGA"::text)         end)::numeric(5,1) as fga,
        (case when trim("fg_pct"::text)      ~ '^-?[0-9]+\.?[0-9]*$' then trim("fg_pct"::text)      end)::numeric(5,3) as fg_pct,
        (case when trim("three_p"::text)     ~ '^-?[0-9]+\.?[0-9]*$' then trim("three_p"::text)     end)::numeric(5,1) as three_p,
        (case when trim("three_pa"::text)    ~ '^-?[0-9]+\.?[0-9]*$' then trim("three_pa"::text)    end)::numeric(5,1) as three_pa,
        (case when trim("three_p_pct"::text) ~ '^-?[0-9]+\.?[0-9]*$' then trim("three_p_pct"::text) end)::numeric(5,3) as three_p_pct,
        (case when trim("FT"::text)          ~ '^-?[0-9]+\.?[0-9]*$' then trim("FT"::text)          end)::numeric(5,1) as ft,
        (case when trim("FTA"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("FTA"::text)         end)::numeric(5,1) as fta,
        (case when trim("ft_pct"::text)      ~ '^-?[0-9]+\.?[0-9]*$' then trim("ft_pct"::text)      end)::numeric(5,3) as ft_pct,

        -- Rebounds
        (case when trim("ORB"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("ORB"::text)         end)::numeric(5,1) as orb,
        (case when trim("DRB"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("DRB"::text)         end)::numeric(5,1) as drb,
        (case when trim("TRB"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("TRB"::text)         end)::numeric(5,1) as trb,

        -- Other
        (case when trim("AST"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("AST"::text)         end)::numeric(5,1) as ast,
        (case when trim("STL"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("STL"::text)         end)::numeric(5,1) as stl,
        (case when trim("BLK"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("BLK"::text)         end)::numeric(5,1) as blk,
        (case when trim("TOV"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("TOV"::text)         end)::numeric(5,1) as tov,
        (case when trim("PF"::text)          ~ '^-?[0-9]+\.?[0-9]*$' then trim("PF"::text)          end)::numeric(5,1) as pf,
        (case when trim("PTS"::text)         ~ '^-?[0-9]+\.?[0-9]*$' then trim("PTS"::text)         end)::numeric(5,1) as pts,
        (case when trim("game_score"::text)  ~ '^-?[0-9]+\.?[0-9]*$' then trim("game_score"::text)  end)::numeric(6,1) as game_score,
        (case when trim("plus_minus"::text)  ~ '^-?[0-9]+$'          then trim("plus_minus"::text)  end)::integer      as plus_minus

    from source
    where "player_name" is not null
      and trim("player_name") != ''
      and "game_date" is not null
)

select * from cleaned
