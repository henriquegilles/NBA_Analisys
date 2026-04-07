-- stg_bbr__contracts
-- Contratos dos jogadores da NBA scraped do Basketball Reference.
-- Requer que o scraper tenha rodado primeiro:
--   cd src/scraping && python contracts.py
--
-- Estrutura do BBR contracts page:
--   Player, Tm, 2024-25, 2025-26, 2026-27, 2027-28, 2028-29, Signed Using, Guaranteed
-- Após achatar o cabeçalho multi-nível, as colunas ficam com sufixo duplicado.
-- O scraper já normaliza para nomes legíveis.

with source as (
    select * from {{ ref('contracts') }}
),

cleaned as (
    select
        trim("Player")                              as player_name,
        upper(trim("Tm"))                           as team_abbr,
        nullif(trim("2024-25"::text), '')           as salary_2024_25,
        nullif(trim("2025-26"::text), '')           as salary_2025_26,
        nullif(trim("2026-27"::text), '')           as salary_2026_27,
        nullif(trim("2027-28"::text), '')           as salary_2027_28,
        nullif(trim("2028-29"::text), '')           as salary_2028_29,
        nullif(trim("Signed Using"::text), '')      as signed_using,
        nullif(trim("Guaranteed"::text), '')        as guaranteed

    from source
    where trim("Player") not in ('Player', '')
)

select * from cleaned
