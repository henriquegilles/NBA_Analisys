{{ config(schema='raw', materialized='view') }}
select
  upper(trim(team_name))           as team_name,
  upper(trim(conference))          as conference,
  upper(trim(division))            as division,
  upper(trim(city))                as city
from {{ source('raw','team_csv') }}
