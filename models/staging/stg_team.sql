{{ config(schema='raw', materialized='view') }}

select
    upper(trim(franchise))   as franchise,
    upper(trim(lg))          as league,
    upper(trim("from"))      as season_from,
    upper(trim("to"))        as season_to,
    nullif(trim(yrs),  '')::integer   as years,
    nullif(trim(g),    '')::integer   as games,
    nullif(trim(w),    '')::integer   as wins,
    nullif(trim(l),    '')::integer   as losses,
    nullif(trim("w/l%"), '')::double precision as win_loss_pct,
    nullif(trim(plyfs), '')::integer   as playoffs,
    nullif(trim(div),  '')::integer   as division_titles,
    nullif(trim(conf), '')::integer   as conference_titles,
    nullif(trim(champ), '')::integer  as championships
from {{ ref('team') }}
