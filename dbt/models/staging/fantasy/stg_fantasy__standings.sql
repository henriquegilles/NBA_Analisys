{{ config(materialized='view') }}
select
    cast(codigo_franquia as int) as franchise_id,
    nome_franquia                as franchise_name,
    cast(posicao as int)         as standing_pos,
    cast(vitorias as int)        as wins,
    cast(derrotas as int)        as losses
from {{ ref('fantasy_standings') }}
