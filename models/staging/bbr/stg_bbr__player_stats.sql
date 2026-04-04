-- stg_bbr__player_stats
-- Per-game statistical lines scraped from BBR.
-- Players traded mid-season appear multiple times:
--   one "TOT" row (season aggregate) + one row per team.
-- The intermediate layer handles de-duplication.

with source as (
    select * from {{ ref('players_stats') }}
),

cleaned as (
    select
        trim("Player")                                    as player_name,
        upper(trim("Team"))                               as team_abbr,
        upper(trim("Pos"))                                as position,
        nullif(trim("Age"::text),         '')::integer    as age,
        nullif(trim("G"::text),           '')::integer    as games_played,
        nullif(trim("GS"::text),          '')::integer    as games_started,
        nullif(trim("MP"::text),          '')::numeric(6,1) as minutes_per_game,

        nullif(trim("FG"::text),          '')::numeric(5,1) as fg_per_game,
        nullif(trim("FGA"::text),         '')::numeric(5,1) as fga_per_game,
        nullif(trim("fg_pct"::text),      '')::numeric(5,3) as fg_pct,

        nullif(trim("three_p"::text),     '')::numeric(5,1) as three_pt_per_game,
        nullif(trim("three_pa"::text),    '')::numeric(5,1) as three_pt_attempted,
        nullif(trim("three_p_pct"::text), '')::numeric(5,3) as three_pt_pct,

        nullif(trim("two_p"::text),       '')::numeric(5,1) as two_pt_per_game,
        nullif(trim("two_pa"::text),      '')::numeric(5,1) as two_pt_attempted,
        nullif(trim("two_p_pct"::text),   '')::numeric(5,3) as two_pt_pct,

        nullif(trim("efg_pct"::text),     '')::numeric(5,3) as efg_pct,

        nullif(trim("FT"::text),          '')::numeric(5,1) as ft_per_game,
        nullif(trim("FTA"::text),         '')::numeric(5,1) as fta_per_game,
        nullif(trim("ft_pct"::text),      '')::numeric(5,3) as ft_pct,

        nullif(trim("ORB"::text),         '')::numeric(5,1) as off_reb_per_game,
        nullif(trim("DRB"::text),         '')::numeric(5,1) as def_reb_per_game,
        nullif(trim("TRB"::text),         '')::numeric(5,1) as total_reb_per_game,

        nullif(trim("AST"::text),         '')::numeric(5,1) as assists_per_game,
        nullif(trim("STL"::text),         '')::numeric(5,1) as steals_per_game,
        nullif(trim("BLK"::text),         '')::numeric(5,1) as blocks_per_game,
        nullif(trim("TOV"::text),         '')::numeric(5,1) as turnovers_per_game,
        nullif(trim("PF"::text),          '')::numeric(5,1) as personal_fouls_per_game,
        nullif(trim("PTS"::text),         '')::numeric(5,1) as points_per_game

    from source
    where trim("Player") != 'Player'
)

select * from cleaned
