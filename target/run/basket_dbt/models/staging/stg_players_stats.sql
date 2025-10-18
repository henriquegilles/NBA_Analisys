
  create view "nba"."analytics_raw"."stg_players_stats__dbt_tmp"
    
    
  as (
    with src as (
  select * from "nba"."analytics_raw"."players_stats"
)

select
  upper(trim("Player")) as player_name,
  upper(trim("Tm"))     as team,
  upper(trim("Opp"))    as opponent,
  upper(trim("Res"))    as result,

  case
    when "MP"::text ~ '^\d+:\d{1,2}$' then
      split_part("MP"::text, ':', 1)::int
      + split_part("MP"::text, ':', 2)::int / 60.0
    else
      nullif("MP"::text, '')::double precision
  end as minutes_played,

  "FG"::int                 as field_goals_made,
  "FGA"::int                as field_goals_attempted,
  "FGPer"::double precision as fg_pct,

  "ThreP"::int              as three_pt_made,
  "ThrePA"::int             as three_pt_attempted,
  "ThrePPer"::double precision as three_pt_pct,

  "FT"::int                 as free_throws_made,
  "FTA"::int                as free_throws_attempted,
  "FTPer"::double precision as ft_pct,

  "ORB"::int  as offensive_rebounds,
  "DRB"::int  as defensive_rebounds,
  "TRB"::int  as total_rebounds,
  "AST"::int  as assists,
  "STL"::int  as steals,
  "BLK"::int  as blocks,
  "TOV"::int  as turnovers,
  "PF"::int   as personal_fouls,
  "PTS"::int  as points,

  "GmSc"::double precision as game_score,
  "Data"::date             as game_date
from src
  );