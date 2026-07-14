-- fct_player_season_stats
-- Grain: one row per player per season (current season only).
-- Central fact table joining de-duplicated player stats with
-- player and team dimension keys.
--
-- All rate stats (per-game averages, percentages) come from BBR
-- and are already computed — we don't re-aggregate here.

with stats as (
    select * from {{ ref('int_player_stats__season_totals') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        -- Surrogate key for this fact row
        {{ generate_id(['s.player_name', 's.season']) }}               as fact_key,

        -- Foreign keys to dimensions
        dp.player_key,
        dt.team_key,

        -- Degenerate dimensions (useful for filtering without a join)
        s.player_name,
        s.team_abbr,
        s.position,
        s.season,

        -- Volume stats
        s.games_played,
        s.games_started,
        s.minutes_per_game,

        -- Shooting
        s.fg_per_game,
        s.fga_per_game,
        s.fg_pct,
        s.three_pt_per_game,
        s.three_pt_attempted,
        s.three_pt_pct,
        s.two_pt_per_game,
        s.two_pt_attempted,
        s.two_pt_pct,
        s.efg_pct,

        -- Free throws
        s.ft_per_game,
        s.fta_per_game,
        s.ft_pct,

        -- Rebounds
        s.off_reb_per_game,
        s.def_reb_per_game,
        s.total_reb_per_game,

        -- Other
        s.assists_per_game,
        s.steals_per_game,
        s.blocks_per_game,
        s.turnovers_per_game,
        s.personal_fouls_per_game,
        s.points_per_game

    from stats s
    left join dim_player dp using (player_name)
    left join dim_team   dt on dp.current_team_abbr = dt.team_abbr
)

select * from final
