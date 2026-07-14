-- stg_bbr__player_advanced_stats
-- Advanced statistical lines scraped from BBR.
-- Contains both regular season and playoff rows, distinguished by season_type.
-- Traded players appear multiple times; deduplication happens in the intermediate layer.

with source as (
    select * from {{ ref('players_advanced_stats') }}
),

cleaned as (
    select
        trim("Player")                                        as player_name,
        {{ normalize_team_abbr('"Team"') }}                   as team_abbr,
        upper(trim("Pos"))                                    as position,
        nullif(trim("Age"::text),         '')::integer        as age,
        nullif(trim("G"::text),           '')::integer        as games_played,
        nullif(trim("MP"::text),          '')::integer        as minutes_played,

        -- Efficiency
        nullif(trim("PER"::text),         '')::numeric(6,1)   as per,
        nullif(trim("ts_pct"::text),      '')::numeric(5,3)   as ts_pct,
        nullif(trim("three_p_ar"::text),  '')::numeric(5,3)   as three_p_ar,
        nullif(trim("ftr"::text),         '')::numeric(5,3)   as ftr,

        -- Rebounding rates
        nullif(trim("orb_pct"::text),     '')::numeric(5,1)   as orb_pct,
        nullif(trim("drb_pct"::text),     '')::numeric(5,1)   as drb_pct,
        nullif(trim("trb_pct"::text),     '')::numeric(5,1)   as trb_pct,

        -- Playmaking / defense rates
        nullif(trim("ast_pct"::text),     '')::numeric(5,1)   as ast_pct,
        nullif(trim("stl_pct"::text),     '')::numeric(5,1)   as stl_pct,
        nullif(trim("blk_pct"::text),     '')::numeric(5,1)   as blk_pct,
        nullif(trim("tov_pct"::text),     '')::numeric(5,1)   as tov_pct,
        nullif(trim("usg_pct"::text),     '')::numeric(5,1)   as usg_pct,

        -- Win Shares
        nullif(trim("OWS"::text),         '')::numeric(6,1)   as offensive_win_shares,
        nullif(trim("DWS"::text),         '')::numeric(6,1)   as defensive_win_shares,
        nullif(trim("WS"::text),          '')::numeric(6,1)   as win_shares,
        nullif(trim("ws_per_48"::text),   '')::numeric(6,3)   as ws_per_48,

        -- Box Plus/Minus
        nullif(trim("OBPM"::text),        '')::numeric(6,1)   as obpm,
        nullif(trim("DBPM"::text),        '')::numeric(6,1)   as dbpm,
        nullif(trim("BPM"::text),         '')::numeric(6,1)   as bpm,
        nullif(trim("VORP"::text),        '')::numeric(6,1)   as vorp,

        -- Season identifiers
        trim("season"::text)                                  as season,
        trim("season_type"::text)                             as season_type

    from source
    where trim("Player") != 'Player'
)

select * from cleaned
