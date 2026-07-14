-- stg_bbr__nba_careers
-- Per-game NBA career stats, scraped from the "Career" row of the per_game
-- table on each player page (src/scraping/nba_careers.py). Grain: 1 row per NBA player.
--
-- Why it exists: the `draft` seed only carries career pts/trb/ast; this adds the
-- categories still needed to complete the 6 Bandeja de 3 cats — stl, blk (→stocks),
-- 3PM (fg3) and TOV. Joined in int_prospect__nba_bridge on the `bbr_id` key
-- (NBA slug), which the draft seed now exposes as `nba_bbr_id`.

with source as (
    select * from {{ ref('nba_player_careers') }}
),

cleaned as (
    select
        nullif(trim("bbr_id"::text), '')               as bbr_id,
        nullif(trim("player_name"::text), '')          as player_name,

        nullif(trim("career_games"::text), '')::integer as career_games,
        nullif(trim("pg_pts"::text), '')::numeric(5,1)  as pg_pts,
        nullif(trim("pg_trb"::text), '')::numeric(5,1)  as pg_trb,
        nullif(trim("pg_ast"::text), '')::numeric(5,1)  as pg_ast,
        nullif(trim("pg_stl"::text), '')::numeric(5,1)  as pg_stl,
        nullif(trim("pg_blk"::text), '')::numeric(5,1)  as pg_blk,
        nullif(trim("pg_fg3"::text), '')::numeric(5,1)  as pg_fg3,
        nullif(trim("pg_tov"::text), '')::numeric(5,1)  as pg_tov

    from source
    where nullif(trim("bbr_id"::text), '') is not null
)

select * from cleaned
