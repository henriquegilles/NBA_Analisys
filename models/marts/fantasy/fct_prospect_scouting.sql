-- fct_prospect_scouting
-- Grão: 1 linha por prospecto que tem ao menos um comp com desfecho NBA.
--
-- O PRODUTO do Domínio B: para cada prospecto, projeta o desfecho NBA pela
-- MÉDIA dos desfechos dos seus comps (D-04). Junta int_prospect__comps
-- (os k vizinhos) a fct_college_to_nba_outcomes (quem dos comps chegou à NBA)
-- e tira a média — só sobre os comps que efetivamente jogaram na NBA.
--
-- `n_comps_with_outcome` é o "tamanho da amostra" da projeção: quanto maior,
-- mais confiável. Prospectos cujos comps nunca chegaram à NBA não aparecem
-- (projeção vazia = sinal fraco de NBA).

with comps as (
    select prospect_id, prospect_name, prospect_season, prospect_archetype,
           comp_id, comp_rank, used_archetype_fallback
    from {{ ref('int_prospect__comps') }}
),

outcomes as (
    select cbb_id,
           nba_pg_pts, nba_pg_trb, nba_pg_ast,
           nba_pg_stocks, nba_pg_fg3, nba_pg_tov,
           nba_win_shares, nba_vorp
    from {{ ref('fct_college_to_nba_outcomes') }}
),

comp_outcomes as (
    -- lista plana: 1 linha por (prospecto × comp que chegou à NBA)
    select
        c.prospect_id,
        c.prospect_name,
        c.prospect_season,
        c.prospect_archetype,
        c.used_archetype_fallback,
        o.nba_pg_pts, o.nba_pg_trb, o.nba_pg_ast,
        o.nba_pg_stocks, o.nba_pg_fg3, o.nba_pg_tov,
        o.nba_win_shares, o.nba_vorp
    from comps c
    join outcomes o on c.comp_id = o.cbb_id        -- só comps que chegaram à NBA
)

select
    prospect_id,
    prospect_name,
    prospect_season,
    prospect_archetype,
    bool_or(used_archetype_fallback)              as used_archetype_fallback,
    count(*)                                      as n_comps_with_outcome,
    round(avg(nba_pg_pts), 1)                     as proj_pg_pts,
    round(avg(nba_pg_trb), 1)                     as proj_pg_trb,
    round(avg(nba_pg_ast), 1)                     as proj_pg_ast,
    -- 6-cat: avg() ignora NULL, então projeta sobre os comps cuja carreira NBA
    -- já foi raspada (pode ser < n_comps_with_outcome enquanto o backbone cresce).
    round(avg(nba_pg_stocks), 1)                  as proj_pg_stocks,
    round(avg(nba_pg_fg3), 1)                     as proj_pg_fg3,
    round(avg(nba_pg_tov), 1)                     as proj_pg_tov,
    count(nba_pg_stocks)                          as n_comps_with_6cat,
    round(avg(nba_win_shares), 1)                 as proj_win_shares,
    round(avg(nba_vorp), 1)                       as proj_vorp
from comp_outcomes
group by 1, 2, 3, 4
