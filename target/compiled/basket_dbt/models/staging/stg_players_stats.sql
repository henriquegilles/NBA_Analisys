
select
  try_cast(player_id as bigint)  as player_id,
  try_cast(season as integer)    as season,
  try_cast(games as integer)     as games,
  try_cast(minutes as double)    as minutes,
  try_cast(points as double)     as points,
  try_cast(rebounds as double)   as rebounds,
  try_cast(assists as double)    as assists,
  try_cast(steals as double)     as steals,
  try_cast(blocks as double)     as blocks,
  try_cast(turnovers as double)  as turnovers,
  try_cast(fg_pct as double)     as fg_pct,
  try_cast(tp_pct as double)     as tp_pct,
  try_cast(ft_pct as double)     as ft_pct,
  upper(trim(team_name))         as team_name
from read_csv_auto('basket_dbt/seeds/storage/raw/players_stats.csv')