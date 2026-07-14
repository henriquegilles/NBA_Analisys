-- fct_prospect_scouting
-- Grain: 1 row per prospect with at least one comp that has an NBA outcome.
--
-- The Domain B PRODUCT: for each prospect, projects the NBA outcome from the
-- outcomes of their comps (D-04). Joins int_prospect__comps (the k neighbors)
-- to fct_college_to_nba_outcomes (which of the comps reached the NBA).
--
-- TWO projections per category (Improvement 2):
--   proj_*            → SIMPLE average of the comps (current default).
--   proj_*_weighted   → inverse-distance WEIGHTED average (a closer comp
--                       weighs more). w_i = 1/(distance_i + ε), ε = median of
--                       the distances (data-driven). NULL-aware per category.
-- Both are kept side by side; the default only changes after a leave-one-out backtest.
--
-- CONFIDENCE signal (Improvement 1, D-33): confidence/coverage_6cat/mean_comp_distance.
-- Thresholds calibrated on the real TERCILES of the mean distance: t33≈1.43, t67≈1.78.

{% set k = 8 %}                {# number of comps per prospect (same as int_prospect__comps) #}
{% set dist_low = 1.43 %}      {# t33 of the mean distance — below = good analogues #}
{% set dist_high = 1.78 %}     {# t67 of the mean distance — above = extrapolation #}

with comps as (
    select prospect_id, prospect_name, prospect_season, prospect_archetype,
           comp_id, comp_rank, used_archetype_fallback, distance
    from {{ ref('int_prospect__comps') }}
),

outcomes as (
    select cbb_id,
           nba_pg_pts, nba_pg_trb, nba_pg_ast,
           nba_pg_stocks, nba_pg_fg3, nba_pg_tov,
           nba_win_shares, nba_vorp
    from {{ ref('fct_college_to_nba_outcomes') }}
),

-- Weighting ε = median of ALL comp distances (data-driven, scale-free).
-- Avoids blow-ups when distance ≈ 0 and controls aggressiveness.
eps as (
    select percentile_cont(0.5) within group (order by distance) as eps
    from comps
),

-- Mean distance over ALL k comps (not just those with an outcome) — base of
-- the confidence signal; it is the population the terciles were calibrated on.
comp_distance as (
    select prospect_id, avg(distance) as mean_comp_distance
    from comps
    group by prospect_id
),

comp_outcomes as (
    -- flat list: 1 row per (prospect × comp that reached the NBA), with the weight.
    select
        c.prospect_id,
        c.prospect_name,
        c.prospect_season,
        c.prospect_archetype,
        c.used_archetype_fallback,
        1.0 / (c.distance + e.eps)                     as w,
        o.nba_pg_pts, o.nba_pg_trb, o.nba_pg_ast,
        o.nba_pg_stocks, o.nba_pg_fg3, o.nba_pg_tov,
        o.nba_win_shares, o.nba_vorp
    from comps c
    join outcomes o on c.comp_id = o.cbb_id        -- only comps that reached the NBA
    cross join eps e
),

aggregated as (
    select
        prospect_id,
        prospect_name,
        prospect_season,
        prospect_archetype,
        bool_or(used_archetype_fallback)              as used_archetype_fallback,
        count(*)                                      as n_comps_with_outcome,
        count(nba_pg_stocks)                          as n_comps_with_6cat,

        -- SIMPLE projection (default). avg() ignores NULL → projects over the
        -- comps whose NBA career has already been scraped.
        round(avg(nba_pg_pts), 1)                     as proj_pg_pts,
        round(avg(nba_pg_trb), 1)                     as proj_pg_trb,
        round(avg(nba_pg_ast), 1)                     as proj_pg_ast,
        round(avg(nba_pg_stocks), 1)                  as proj_pg_stocks,
        round(avg(nba_pg_fg3), 1)                     as proj_pg_fg3,
        round(avg(nba_pg_tov), 1)                     as proj_pg_tov,
        round(avg(nba_win_shares), 1)                 as proj_win_shares,
        round(avg(nba_vorp), 1)                       as proj_vorp,

        -- Inverse-distance WEIGHTED projection (Improvement 2). NULL-aware:
        -- per category, renormalizes the weight only over comps that have it.
        round((sum(w * nba_pg_pts)    filter (where nba_pg_pts    is not null)
             / nullif(sum(w)          filter (where nba_pg_pts    is not null), 0))::numeric, 1) as proj_pg_pts_weighted,
        round((sum(w * nba_pg_trb)    filter (where nba_pg_trb    is not null)
             / nullif(sum(w)          filter (where nba_pg_trb    is not null), 0))::numeric, 1) as proj_pg_trb_weighted,
        round((sum(w * nba_pg_ast)    filter (where nba_pg_ast    is not null)
             / nullif(sum(w)          filter (where nba_pg_ast    is not null), 0))::numeric, 1) as proj_pg_ast_weighted,
        round((sum(w * nba_pg_stocks) filter (where nba_pg_stocks is not null)
             / nullif(sum(w)          filter (where nba_pg_stocks is not null), 0))::numeric, 1) as proj_pg_stocks_weighted,
        round((sum(w * nba_pg_fg3)    filter (where nba_pg_fg3    is not null)
             / nullif(sum(w)          filter (where nba_pg_fg3    is not null), 0))::numeric, 1) as proj_pg_fg3_weighted,
        round((sum(w * nba_pg_tov)    filter (where nba_pg_tov    is not null)
             / nullif(sum(w)          filter (where nba_pg_tov    is not null), 0))::numeric, 1) as proj_pg_tov_weighted
    from comp_outcomes
    group by 1, 2, 3, 4
)

select
    a.*,
    round(d.mean_comp_distance::numeric, 3)           as mean_comp_distance,
    round(a.n_comps_with_6cat::numeric / {{ k }}, 2)  as coverage_6cat,

    -- Confidence signal (Improvement 1, tunable via dist_low/dist_high above).
    case
        when a.n_comps_with_6cat < 3
          or a.used_archetype_fallback
          or d.mean_comp_distance > {{ dist_high }}                  then 'baixa'
        when a.n_comps_with_6cat >= 6
         and not a.used_archetype_fallback
         and d.mean_comp_distance < {{ dist_low }}                   then 'alta'
        else 'media'
    end                                               as confidence

from aggregated a
join comp_distance d using (prospect_id)
