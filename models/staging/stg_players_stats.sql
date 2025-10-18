{{ config(schema='stg', materialized='view') }}

with src as (
  select * from {{ ref('players_stats') }}
)

select
  upper(trim("Player"))                         as player_name,
  upper(trim("Tm"))                             as team,
  upper(trim("Opp"))                            as opponent,
  upper(trim("Res"))                            as result,

  case
    when "MP" ~ '^\d+:\d{1,2}$'
      then split_part("MP", ':', 1)::int + split_part("MP", ':', 2)::int / 60.0
    when "MP" ~ '^\d+(\.\d+)?$'
      then "MP"::double precision
    else null
  end                                           as minutes_played,

  nullif(trim("FG"),  '')::int                  as field_goals_made,
  nullif(trim("FGA"), '')::int                  as field_goals_attempted,
  nullif(trim("FG%"), '')::double precision     as fg_pct,

  nullif(trim("3P"),  '')::int                  as three_pt_made,
  nullif(trim("3PA"), '')::int                  as three_pt_attempted,
  nullif(trim("3P%"), '')::double precision     as three_pt_pct,

  nullif(trim("FT"),  '')::int                  as free_throws_made,
  nullif(trim("FTA"), '')::int                  as free_throws_attempted,
  nullif(trim("FT%"), '')::double precision     as ft_pct,

  nullif(trim("ORB"), '')::int                  as offensive_rebounds,
  nullif(trim("DRB"), '')::int                  as defensive_rebounds,
  nullif(trim("TRB"), '')::int                  as total_rebounds,

  nullif(trim("AST"), '')::int                  as assists,
  nullif(trim("STL"), '')::int                  as steals,
  nullif(trim("BLK"), '')::int                  as blocks,
  nullif(trim("TOV"), '')::int                  as turnovers,
  nullif(trim("PF"),  '')::int                  as personal_fouls,
  nullif(trim("PTS"), '')::int                  as points,

  nullif(trim("GmSc"), '')::double precision    as game_score,
  to_date(nullif(trim("Data"), ''), 'YYYY-MM-DD') as game_date
from src
