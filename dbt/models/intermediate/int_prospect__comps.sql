-- int_prospect__comps
-- Grain: prospect × comp (k rows per prospect).
--
-- The scouting comparables MECHANIC (Domain B), prototyped WITHOUT the NBA side:
-- for each prospect, finds the k most similar college players. Once the
-- college→NBA backbone exists, `fct_prospect_scouting` joins these comps to
-- NBA outcomes to produce the projection.
--
-- Decisions applied:
--   D-12  prospect = each player's MOST RECENT season.
--   D-21  EUCLIDEAN distance over STANDARDIZED features (z-score), k ≈ 8–10.
--         Features (9): 6 categories per-40 + class_rank + TS% + SOS.
--   D-23/D-28  comps within the same archetype (G/F/C), with FALLBACK to all
--         archetypes when the same-archetype pool has fewer than k candidates.
--
-- Feature nulls are neutralized (coalesce to the mean → 0 contribution to the
-- distance), so they neither break nor dominate the calculation.

-- Materialized as a TABLE (exception to the intermediate view default): the k-NN
-- cross-joins 3.7k player-seasons and as a view it recomputed EVERYTHING on every
-- dashboard query (the Comps tab took ~8 min per query — Round 6 Phase 2).
{{ config(materialized='table') }}

{% set k = 8 %}

{% set features = [
    'pts_per_40', 'trb_per_40', 'ast_per_40', 'stocks_per_40',
    'three_p_per_40', 'tov_per_40', 'class_rank', 'ts_pct', 'team_sos'
] %}

with prospects as (
    -- Most recent season of each player (D-12).
    select *
    from (
        select *,
               row_number() over (partition by cbb_id order by season desc) as rn_recent
        from {{ ref('int_prospect__college_stats') }}
    ) s
    where rn_recent = 1
),

-- Mean and standard deviation of each feature over the prospect pool.
stats as (
    select
        {% for f in features %}
        avg({{ f }})              as {{ f }}_mean,
        stddev_samp({{ f }})      as {{ f }}_std{{ "," if not loop.last }}
        {% endfor %}
    from prospects
),

-- Standardized features (z-score). Null → mean → z = 0 (neutral).
z as (
    select
        p.cbb_id,
        p.player_name,
        p.season,
        p.archetype,
        {% for f in features %}
        (coalesce(p.{{ f }}, s.{{ f }}_mean) - s.{{ f }}_mean) / nullif(s.{{ f }}_std, 0) as z_{{ f }}{{ "," if not loop.last }}
        {% endfor %}
    from prospects p
    cross join stats s
),

-- All prospect × candidate pairs (excludes the player itself).
pairs as (
    select
        a.cbb_id      as prospect_id,
        a.player_name as prospect_name,
        a.season      as prospect_season,
        a.archetype   as prospect_archetype,
        b.cbb_id      as comp_id,
        b.player_name as comp_name,
        b.season      as comp_season,
        b.archetype   as comp_archetype,
        (a.archetype = b.archetype) as same_archetype,
        sqrt(
            {% for f in features %}
            power(a.z_{{ f }} - b.z_{{ f }}, 2){{ " +" if not loop.last }}
            {% endfor %}
        ) as distance
    from z a
    join z b on a.cbb_id <> b.cbb_id
),

-- How many same-archetype candidates does each prospect have?
arch_counts as (
    select prospect_id, count(*) filter (where same_archetype) as n_same_archetype
    from pairs
    group by prospect_id
),

-- If there are >= k of the same archetype, restrict to it; otherwise open up to all (fallback).
scoped as (
    select
        p.*,
        ac.n_same_archetype,
        (ac.n_same_archetype < {{ k }}) as used_archetype_fallback
    from pairs p
    join arch_counts ac using (prospect_id)
    where p.same_archetype
       or ac.n_same_archetype < {{ k }}
),

ranked as (
    select
        *,
        row_number() over (partition by prospect_id order by distance) as comp_rank
    from scoped
)

select
    prospect_id,
    prospect_name,
    prospect_season,
    prospect_archetype,
    comp_rank,
    comp_id,
    comp_name,
    comp_season,
    comp_archetype,
    round(distance::numeric, 3) as distance,
    used_archetype_fallback
from ranked
where comp_rank <= {{ k }}
