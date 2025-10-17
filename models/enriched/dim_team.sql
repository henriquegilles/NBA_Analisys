{{ config(schema='enriched', materialized='table') }}
select
  team_id,
  team_name,
  conference,
  division,
  city
from {{ ref('stg_team') }}
