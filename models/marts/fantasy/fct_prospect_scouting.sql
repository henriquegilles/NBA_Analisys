-- fct_prospect_scouting
-- Grão: 1 linha por prospecto que tem ao menos um comp com desfecho NBA.
--
-- O PRODUTO do Domínio B: para cada prospecto, projeta o desfecho NBA a partir
-- dos desfechos dos seus comps (D-04). Junta int_prospect__comps (os k vizinhos)
-- a fct_college_to_nba_outcomes (quem dos comps chegou à NBA).
--
-- DUAS projeções por categoria (Melhoria 2, doc 05):
--   proj_*            → média SIMPLES dos comps (default atual).
--   proj_*_weighted   → média PONDERADA por inverso-da-distância (comp colado
--                       pesa mais). w_i = 1/(distance_i + ε), ε = mediana das
--                       distâncias (data-driven). NULL-aware por categoria.
-- Mantemos as duas lado a lado; a troca do default só após backtest leave-one-out.
--
-- Sinal de CONFIANÇA (Melhoria 1, D-33): confidence/coverage_6cat/mean_comp_distance.
-- Limiares calibrados pelos TERCIS reais da distância média: t33≈1.43, t67≈1.78.

{% set k = 8 %}                {# nº de comps por prospecto (igual ao int_prospect__comps) #}
{% set dist_low = 1.43 %}      {# t33 da distância média — abaixo = bons análogos #}
{% set dist_high = 1.78 %}     {# t67 da distância média — acima = extrapolação #}

with comps as (
    select prospect_id, prospect_name, prospect_season, prospect_archetype,
           comp_id, comp_rank, used_archetype_fallback, distance
    from {{ ref('int_prospect__comps') }}
),

outcomes as (
    select cbb_id,
           nba_pg_pts, nba_pg_trb, nba_pg_ast,
           nba_pg_stocks, nba_pg_fg3, nba_pg_tov,
           nba_win_shares, nba_vorp
    from {{ ref('fct_college_to_nba_outcomes') }}
),

-- ε da ponderação = mediana de TODAS as distâncias dos comps (data-driven,
-- livre de escala). Evita explosão quando distance ≈ 0 e controla a agressividade.
eps as (
    select percentile_cont(0.5) within group (order by distance) as eps
    from comps
),

-- Distância média sobre TODOS os k comps (não só os com desfecho) — base do
-- sinal de confiança; é a população em que os tercis foram calibrados.
comp_distance as (
    select prospect_id, avg(distance) as mean_comp_distance
    from comps
    group by prospect_id
),

comp_outcomes as (
    -- lista plana: 1 linha por (prospecto × comp que chegou à NBA), com o peso.
    select
        c.prospect_id,
        c.prospect_name,
        c.prospect_season,
        c.prospect_archetype,
        c.used_archetype_fallback,
        1.0 / (c.distance + e.eps)                     as w,
        o.nba_pg_pts, o.nba_pg_trb, o.nba_pg_ast,
        o.nba_pg_stocks, o.nba_pg_fg3, o.nba_pg_tov,
        o.nba_win_shares, o.nba_vorp
    from comps c
    join outcomes o on c.comp_id = o.cbb_id        -- só comps que chegaram à NBA
    cross join eps e
),

aggregated as (
    select
        prospect_id,
        prospect_name,
        prospect_season,
        prospect_archetype,
        bool_or(used_archetype_fallback)              as used_archetype_fallback,
        count(*)                                      as n_comps_with_outcome,
        count(nba_pg_stocks)                          as n_comps_with_6cat,

        -- Projeção SIMPLES (default). avg() ignora NULL → projeta sobre os comps
        -- cuja carreira NBA já foi raspada.
        round(avg(nba_pg_pts), 1)                     as proj_pg_pts,
        round(avg(nba_pg_trb), 1)                     as proj_pg_trb,
        round(avg(nba_pg_ast), 1)                     as proj_pg_ast,
        round(avg(nba_pg_stocks), 1)                  as proj_pg_stocks,
        round(avg(nba_pg_fg3), 1)                     as proj_pg_fg3,
        round(avg(nba_pg_tov), 1)                     as proj_pg_tov,
        round(avg(nba_win_shares), 1)                 as proj_win_shares,
        round(avg(nba_vorp), 1)                       as proj_vorp,

        -- Projeção PONDERADA por inverso-da-distância (Melhoria 2). NULL-aware:
        -- por categoria, renormaliza o peso só sobre os comps que têm a categoria.
        round((sum(w * nba_pg_pts)    filter (where nba_pg_pts    is not null)
             / nullif(sum(w)          filter (where nba_pg_pts    is not null), 0))::numeric, 1) as proj_pg_pts_weighted,
        round((sum(w * nba_pg_trb)    filter (where nba_pg_trb    is not null)
             / nullif(sum(w)          filter (where nba_pg_trb    is not null), 0))::numeric, 1) as proj_pg_trb_weighted,
        round((sum(w * nba_pg_ast)    filter (where nba_pg_ast    is not null)
             / nullif(sum(w)          filter (where nba_pg_ast    is not null), 0))::numeric, 1) as proj_pg_ast_weighted,
        round((sum(w * nba_pg_stocks) filter (where nba_pg_stocks is not null)
             / nullif(sum(w)          filter (where nba_pg_stocks is not null), 0))::numeric, 1) as proj_pg_stocks_weighted,
        round((sum(w * nba_pg_fg3)    filter (where nba_pg_fg3    is not null)
             / nullif(sum(w)          filter (where nba_pg_fg3    is not null), 0))::numeric, 1) as proj_pg_fg3_weighted,
        round((sum(w * nba_pg_tov)    filter (where nba_pg_tov    is not null)
             / nullif(sum(w)          filter (where nba_pg_tov    is not null), 0))::numeric, 1) as proj_pg_tov_weighted
    from comp_outcomes
    group by 1, 2, 3, 4
)

select
    a.*,
    round(d.mean_comp_distance::numeric, 3)           as mean_comp_distance,
    round(a.n_comps_with_6cat::numeric / {{ k }}, 2)  as coverage_6cat,

    -- Sinal de confiança (Melhoria 1, calibrável via dist_low/dist_high acima).
    case
        when a.n_comps_with_6cat < 3
          or a.used_archetype_fallback
          or d.mean_comp_distance > {{ dist_high }}                  then 'baixa'
        when a.n_comps_with_6cat >= 6
         and not a.used_archetype_fallback
         and d.mean_comp_distance < {{ dist_low }}                   then 'alta'
        else 'media'
    end                                               as confidence

from aggregated a
join comp_distance d using (prospect_id)
