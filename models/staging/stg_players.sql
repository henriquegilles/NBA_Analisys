{{ config(enabled=false) }}
--{{ config(schema='raw', materialized='view') }}

select
  (player_id)::bigint                                                 as player_id,        -- já é numérico; sem trim

  -- "#": no CSV vem 8.0, 12.0; se quiser inteiro, converta depois de ler como numérico
  nullif(trim("#"::text), '')::numeric(10,1)                          as jersey_number_num,
  (nullif(trim("#"::text), '')::numeric(10,1))::int                   as jersey_number,    -- opcional: inteiro

  upper(trim(player::text))                                           as player_name,
  upper(trim(pos::text))                                              as position,
  upper(trim("HT"::text))                                             as height,           -- ex.: '6-8'
  nullif(trim("WT"::text), '')::integer                               as weight_lbs,
  nullif(trim("Age"::text), '')::integer                              as age,              -- <<<< "Age"
  upper(trim("Current Team"::text))                                   as current_team,
  nullif(trim("YOS"::text), '')::integer                              as years_of_service,
  upper(trim("Pre-Draft Team"::text))                                 as pre_draft_team,   -- <<<< hífen e caps
  upper(trim("Draft Status"::text))                                   as draft_status,
  upper(trim("Nationality"::text))                                    as nationality
from {{ ref('players') }}
