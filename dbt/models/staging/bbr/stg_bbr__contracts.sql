-- stg_bbr__contracts
-- NBA player contracts scraped from Basketball Reference.
-- Requires the scraper to have run first:
--   cd src/scraping && python contracts.py
--
-- Current structure of the BBR contracts page (seed contracts.csv):
--   Rk, Player, Tm, 2025-26, 2026-27, 2027-28, 2028-29, 2029-30, 2030-31, Guaranteed
-- (The seasons roll forward every year; the scraper no longer captures "Signed Using".)

with source as (
    select * from {{ ref('contracts') }}
),

cleaned as (
    select
        trim("Player")                              as player_name,
        upper(trim("Tm"))                           as team_abbr,
        nullif(trim("2025-26"::text), '')           as salary_2025_26,
        nullif(trim("2026-27"::text), '')           as salary_2026_27,
        nullif(trim("2027-28"::text), '')           as salary_2027_28,
        nullif(trim("2028-29"::text), '')           as salary_2028_29,
        nullif(trim("2029-30"::text), '')           as salary_2029_30,
        nullif(trim("2030-31"::text), '')           as salary_2030_31,
        nullif(trim("Guaranteed"::text), '')        as guaranteed

    from source
    where trim("Player") not in ('Player', '')
)

select * from cleaned
