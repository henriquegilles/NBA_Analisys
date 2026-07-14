{{ config(materialized='view') }}
-- Cap per franchise ($190M ceiling). Salaries already in $M in staging.
with by_team as (
    select
        franchise_id, franchise_name,
        round(sum(salary_y1_m)::numeric,1)                  as payroll_y1_m,
        count(*) filter (where salary_y1_m > 0)             as paid_players,
        count(*) filter (where salary_y1_m = 0)             as fa_bound_players
    from {{ ref('stg_fantasy__rosters') }}
    group by 1,2
)
select *,
    190.0 - payroll_y1_m as cap_space_m
from by_team
order by cap_space_m desc
