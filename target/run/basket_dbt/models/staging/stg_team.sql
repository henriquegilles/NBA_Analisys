
  create view "nba"."analytics_raw"."stg_team__dbt_tmp"
    
    
  as (
    select * 
from "nba"."analytics_raw"."team"
  );