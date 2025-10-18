with src as (select * from {{ ref('team') }})
select
  upper(trim("Franchise"::text))                    as franchise,
  upper(trim("Lg"::text))                           as league,
  nullif(trim("From"::text), '')::int               as season_from,
  nullif(trim("To"::text), '')::int                 as season_to,
  nullif(trim("Yrs"::text), '')::int                as years,
  nullif(trim("G"::text),   '')::int                as games,
  nullif(trim("W"::text),   '')::int                as wins,
  nullif(trim("L"::text),   '')::int                as losses,
  nullif(trim("W/L%"::text), '')::double precision  as win_loss_pct,
  nullif(trim("Plyfs"::text), '')::int              as playoffs,
  nullif(trim("Div"::text),   '')::int              as division_titles,
  nullif(trim("Conf"::text),  '')::int              as conference_titles,
  nullif(trim("Champ"::text), '')::int              as championships
from src
