-- dim_player_contract
-- Grain: 1 linha por jogador (snapshot atual do contrato).
-- Era fct_player_contract — renomeado para refletir que não tem medidas de evento:
-- é um estado atual, não uma transação. Histórico via player_contract_snapshot.
--
-- Para análises de evolução salarial, use:
--   analytics_snapshots.player_contract_snapshot
--
-- Para converter salário de string para numérico:
--   replace(replace(salary_2025_26, '$', ''), ',', '')::bigint

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
        {{ generate_id(['c.player_name']) }}                 as contract_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,

        -- Natural keys
        c.player_name,
        c.team_abbr,

        -- Salários por temporada (string formatada pelo BBR — "$12,345,678")
        c.salary_2024_25,
        c.salary_2025_26,
        c.salary_2026_27,
        c.salary_2027_28,
        c.salary_2028_29,

        -- Detalhes do contrato
        c.signed_using,
        c.guaranteed

    from contracts c
    left join dim_player dp using (player_name)
    left join dim_team   dt on c.team_abbr = dt.team_abbr
)

select * from final
