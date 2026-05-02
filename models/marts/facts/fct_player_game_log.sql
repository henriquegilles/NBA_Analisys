-- fct_player_game_log
-- Grain: one row per player × game.
-- Central fact for per-game performance analysis:
--   • single-game scoring/efficiency breakdowns
--   • player hot/cold streaks
--   • home vs away splits
--   • playoff vs regular season game comparison (when combined with fct_player_advanced_stats)

with box as (
    select * from {{ ref('stg_bbr__box_scores') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_surrogate_key(['b.game_id', 'b.player_name']) }} as game_player_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,

        -- Game identifiers
        b.game_id,
        b.game_date,
        extract(year from b.game_date)::integer                  as game_year,

        -- Context
        b.player_name,
        b.team_abbr,
        b.home_away,

        -- Playing time (raw string kept; convert to minutes in BI tool or add computed column)
        b.minutes_played_str,

        -- Shooting
        b.fg,
        b.fga,
        b.fg_pct,
        b.three_p,
        b.three_pa,
        b.three_p_pct,
        b.ft,
        b.fta,
        b.ft_pct,

        -- Rebounds
        b.orb,
        b.drb,
        b.trb,

        -- Other
        b.ast,
        b.stl,
        b.blk,
        b.tov,
        b.pf,
        b.pts,
        b.plus_minus

    from box b
    left join dim_player dp using (player_name)
    left join dim_team   dt on b.team_abbr = dt.team_abbr
)

select * from final
