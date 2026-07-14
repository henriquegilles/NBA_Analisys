{{ config(materialized='view') }}
select
    cast(codigo_liga as int)      as league_id,
    cast(codigo_temporada as int) as season_id,
    cast(codigo_franquia as int)  as franchise_id,
    nome_franquia                 as franchise_name,
    nome_usuario                  as owner_name,
    cast(qtd_jogadores as int)    as roster_count
from {{ ref('fantasy_franchises') }}
