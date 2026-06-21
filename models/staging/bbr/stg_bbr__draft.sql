-- stg_bbr__draft
-- NBA Draft picks from 1986–2025 scraped from BBR.
-- One row per draft pick. Career stats are cumulative through the
-- most recent season at time of scraping.

with source as (
    select * from {{ ref('draft') }}
),

-- BBR repete linhas de cabeçalho dentro da tabela ("Pk", "G"…). Filtramos para
-- só picks numéricos ANTES de qualquer cast (senão o cast quebra na linha-lixo).
valid as (
    select * from source
    where trim("pick"::text) ~ '^[0-9]+$'
),

cleaned as (
    select
        nullif(trim("draft_year"::text), '')::integer           as draft_year,
        -- O draft.csv não traz mais `round`; derivamos do pick (30 picks/round,
        -- exato na era moderna de 2 rodadas).
        ceil(nullif(trim("pick"::text), '')::numeric / 30.0)::integer as round,
        nullif(trim("pick"::text),       '')::integer           as pick,
        upper(trim("team"))                                      as team_abbr,
        trim("player_name")                                      as player_name,
        -- slug NBA capturado dos hrefs da página do draft (draft.py). Chave
        -- canônica p/ juntar a carreira NBA completa em int_prospect__nba_bridge.
        nullif(trim("bbr_id"::text),     '')                     as nba_bbr_id,
        nullif(trim("college"),          '')                     as college,

        -- Career volume
        nullif(trim("career_years"::text), '')::integer         as career_seasons,
        nullif(trim("career_games"::text), '')::integer         as career_games,
        nullif(trim("career_mp"::text),    '')::integer         as career_minutes,
        nullif(trim("career_pts"::text),   '')::integer         as career_points,
        nullif(trim("career_trb"::text),   '')::integer         as career_reb,
        nullif(trim("career_ast"::text),   '')::integer         as career_ast,

        -- Career shooting percentages
        nullif(trim("career_fg_pct"::text),  '')::numeric(5,3)  as career_fg_pct,
        nullif(trim("career_3p_pct"::text),  '')::numeric(5,3)  as career_3p_pct,
        nullif(trim("career_ft_pct"::text),  '')::numeric(5,3)  as career_ft_pct,

        -- Per-game career averages
        nullif(trim("pg_mp"::text),  '')::numeric(5,1)          as pg_mp,
        nullif(trim("pg_pts"::text), '')::numeric(5,1)          as pg_pts,
        nullif(trim("pg_trb"::text), '')::numeric(5,1)          as pg_trb,
        nullif(trim("pg_ast"::text), '')::numeric(5,1)          as pg_ast,

        -- Advanced career metrics
        nullif(trim("win_shares"::text), '')::numeric(6,1)      as win_shares,
        nullif(trim("ws_per_48"::text),  '')::numeric(6,3)      as ws_per_48,
        nullif(trim("bpm"::text),        '')::numeric(6,1)      as bpm,
        nullif(trim("vorp"::text),       '')::numeric(6,1)      as vorp

    from valid
    where trim("player_name") != ''
      and "player_name" is not null
)

select * from cleaned
