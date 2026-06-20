-- stg_cbb__player_season
-- Cleaned college player-season lines scraped from College Basketball Reference.
-- Grão: 1 linha por jogador × temporada de college (chave cbb_id × season).
--
-- Fonte: seed college_player_seasons.csv (scraper src/scraping/college.py,
-- coletado por escola × temporada — decisão D-27). Per-40-min já vem pronto do
-- site (D-10), então aqui só limpamos e tipamos; não há cálculo de normalização.
--
-- `class` é mantido como string limpa (FR/SO/JR/SR); o mapeamento ordinal
-- (proxy de idade, D-26) e a montagem de features acontecem no intermediate.
-- `conf_abbr` costuma vir nulo no scrape por escola (conferência implícita pela
-- escola) — coluna mantida para quando a fonte for página de jogador.

with source as (
    select * from {{ ref('college_player_seasons') }}
),

cleaned as (
    select
        -- Identidade
        trim("cbb_id"::text)                                  as cbb_id,
        trim("player"::text)                                  as player_name,
        trim("school"::text)                                  as school,
        trim("season"::text)                                  as season,
        nullif(trim("conf_abbr"::text), '')                   as conf_abbr,

        -- Contexto do prospecto
        upper(nullif(trim("class"::text), ''))                as class,        -- FR/SO/JR/SR (proxy de idade, D-26)
        upper(nullif(trim("pos"::text), ''))                  as position,
        nullif(trim("height"::text), '')                      as height,       -- "6-7" (texto)
        nullif(trim("weight"::text), '')::integer             as weight_lb,
        nullif(substring(trim("rsci"::text) from '^\d+'), '')::integer
                                                              as rsci_rank,    -- rank de recruta (top-100); null = não rankeado

        -- Volume
        nullif(trim("games"::text), '')::integer              as games,
        nullif(trim("games_started"::text), '')::integer      as games_started,
        nullif(trim("mp"::text), '')::integer                 as minutes_played,

        -- 6 categorias da liga, por-40-min (sem +/- em college — D-10)
        nullif(trim("pts_per_min"::text), '')::numeric(6,1)   as pts_per_40,
        nullif(trim("trb_per_min"::text), '')::numeric(6,1)   as trb_per_40,
        nullif(trim("ast_per_min"::text), '')::numeric(6,1)   as ast_per_40,
        nullif(trim("stl_per_min"::text), '')::numeric(6,1)   as stl_per_40,   -- componente de STOCKS
        nullif(trim("blk_per_min"::text), '')::numeric(6,1)   as blk_per_40,   -- componente de STOCKS
        nullif(trim("fg3_per_min"::text), '')::numeric(6,1)   as three_p_per_40,
        nullif(trim("tov_per_min"::text), '')::numeric(6,1)   as tov_per_40,   -- invertida — tratada no z-score downstream

        -- Eficiência (contexto)
        nullif(trim("ts_pct"::text), '')::numeric(5,3)        as ts_pct,
        nullif(trim("efg_pct"::text), '')::numeric(5,3)       as efg_pct,
        nullif(trim("fg3_pct"::text), '')::numeric(5,3)       as fg3_pct,
        nullif(trim("ft_pct"::text), '')::numeric(5,3)        as ft_pct,
        nullif(trim("usg_pct"::text), '')::numeric(5,1)       as usg_pct,

        -- Avançadas (bônus de contexto)
        nullif(trim("per"::text), '')::numeric(6,1)           as per,
        nullif(trim("ws"::text), '')::numeric(6,1)            as win_shares,
        nullif(trim("obpm"::text), '')::numeric(6,1)          as obpm,
        nullif(trim("dbpm"::text), '')::numeric(6,1)          as dbpm,
        nullif(trim("bpm"::text), '')::numeric(6,1)           as bpm,

        -- Contexto de time (D-27 — força de calendário, nível de time)
        nullif(trim("team_sos"::text), '')::numeric(6,2)      as team_sos,
        nullif(trim("team_srs"::text), '')::numeric(6,2)      as team_srs

    from source
    where trim("player"::text) != 'Player'
)

select * from cleaned
