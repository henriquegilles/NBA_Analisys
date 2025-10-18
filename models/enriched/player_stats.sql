with src as (
  select * from {{ ref('players_stats') }}
)
select
  upper(trim("Player"::text))                       as player_name,
  upper(trim("Tm"::text))                           as team,
  upper(trim("Opp"::text))                          as opponent,
  upper(trim("Res"::text))                          as result,

  case
    when "MP" ~ '^\d+:\d{1,2}$'
      then split_part("MP", ':', 1)::int + split_part("MP", ':', 2)::int / 60.0
    when "MP" ~ '^\d+(\.\d+)?$' then "MP"::double precision
    else null
  end                                               as minutes_played,

  nullif(trim("FG"::text), '')::int                 as fg_made,
  nullif(trim("FGA"::text), '')::int                as fg_att,
  nullif(trim("FG%"::text), '')::double precision   as fg_pct,

  nullif(trim("3P"::text), '')::int                 as tp_made,
  nullif(trim("3PA"::text), '')::int                as tp_att,
  nullif(trim("3P%"::text), '')::double precision   as tp_pct,

  nullif(trim("FT"::text), '')::int                 as ft_made,
  nullif(trim("FTA"::text), '')::int                as ft_att,
  nullif(trim("FT%"::text), '')::double precision   as ft_pct,

  nullif(trim("ORB"::text), '')::int                as orb,
  nullif(trim("DRB"::text), '')::int                as drb,
  nullif(trim("TRB"::text), '')::int                as trb,
  nullif(trim("AST"::text), '')::int                as ast,
  nullif(trim("STL"::text), '')::int                as stl,
  nullif(trim("BLK"::text), '')::int                as blk,
  nullif(trim("TOV"::text), '')::int                as tov,
  nullif(trim("PF"::text),  '')::int                as pf,
  nullif(trim("PTS"::text), '')::int                as pts,

  nullif(trim("GmSc"::text), '')::double precision  as game_score,
  to_date(nullif(trim("Data"::text), ''), 'YYYY-MM-DD') as game_date
from src
