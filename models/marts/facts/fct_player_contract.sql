-- fct_player_contract
-- Grain: one row per player (current contract snapshot).
-- Source: BBR contracts page — salaries por season + CBA mechanism.
--
-- Salary columns chegam como strings do BBR ("$12,345,678") e são mantidas
-- assim aqui. Parsing para numérico pode ser feito com:
--     replace(replace(salary_2025_26, '$', ''), ',', '')::bigint

with contracts as (
    select * from {{ ref('stg_bbr__contracts') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_surrogate_key(['c.player_name']) }}     as contract_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,

        -- Natural keys
        c.player_name,
        c.team_abbr,

        -- Salary por season (string formatada pelo BBR)
        c.salary_2024_25,
        c.salary_2025_26,
        c.salary_2026_27,
        c.salary_2027_28,
        c.salary_2028_29,

        -- CBA details
        c.signed_using,
        c.guaranteed

    from contracts c
    left join dim_player dp using (player_name)
    left join dim_team   dt on c.team_abbr = dt.team_abbr
)

select * from final
