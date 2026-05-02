-- fct_player_advanced_stats
-- Grain: one row per player × season × season_type (regular / playoffs).
-- Joins de-duplicated advanced stats with player and team dimension keys.
--
-- season_type values: 'regular' | 'playoffs'
-- season format:      '2025-26'

with stats as (
    select * from {{ ref('int_player_advanced_stats__deduped') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_surrogate_key(['s.player_name', 's.season', 's.season_type']) }} as fact_key,

        -- Foreign keys to dimensions
        dp.player_key,
        dt.team_key,

        -- Degenerate dimensions
        s.player_name,
        s.team_abbr,
        s.position,
        s.season,
        s.season_type,

        -- Volume
        s.games_played,
        s.minutes_played,

        -- Efficiency
        s.per,
        s.ts_pct,
        s.three_p_ar,
        s.ftr,
        s.usg_pct,

        -- Rebounding rates
        s.orb_pct,
        s.drb_pct,
        s.trb_pct,

        -- Playmaking / defense rates
        s.ast_pct,
        s.stl_pct,
        s.blk_pct,
        s.tov_pct,

        -- Win Shares
        s.offensive_win_shares,
        s.defensive_win_shares,
        s.win_shares,
        s.ws_per_48,

        -- Box Plus/Minus
        s.obpm,
        s.dbpm,
        s.bpm,
        s.vorp

    from stats s
    left join dim_player dp using (player_name)
    left join dim_team   dt on s.team_abbr = dt.team_abbr
)

select * from final
