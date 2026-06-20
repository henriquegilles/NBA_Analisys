-- int_prospect__nba_bridge
-- Grão: 1 linha por prospecto college que casou com um pick do draft.
--
-- Ponte college→NBA (D-09): casa o prospecto (temporada college mais recente)
-- com sua carreira NBA no seed `draft`, que já traz médias DE CARREIRA por-jogo
-- (pg_pts/trb/ast) + valor (WS/BPM/VORP) — exatamente o "média de carreira" do
-- desfecho D-11, para essas categorias.
--
-- Casamento por NOME normalizado + JANELA de ano do draft (±1 do fim da última
-- temporada college), que desambigua xarás de eras diferentes (ex.: Corliss
-- Williamson 1995 vs. Zion Williamson 2019). `n_matches` sinaliza ambiguidade
-- remanescente (deveria ser 1; >1 é candidato a override manual — D-09).
--
-- Limitação assumida: o `draft` não traz stocks/3PM/TOV de carreira, então o
-- desfecho cobre 3 das 6 categorias + métricas de valor. Carreira NBA completa
-- (6 cat) fica como melhoria futura (scraper de páginas de jogador da NBA).

with prospect_latest as (
    select cbb_id, player_name, school, season,
           left(season, 4)::int + 1 as season_end_year
    from (
        select *, row_number() over (partition by cbb_id order by season desc) as rn
        from {{ ref('int_prospect__college_stats') }}
    ) s
    where rn = 1
),

draft as (
    select
        trim("player_name"::text)                          as player_name,
        nullif(trim("college"::text), '')                  as nba_college,
        nullif(trim("draft_year"::text), '')::int          as draft_year,
        nullif(trim("pick"::text), '')::int                as pick,
        nullif(trim("pg_pts"::text), '')::numeric(5,1)     as nba_pg_pts,
        nullif(trim("pg_trb"::text), '')::numeric(5,1)     as nba_pg_trb,
        nullif(trim("pg_ast"::text), '')::numeric(5,1)     as nba_pg_ast,
        nullif(trim("career_games"::text), '')::int        as nba_career_games,
        nullif(trim("win_shares"::text), '')::numeric(6,1) as nba_win_shares,
        nullif(trim("bpm"::text), '')::numeric(6,1)        as nba_bpm,
        nullif(trim("vorp"::text), '')::numeric(6,1)       as nba_vorp
    from {{ ref('draft') }}
    where trim("player_name"::text) <> ''
      and nullif(trim("draft_year"::text), '') is not null
),

matched as (
    select
        p.cbb_id,
        p.player_name,
        p.school                                           as college_school,
        p.season                                           as last_college_season,
        d.nba_college,
        d.draft_year,
        d.pick,
        (d.nba_pg_pts is not null)                         as reached_nba,
        d.nba_pg_pts, d.nba_pg_trb, d.nba_pg_ast,
        d.nba_career_games, d.nba_win_shares, d.nba_bpm, d.nba_vorp,
        count(*) over (partition by p.cbb_id)              as n_matches
    from prospect_latest p
    join draft d
      on lower(trim(p.player_name)) = lower(trim(d.player_name))
     and d.draft_year between p.season_end_year - 1 and p.season_end_year + 1
)

select * from matched
