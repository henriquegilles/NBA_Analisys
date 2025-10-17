
  
  create view "dev"."main_raw"."stg_team__dbt_tmp" as (
    
select
  try_cast(team_id as bigint)      as team_id,
  upper(trim(team_name))           as team_name,
  upper(trim(conference))          as conference,
  upper(trim(division))            as division,
  upper(trim(city))                as city
from read_csv_auto('basket_dbt/seeds/storage/raw/team.csv')
  );
