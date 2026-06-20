-- int_prospect__college_stats
-- Grão: jogador × temporada de college (acima do piso de minutos).
--
-- Monta o PERFIL do prospecto para o scouting (Domínio B): as 6 categorias
-- por-40-min + contexto (senioridade, eficiência, uso, força de calendário,
-- arquétipo) + sinal de TRAJETÓRIA (evolução vs. temporada anterior).
-- É a base de onde saem tanto os prospectos históricos (→ outcomes NBA) quanto
-- os da classe atual (→ comps).
--
-- Decisões aplicadas:
--   D-10  per-40 já vem pronto do staging (sem cálculo aqui).
--   D-26  `class` → `class_rank` ordinal (FR=1…SR=4), proxy de idade/senioridade.
--   D-28  arquétipo = G/F/C (CBB Reference só classifica nesses 3 níveis; o
--         "fino de 5 posições" do D-23 não existe na fonte). G→guard, F→wing, C→big.
--   D-24  trajetória = z-score do delta de produção por-40 vs. temporada anterior
--         do MESMO jogador + flag (melhorando/estável/piorando).
--   Piso de minutos: corta walk-ons/garbage time, cujos per-40 são ruído
--   (extrapolação de pouquíssimos minutos). Calibrável via `min_minutes` abaixo.

{% set min_minutes = 200 %}   {# piso (calibrável). Em ~841 linhas, <200min ≈ 37% (cauda de ruído). #}
{% set traj_band = 0.5 %}     {# banda de "estável" em desvios-padrão do delta de produção. #}

with college as (
    select *
    from {{ ref('stg_cbb__player_season') }}
    where minutes_played >= {{ min_minutes }}
),

enriched as (
    select
        -- Identidade
        cbb_id,
        player_name,
        school,
        season,

        -- Arquétipo / posição (D-28)
        position,
        case position
            when 'G' then 'guard'
            when 'F' then 'wing'
            when 'C' then 'big'
            else 'unknown'
        end                                                   as archetype,

        -- Senioridade (D-26 — proxy de idade)
        class,
        case class when 'FR' then 1 when 'SO' then 2
                   when 'JR' then 3 when 'SR' then 4 end      as class_rank,

        -- 6 categorias por-40 (D-10)
        pts_per_40,
        trb_per_40,
        ast_per_40,
        stl_per_40,
        blk_per_40,
        coalesce(stl_per_40, 0) + coalesce(blk_per_40, 0)     as stocks_per_40,   -- categoria derivada
        three_p_per_40,
        tov_per_40,

        -- Composto de produção por-40 (base da trajetória): conta o que ajuda,
        -- desconta turnovers. Não é a valoração final (z-score 6-cat vem depois).
        coalesce(pts_per_40, 0) + coalesce(trb_per_40, 0) + coalesce(ast_per_40, 0)
          + coalesce(stl_per_40, 0) + coalesce(blk_per_40, 0) + coalesce(three_p_per_40, 0)
          - coalesce(tov_per_40, 0)                           as production_per_40,

        -- Contexto
        ts_pct,
        usg_pct,
        team_sos,
        rsci_rank,
        minutes_played,
        games
    from college
),

-- Temporada anterior do MESMO jogador (cbb_id), em ordem cronológica.
-- `season` no formato 'YYYY-YY' ordena lexicograficamente igual à cronologia.
with_prior as (
    select
        *,
        lag(season)             over w as prev_season,
        lag(production_per_40)  over w as prev_production_per_40,
        lag(ts_pct)             over w as prev_ts_pct
    from enriched
    window w as (partition by cbb_id order by season)
),

delta as (
    select
        *,
        production_per_40 - prev_production_per_40 as d_production_per_40,
        ts_pct - prev_ts_pct                       as d_ts_pct
    from with_prior
),

-- Momentos populacionais do delta (só sobre quem tem temporada anterior),
-- para padronizar a trajetória (D-24).
moments as (
    select
        avg(d_production_per_40)         as mu,
        stddev_samp(d_production_per_40) as sd
    from delta
    where prev_season is not null
),

final as (
    select
        d.*,
        case when d.prev_season is null then null
             else (d.d_production_per_40 - m.mu) / nullif(m.sd, 0)
        end as d_production_z,

        case
            when d.prev_season is null                                   then 'sem_historico'
            when (d.d_production_per_40 - m.mu) / nullif(m.sd, 0) >=  {{ traj_band }} then 'melhorando'
            when (d.d_production_per_40 - m.mu) / nullif(m.sd, 0) <= -{{ traj_band }} then 'piorando'
            else 'estavel'
        end as trajectory_flag
    from delta d
    cross join moments m
)

select * from final
