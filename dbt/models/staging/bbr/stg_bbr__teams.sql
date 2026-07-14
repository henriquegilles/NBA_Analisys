-- stg_bbr__teams
-- Season-level team stats from Basketball Reference teams page.
-- The source table has one row per franchise era; we keep all rows
-- and let downstream models filter to the current season.

with source as (
    select * from {{ ref('team') }}
),

cleaned as (
    select
        trim("Franchise")                             as franchise_name,
        trim("Lg")                                    as league,
        trim("From")                                  as season_from,
        trim("To")                                    as season_to,
        nullif(trim("Yrs"::text),   '')::integer      as years_active,
        nullif(trim("G"::text),     '')::integer      as games_played,
        nullif(trim("W"::text),     '')::integer      as wins,
        nullif(trim("L"::text),     '')::integer      as losses,
        nullif(trim("wl_pct"::text),'')::numeric(5,3) as win_loss_pct,
        nullif(trim("Plyfs"::text), '')::integer      as playoff_appearances,
        nullif(trim("Div"::text),   '')::integer      as division_titles,
        nullif(trim("Conf"::text),  '')::integer      as conference_titles,
        nullif(trim("Champ"::text), '')::integer      as championships

    from source
    -- BBR uses 'Franchise' as column header; skip repeated header rows
    where trim("Franchise") not in ('Franchise', '')
)

select * from cleaned
