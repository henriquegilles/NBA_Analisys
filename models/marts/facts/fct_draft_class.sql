-- fct_draft_class
-- Grain: one row per draft pick (draft_year × pick).
-- Immutable pick metadata + career stats snapshot (as of the last scrape).
-- career_stats_as_of marks when the career numbers were loaded — they update
-- each time the draft scraper runs and dbt is rebuilt.

with draft as (
    select * from {{ ref('stg_bbr__draft') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

final as (
    select
        {{ generate_surrogate_key(['d.draft_year', 'd.pick']) }} as draft_pick_key,

        -- Pick info
        d.draft_year,
        d.round,
        d.pick,
        d.team_abbr                                              as drafting_team,
        d.player_name,
        d.college,

        -- FK to dim_player (null when player never played in NBA)
        dp.player_key,

        -- Career volume
        d.career_seasons,
        d.career_games,
        d.career_minutes,
        d.career_points,
        d.career_reb,
        d.career_ast,

        -- Career shooting percentages
        d.career_fg_pct,
        d.career_3p_pct,
        d.career_ft_pct,

        -- Per-game career averages
        d.pg_mp,
        d.pg_pts,
        d.pg_trb,
        d.pg_ast,

        -- Career advanced metrics
        d.win_shares,
        d.ws_per_48,
        d.bpm,
        d.vorp,

        -- Snapshot timestamp — career stats are point-in-time, not immutable
        current_date::date as career_stats_as_of,

        -- Derived: did the pick pan out? (simple proxy: ≥3 seasons played)
        case when coalesce(d.career_seasons, 0) >= 3 then true else false end as reached_3_seasons

    from draft d
    left join dim_player dp on lower(trim(d.player_name)) = lower(trim(dp.player_name))
)

select * from final
