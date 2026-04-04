-- int_players__deduped
-- Resolves the traded-player problem from BBR data.
--
-- BBR inserts an aggregate row for every player traded mid-season,
-- plus one row per team they played for. For roster purposes we want exactly
-- one row per player:
--   - If the player was NOT traded  → keep their single team row.
--   - If the player WAS traded      → keep only the aggregate row (2TM, 3TM …)
--     and drop the per-team rows so we don't double-count them.
--
-- Note: BBR historically used "TOT" for this aggregate. Since the 2024-25
-- season they switched to "NTM" format (2TM, 3TM, etc.) matching the number
-- of teams. We match both patterns with a regex to stay forward-compatible.
--
-- The final team assignment for traded players is resolved in dim_player
-- by joining back to stg_bbr__player_stats on the per-team rows.

with players as (
    select * from {{ ref('stg_bbr__players') }}
),

-- Tag players who have a multi-team aggregate row
traded_players as (
    select distinct player_name
    from players
    where team_abbr = 'TOT'
       or team_abbr ~ '^\d+TM$'
),

deduped as (
    select p.*
    from players p
    left join traded_players t using (player_name)
    where
        -- Keep everyone who was NOT traded
        t.player_name is null
        -- For traded players keep only the aggregate row
        or p.team_abbr = 'TOT'
        or p.team_abbr ~ '^\d+TM$'
)

select * from deduped
