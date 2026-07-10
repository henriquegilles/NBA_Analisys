{{ config(materialized='view') }}

-- Staging dos rosters da liga (FantasyGM). Uma linha por jogador × franquia.
-- Padroniza: nome normalizado (join), salários em $M, posições, flags.
with src as (
    select * from {{ ref('fantasy_rosters') }}
),
typed as (
    select
        cast(codigo_liga as int)                as league_id,
        cast(codigo_temporada as int)           as season_id,
        cast(codigo_franquia as int)            as franchise_id,
        nome_franquia                           as franchise_name,
        nome_usuario                            as owner_name,
        cast(codigo_jogador as int)             as fgm_player_id,
        cast(codigo_nba as bigint)              as nba_player_id,
        nome_jogador                            as player_name,
        {{ norm_name('nome_jogador') }}         as player_key,
        posicao_1                               as pos_1,
        nullif(trim(posicao_2::text), '')       as pos_2,
        nullif(trim(posicao_3::text), '')       as pos_3,
        -- salários vêm em dólares cheios; ::text antes do nullif p/ ser robusto ao
        -- tipo inferido pelo dbt seed (numeric OU text). Converte p/ $M.
        coalesce(nullif(trim(salario_ano1::text), '')::numeric, 0)/1e6 as salary_y1_m,
        coalesce(nullif(trim(salario_ano2::text), '')::numeric, 0)/1e6 as salary_y2_m,
        coalesce(nullif(trim(salario_ano3::text), '')::numeric, 0)/1e6 as salary_y3_m,
        lower(contundido::text) = 'true'        as is_injured,
        lower(restrito::text)   = 'true'        as is_restricted,
        lower(fora_nba::text)   = 'true'        as is_out_of_nba
    from src
    where trim(coalesce(nome_jogador,'')) <> ''
),
-- dedup defensivo: 1 linha por (franquia, jogador) — pega a de maior salário
ranked as (
    select *,
        row_number() over (
            partition by franchise_id, player_key
            order by salary_y1_m desc
        ) as rn
    from typed
)
select * from ranked where rn = 1
