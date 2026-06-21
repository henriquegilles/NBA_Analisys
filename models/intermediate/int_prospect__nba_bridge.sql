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
-- Williamson 1995 vs. Zion Williamson 2019). Quando a janela NÃO basta (xarás de
-- anos vizinhos, ex.: Justin Jackson UNC 2017 vs. Maryland 2018), o seed manual
-- `college_nba_id_overrides` (D-09) fixa o slug NBA canônico. `n_matches` é
-- recomputado APÓS o override — depois dele deveria ser sempre 1.
--
-- 6 categorias completas (D-30): pts/trb/ast vêm do `draft`; stl/blk (→stocks),
-- 3PM e TOV vêm de stg_bbr__nba_careers (linha "Career" da página do jogador),
-- juntos pelo slug NBA `nba_bbr_id`. O join é LEFT: prospecto cuja carreira ainda
-- não foi raspada fica com as 4 cats novas em NULL (não perde a linha).

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
        nullif(trim("bbr_id"::text), '')                   as nba_bbr_id,
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

-- Carreira NBA 6-cat completa (stl/blk/3PM/TOV que o `draft` não traz).
-- Junta pelo slug NBA — chave canônica, sem ambiguidade de xará (D-30).
careers as (
    select bbr_id, pg_stl, pg_blk, pg_fg3, pg_tov
    from {{ ref('stg_bbr__nba_careers') }}
),

matched as (
    select
        p.cbb_id,
        p.player_name,
        p.school                                           as college_school,
        p.season                                           as last_college_season,
        d.nba_bbr_id,
        d.nba_college,
        d.draft_year,
        d.pick,
        (d.nba_pg_pts is not null)                         as reached_nba,
        d.nba_pg_pts, d.nba_pg_trb, d.nba_pg_ast,
        -- 6-cat completa: stl/blk/3PM/TOV da carreira NBA (left join — NULL se a
        -- carreira ainda não foi raspada). stocks = stl + blk.
        c.nba_pg_stl, c.nba_pg_blk, c.nba_pg_stocks, c.nba_pg_fg3, c.nba_pg_tov,
        d.nba_career_games, d.nba_win_shares, d.nba_bpm, d.nba_vorp
    from prospect_latest p
    join draft d
      on lower(trim(p.player_name)) = lower(trim(d.player_name))
     and d.draft_year between p.season_end_year - 1 and p.season_end_year + 1
    left join (
        select
            bbr_id,
            pg_stl                 as nba_pg_stl,
            pg_blk                 as nba_pg_blk,
            (pg_stl + pg_blk)      as nba_pg_stocks,
            pg_fg3                 as nba_pg_fg3,
            pg_tov                 as nba_pg_tov
        from careers
    ) c on c.bbr_id = d.nba_bbr_id
),

-- D-09: correções manuais de identidade para xarás que a janela de ano não
-- desambigua. Mapeia o cbb_id do prospecto para o slug NBA canônico; com isso
-- descartamos os matches errados do mesmo prospecto.
overrides as (
    select
        nullif(trim("cbb_id"::text), '')     as cbb_id,
        nullif(trim("nba_bbr_id"::text), '') as nba_bbr_id
    from {{ ref('college_nba_id_overrides') }}
),

resolved as (
    select m.*
    from matched m
    left join overrides o on o.cbb_id = m.cbb_id
    where o.cbb_id is null               -- sem override: mantém todos os matches
       or m.nba_bbr_id = o.nba_bbr_id     -- com override: só o slug NBA canônico
)

-- n_matches recomputado DEPOIS do override (deveria ser 1 para todos agora).
select
    *,
    count(*) over (partition by cbb_id) as n_matches
from resolved
