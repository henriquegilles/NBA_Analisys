
  
  create view "dev"."main_raw"."stg_players__dbt_tmp" as (
    
select
  try_cast(player_id as bigint)  as player_id,
  upper(trim(first_name))        as first_name,
  upper(trim(last_name))         as last_name,
  upper(trim(position))          as position,
  try_cast(height_cm as double)  as height_cm,
  try_cast(weight_kg as double)  as weight_kg,
  try_cast(birthdate as date)    as birthdate,
  upper(trim(nationality))       as nationality
from read_csv_auto('basket_dbt/seeds/storage/raw/players.csv')
  );
