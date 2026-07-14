-- int_player_advanced_stats__deduped
-- De-duplicates traded players in the advanced stats table,
-- per season and season_type independently.
--
-- BBR includes one aggregate row ("TOT" / "2TM" / "3TM") for players
-- traded mid-season. We keep only that aggregate row and discard the
-- per-team rows — same logic as int_player_stats__season_totals.

with stats as (
    select * from {{ ref('stg_bbr__player_advanced_stats') }}
),

traded_players as (
    select distinct player_name, season, season_type
    from stats
    where team_abbr = 'TOT'
       or team_abbr ~ '^\d+TM$'
),

deduped as (
    select s.*
    from stats s
    left join traded_players t
        using (player_name, season, season_type)
    where
        t.player_name is null
        or s.team_abbr = 'TOT'
        or s.team_abbr ~ '^\d+TM$'
)

select * from deduped
