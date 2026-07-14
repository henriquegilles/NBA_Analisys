{{ config(materialized='view') }}
select
    cast(codigo_liga as int)        as league_id,
    cast(codigo_jogador as int)     as fgm_player_id,
    nullif(trim(codigo_nba::text), '')::bigint as nba_player_id,
    nome                            as prospect_name,
    {{ norm_name('nome') }}         as prospect_key,
    posicao                        as pos,
    posicao_americana              as pos_us,
    franquia_atual_nba             as nba_team_draftnight,
    sigla_franquia_nba             as nba_abbr,
    nullif(trim(codigo_temporada_calouro::text), '')::int as rookie_season_id
from {{ ref('fantasy_draft_class') }}
