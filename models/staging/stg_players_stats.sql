{{ config(schema='raw', materialized='view') }}

select
  upper(trim(player))                         as player_name,
  upper(trim(tm))                             as team,
  upper(trim(opp))                            as opponent,
  upper(trim(res))                            as result,

  nullif(trim(mp), '')::double precision       as minutes_played,
  nullif(trim(fg), '')::integer                as field_goals_made,
  nullif(trim(fga), '')::integer               as field_goals_attempted,
  nullif(trim("FG%"), '')::double precision    as fg_pct,

  nullif(trim("3P"), '')::integer              as three_pt_made,
  nullif(trim("3PA"), '')::integer             as three_pt_attempted,
  nullif(trim("3P%"), '')::double precision    as three_pt_pct,

  nullif(trim(ft), '')::integer                as free_throws_made,
  nullif(trim(fta), '')::integer               as free_throws_attempted,
  nullif(trim("FT%"), '')::double precision    as ft_pct,

  nullif(trim(orb), '')::integer               as offensive_rebounds,
  nullif(trim(drb), '')::integer               as defensive_rebounds,
  nullif(trim(trb), '')::integer               as total_rebounds,

  nullif(trim(ast), '')::integer               as assists,
  nullif(trim(stl), '')::integer               as steals,
  nullif(trim(blk), '')::integer               as blocks,
  nullif(trim(tov), '')::integer               as turnovers,
  nullif(trim(pf), '')::integer                as personal_fouls,
  nullif(trim(pts), '')::integer               as points,

  nullif(trim(gmsc), '')::double precision     as game_score,
  to_date(nullif(trim(data), ''), 'YYYY-MM-DD') as game_date

from {{ ref('players_stats') }}
