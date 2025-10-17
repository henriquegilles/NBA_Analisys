{{ config(schema='enriched', materialized='incremental', unique_key='player_id_season', incremental_strategy='merge') }}

with stats as (select * from {{ ref('stg_players_stats') }}),
dimt  as (select * from {{ ref('stg_team') }})

select
  s.player_id,
  s.season,
  concat(cast(s.player_id as varchar), '-', cast(s.season as varchar)) as player_id_season,
  s.games, s.minutes, s.points, s.rebounds, s.assists, s.steals, s.blocks, s.turnovers,
  s.fg_pct, s.tp_pct, s.ft_pct,
  dt.team_id,
  s.team_name
from stats s
left join dimt dt on upper(dt.team_name) = upper(s.team_name)

{% if is_incremental() %}
where s.season > (select coalesce(max(season), 0) from {{ this }})
{% endif %}
