-- stg_cbb__player_season
-- Cleaned college player-season lines scraped from College Basketball Reference.
-- Grain: 1 row per player × college season (key cbb_id × season).
--
-- Source: seed college_player_seasons.csv (scraper src/scraping/college.py,
-- collected per school × season — decision D-27). Per-40-min comes ready-made
-- from the site (D-10), so here we only clean and type; no normalization math.
--
-- `class` is kept as a clean string (FR/SO/JR/SR); the ordinal mapping
-- (age proxy, D-26) and feature assembly happen in the intermediate layer.
-- `conf_abbr` is usually null in the per-school scrape (conference implied by
-- the school) — column kept for when the source is a player page.

with source as (
    select * from {{ ref('college_player_seasons') }}
),

cleaned as (
    select
        -- Identity
        trim("cbb_id"::text)                                  as cbb_id,
        trim("player"::text)                                  as player_name,
        trim("school"::text)                                  as school,
        trim("season"::text)                                  as season,
        nullif(trim("conf_abbr"::text), '')                   as conf_abbr,

        -- Prospect context
        upper(nullif(trim("class"::text), ''))                as class,        -- FR/SO/JR/SR (age proxy, D-26)
        upper(nullif(trim("pos"::text), ''))                  as position,
        nullif(trim("height"::text), '')                      as height,       -- "6-7" (text)
        nullif(trim("weight"::text), '')::integer             as weight_lb,
        nullif(substring(trim("rsci"::text) from '^\d+'), '')::integer
                                                              as rsci_rank,    -- recruit rank (top-100); null = unranked

        -- Volume
        nullif(trim("games"::text), '')::integer              as games,
        nullif(trim("games_started"::text), '')::integer      as games_started,
        nullif(trim("mp"::text), '')::integer                 as minutes_played,

        -- The league's 6 categories, per-40-min (no +/- in college — D-10)
        nullif(trim("pts_per_min"::text), '')::numeric(6,1)   as pts_per_40,
        nullif(trim("trb_per_min"::text), '')::numeric(6,1)   as trb_per_40,
        nullif(trim("ast_per_min"::text), '')::numeric(6,1)   as ast_per_40,
        nullif(trim("stl_per_min"::text), '')::numeric(6,1)   as stl_per_40,   -- STOCKS component
        nullif(trim("blk_per_min"::text), '')::numeric(6,1)   as blk_per_40,   -- STOCKS component
        nullif(trim("fg3_per_min"::text), '')::numeric(6,1)   as three_p_per_40,
        nullif(trim("tov_per_min"::text), '')::numeric(6,1)   as tov_per_40,   -- inverted — handled in the downstream z-score

        -- Efficiency (context)
        nullif(trim("ts_pct"::text), '')::numeric(5,3)        as ts_pct,
        nullif(trim("efg_pct"::text), '')::numeric(5,3)       as efg_pct,
        nullif(trim("fg3_pct"::text), '')::numeric(5,3)       as fg3_pct,
        nullif(trim("ft_pct"::text), '')::numeric(5,3)        as ft_pct,
        nullif(trim("usg_pct"::text), '')::numeric(5,1)       as usg_pct,

        -- Advanced (context bonus)
        nullif(trim("per"::text), '')::numeric(6,1)           as per,
        nullif(trim("ws"::text), '')::numeric(6,1)            as win_shares,
        nullif(trim("obpm"::text), '')::numeric(6,1)          as obpm,
        nullif(trim("dbpm"::text), '')::numeric(6,1)          as dbpm,
        nullif(trim("bpm"::text), '')::numeric(6,1)           as bpm,

        -- Team context (D-27 — strength of schedule, team level)
        nullif(trim("team_sos"::text), '')::numeric(6,2)      as team_sos,
        nullif(trim("team_srs"::text), '')::numeric(6,2)      as team_srs

    from source
    where trim("player"::text) != 'Player'
)

select * from cleaned
