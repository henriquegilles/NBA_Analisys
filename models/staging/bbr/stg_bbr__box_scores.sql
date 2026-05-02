-- stg_bbr__box_scores
-- Per-player per-game basic box score stats.
-- Grain: one row per player × game.
-- home_away: 'home' or 'away'

with source as (
    select * from {{ ref('box_scores') }}
),

cleaned as (
    select
        trim("game_id")                                          as game_id,
        "game_date"::date                                        as game_date,
        upper(trim("team"))                                      as team_abbr,
        trim("home_away")                                        as home_away,
        trim("Player")                                           as player_name,

        -- Minutes played: BBR formats as "MM:SS" — keep as text, parse in marts
        trim("MP"::text)                                         as minutes_played_str,

        nullif(trim("FG"::text),         '')::numeric(5,1)       as fg,
        nullif(trim("FGA"::text),        '')::numeric(5,1)       as fga,
        nullif(trim("fg_pct"::text),     '')::numeric(5,3)       as fg_pct,
        nullif(trim("three_p"::text),    '')::numeric(5,1)       as three_p,
        nullif(trim("three_pa"::text),   '')::numeric(5,1)       as three_pa,
        nullif(trim("three_p_pct"::text),'')::numeric(5,3)       as three_p_pct,
        nullif(trim("FT"::text),         '')::numeric(5,1)       as ft,
        nullif(trim("FTA"::text),        '')::numeric(5,1)       as fta,
        nullif(trim("ft_pct"::text),     '')::numeric(5,3)       as ft_pct,
        nullif(trim("ORB"::text),        '')::numeric(5,1)       as orb,
        nullif(trim("DRB"::text),        '')::numeric(5,1)       as drb,
        nullif(trim("TRB"::text),        '')::numeric(5,1)       as trb,
        nullif(trim("AST"::text),        '')::numeric(5,1)       as ast,
        nullif(trim("STL"::text),        '')::numeric(5,1)       as stl,
        nullif(trim("BLK"::text),        '')::numeric(5,1)       as blk,
        nullif(trim("TOV"::text),        '')::numeric(5,1)       as tov,
        nullif(trim("PF"::text),         '')::numeric(5,1)       as pf,
        nullif(trim("PTS"::text),        '')::numeric(5,1)       as pts,
        nullif(trim("plus_minus"::text), '')::integer            as plus_minus

    from source
    where "Player" is not null
      and trim("Player") != ''
)

select * from cleaned
