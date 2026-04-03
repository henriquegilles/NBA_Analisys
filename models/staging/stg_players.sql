-- Fonte: players.csv (Basketball Reference, temporada 2024-25)
-- Colunas: Player, Age, Team, Pos
select
  trim("Player")                           as player_name,
  upper(trim("Team"))                      as team,
  upper(trim("Pos"))                       as position,
  nullif(trim("Age"::text), '')::integer   as age
from {{ ref('players') }}
where trim("Player") != 'Player'
