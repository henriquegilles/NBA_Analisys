-- dim_player_contract
-- Grain: 1 row per player (current contract snapshot).
-- Was fct_player_contract — renamed to reflect that it has no event measures:
-- it is a current state, not a transaction. History via player_contract_snapshot.
--
-- For salary-evolution analysis, use:
--   analytics_snapshots.player_contract_snapshot
--
-- To convert a salary from string to numeric:
--   replace(replace(salary_2025_26, '$', ''), ',', '')::bigint

with contracts as (
    -- The contracts seed carries repeated players (duplicate rows on BBR);
    -- the grain here is 1 per player, so we deduplicate deterministically.
    select * from (
        select *,
               row_number() over (partition by player_name order by team_abbr) as _rn
        from {{ ref('stg_bbr__contracts') }}
    ) d
    where _rn = 1
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_id(['c.player_name']) }}                 as contract_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,

        -- Natural keys
        c.player_name,
        c.team_abbr,

        -- Salaries per season (string formatted by BBR — "$12,345,678")
        c.salary_2025_26,
        c.salary_2026_27,
        c.salary_2027_28,
        c.salary_2028_29,
        c.salary_2029_30,
        c.salary_2030_31,

        -- Contract details
        c.guaranteed

    from contracts c
    left join dim_player dp using (player_name)
    left join dim_team   dt on c.team_abbr = dt.team_abbr
)

select * from final
