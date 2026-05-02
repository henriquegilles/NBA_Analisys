-- stg_bbr__players
-- One row per player-team stint scraped from BBR per-game page.
-- Cleans types and normalises text; no business logic here.

with source as (
    select * from {{ ref('players') }}
),

cleaned as (
    select
        trim("Player")                          as player_name,
        trim("bbr_id"::text)                    as bbr_id,
        upper(trim("Team"))                     as team_abbr,
        upper(trim("Pos"))                      as position,
        nullif(trim("Age"::text), '')::integer  as age,
        trim("season"::text)                    as season
    from source
    -- BBR repeats the header row on paginated tables
    where trim("Player") != 'Player'
)

select * from cleaned
