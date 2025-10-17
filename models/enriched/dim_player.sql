{{ config(schema='enriched', materialized='table') }}

select
  player_id,
  first_name,
  last_name,
  position,
  height_cm,
  weight_kg,
  birthdate,
  nationality
from {{ ref('stg_players') }}
