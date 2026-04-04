-- int_player_stats__season_totals
-- Same traded-player de-duplication applied to the stats table.
--
-- For traded players the aggregate row (2TM, 3TM, TOT) already contains
-- the full-season per-game averages weighted by games played on each team —
-- so keeping it is the correct statistical choice for season-level analysis.
--
-- See int_players__deduped for the full explanation of the NTM vs TOT history.

with stats as (
    select * from {{ ref('stg_bbr__player_stats') }}
),

traded_players as (
    select distinct player_name
    from stats
    where team_abbr = 'TOT'
       or team_abbr ~ '^\d+TM$'
),

deduped as (
    select s.*
    from stats s
    left join traded_players t using (player_name)
    where
        t.player_name is null
        or s.team_abbr = 'TOT'
        or s.team_abbr ~ '^\d+TM$'
)

select * from deduped
