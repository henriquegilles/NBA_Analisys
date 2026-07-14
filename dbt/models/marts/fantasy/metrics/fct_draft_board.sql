{{ config(materialized='view') }}
-- Draft board adjusted for OPPORTUNITY (talent × final NBA team situation).
-- Fixes the "draft-night vs final team" error with the nba_landing_spots seed.
with dc as (
    select prospect_key, prospect_name, pos, pos_us from {{ ref('stg_fantasy__draft_class') }}
),
proj as (
    select
        {{ norm_name('prospect_name') }} as prospect_key,
        prospect_archetype,
        proj_pg_pts, proj_pg_trb, proj_pg_ast, proj_pg_stocks, proj_pg_fg3, proj_pg_tov,
        confidence
    from {{ ref('fct_prospect_scouting') }}
    where prospect_season = '2025-26'
),
land as (
    select prospect_key, nba_team_final, opportunity_mult from {{ ref('nba_landing_spots') }}
)
select
    dc.prospect_name,
    dc.pos_us                        as archetype_pos,
    p.prospect_archetype,
    round(p.proj_pg_pts::numeric,1)  as proj_pts,
    round(p.proj_pg_ast::numeric,1)  as proj_ast,
    round(p.proj_pg_fg3::numeric,1)  as proj_3pm,
    round(p.proj_pg_stocks::numeric,1) as proj_stocks,
    l.nba_team_final,
    coalesce(l.opportunity_mult, 1.0) as opportunity_mult,
    -- talent score (weighted cats) × opportunity
    round((
        (p.proj_pg_pts + p.proj_pg_trb + p.proj_pg_ast
         + p.proj_pg_stocks*2 + p.proj_pg_fg3*1.5 - p.proj_pg_tov)
        * coalesce(l.opportunity_mult, 1.0)
    )::numeric, 1) as opp_adjusted_score,
    p.confidence                     as model_confidence  -- never hide the uncertainty
from dc
join proj p on dc.prospect_key = p.prospect_key
left join land l on dc.prospect_key = l.prospect_key
order by opp_adjusted_score desc
