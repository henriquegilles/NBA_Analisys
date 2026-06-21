-- stg_bbr__nba_careers
-- Carreira NBA por-jogo, raspada da linha "Career" da tabela per_game de cada
-- página de jogador (src/scraping/nba_careers.py). Grão: 1 linha por jogador NBA.
--
-- Razão de existir: o seed `draft` só traz pts/trb/ast de carreira; aqui vêm as
-- categorias que faltavam p/ fechar as 6 da Bandeja de 3 — stl, blk (→stocks),
-- 3PM (fg3) e TOV. Junta-se em int_prospect__nba_bridge pela chave `bbr_id`
-- (slug NBA), que o draft passou a expor como `nba_bbr_id`.

with source as (
    select * from {{ ref('nba_player_careers') }}
),

cleaned as (
    select
        nullif(trim("bbr_id"::text), '')               as bbr_id,
        nullif(trim("player_name"::text), '')          as player_name,

        nullif(trim("career_games"::text), '')::integer as career_games,
        nullif(trim("pg_pts"::text), '')::numeric(5,1)  as pg_pts,
        nullif(trim("pg_trb"::text), '')::numeric(5,1)  as pg_trb,
        nullif(trim("pg_ast"::text), '')::numeric(5,1)  as pg_ast,
        nullif(trim("pg_stl"::text), '')::numeric(5,1)  as pg_stl,
        nullif(trim("pg_blk"::text), '')::numeric(5,1)  as pg_blk,
        nullif(trim("pg_fg3"::text), '')::numeric(5,1)  as pg_fg3,
        nullif(trim("pg_tov"::text), '')::numeric(5,1)  as pg_tov

    from source
    where nullif(trim("bbr_id"::text), '') is not null
)

select * from cleaned
