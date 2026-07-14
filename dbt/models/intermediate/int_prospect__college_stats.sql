-- int_prospect__college_stats
-- Grain: player × college season (above the minutes floor).
--
-- Builds the prospect PROFILE for scouting (Domain B): the 6 categories
-- per-40-min + context (seniority, efficiency, usage, strength of schedule,
-- archetype) + TRAJECTORY signal (evolution vs. the previous season).
-- It is the base from which both historical prospects (→ NBA outcomes) and
-- the current class (→ comps) are derived.
--
-- Decisions applied:
--   D-10  per-40 comes ready-made from staging (no math here).
--   D-26  `class` → ordinal `class_rank` (FR=1…SR=4), age/seniority proxy.
--   D-28  archetype = G/F/C (CBB Reference only classifies at these 3 levels;
--         the "fine-grained 5 positions" of D-23 does not exist in the source).
--         G→guard, F→wing, C→big.
--   D-24  trajectory = z-score of the per-40 production delta vs. the SAME
--         player's previous season + flag (improving/stable/declining).
--   Minutes floor: cuts walk-ons/garbage time, whose per-40 numbers are noise
--   (extrapolated from very few minutes). Tunable via `min_minutes` below.

{% set min_minutes = 200 %}   {# floor (tunable). Across ~841 rows, <200min ≈ 37% (noise tail). #}
{% set traj_band = 0.5 %}     {# "stable" band in standard deviations of the production delta. #}

with college as (
    select *
    from {{ ref('stg_cbb__player_season') }}
    where minutes_played >= {{ min_minutes }}
),

enriched as (
    select
        -- Identity
        cbb_id,
        player_name,
        school,
        season,

        -- Archetype / position (D-28)
        position,
        case position
            when 'G' then 'guard'
            when 'F' then 'wing'
            when 'C' then 'big'
            else 'unknown'
        end                                                   as archetype,

        -- Seniority (D-26 — age proxy)
        class,
        case class when 'FR' then 1 when 'SO' then 2
                   when 'JR' then 3 when 'SR' then 4 end      as class_rank,

        -- 6 categories per-40 (D-10)
        pts_per_40,
        trb_per_40,
        ast_per_40,
        stl_per_40,
        blk_per_40,
        coalesce(stl_per_40, 0) + coalesce(blk_per_40, 0)     as stocks_per_40,   -- derived category
        three_p_per_40,
        tov_per_40,

        -- Per-40 production composite (trajectory base): counts what helps,
        -- subtracts turnovers. Not the final valuation (the 6-cat z-score comes later).
        coalesce(pts_per_40, 0) + coalesce(trb_per_40, 0) + coalesce(ast_per_40, 0)
          + coalesce(stl_per_40, 0) + coalesce(blk_per_40, 0) + coalesce(three_p_per_40, 0)
          - coalesce(tov_per_40, 0)                           as production_per_40,

        -- Context
        ts_pct,
        usg_pct,
        team_sos,
        rsci_rank,
        minutes_played,
        games
    from college
),

-- Previous season of the SAME player (cbb_id), in chronological order.
-- `season` in 'YYYY-YY' format sorts lexicographically the same as chronologically.
with_prior as (
    select
        *,
        lag(season)             over w as prev_season,
        lag(production_per_40)  over w as prev_production_per_40,
        lag(ts_pct)             over w as prev_ts_pct
    from enriched
    window w as (partition by cbb_id order by season)
),

delta as (
    select
        *,
        production_per_40 - prev_production_per_40 as d_production_per_40,
        ts_pct - prev_ts_pct                       as d_ts_pct
    from with_prior
),

-- Population moments of the delta (only over players with a previous season),
-- used to standardize the trajectory (D-24).
moments as (
    select
        avg(d_production_per_40)         as mu,
        stddev_samp(d_production_per_40) as sd
    from delta
    where prev_season is not null
),

final as (
    select
        d.*,
        case when d.prev_season is null then null
             else (d.d_production_per_40 - m.mu) / nullif(m.sd, 0)
        end as d_production_z,

        case
            when d.prev_season is null                                   then 'sem_historico'
            when (d.d_production_per_40 - m.mu) / nullif(m.sd, 0) >=  {{ traj_band }} then 'melhorando'
            when (d.d_production_per_40 - m.mu) / nullif(m.sd, 0) <= -{{ traj_band }} then 'piorando'
            else 'estavel'
        end as trajectory_flag
    from delta d
    cross join moments m
)

select * from final
