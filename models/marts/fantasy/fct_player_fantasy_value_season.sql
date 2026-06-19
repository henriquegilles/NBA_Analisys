-- fct_player_fantasy_value_season
-- Grão: 1 linha por jogador. Valor fantasy na TEMPORADA CHEIA.
--
-- Para cada uma das 7 categorias calcula o z-score do jogador (quantos
-- desvios-padrão acima/abaixo da média da liga), somável num valor agregado.
-- Turnovers entram invertidos: menos TOV que a média → z positivo (D-07).
--
-- Pool de referência (D-15): jogadores "rosteráveis" — >= 15 jogos jogados
-- E >= 12 minutos/jogo. A média e o desvio de cada categoria saem SÓ desse
-- pool, evitando que jogadores de pouquíssimo tempo distorçam a escala.
-- O z-score é calculado para TODOS; is_reference_pool marca quem entrou na régua.
--
-- Pesos das categorias são iguais (D-20). Expomos soma E média dos z-scores
-- (D-22) — a escolha final do agregado fica adiada.

{% set min_games = 15 %}
{% set min_mpg   = 12 %}

with categories as (
    select * from {{ ref('int_player__fantasy_categories') }}
    where minutes_played is not null      -- só jogos efetivamente jogados (descarta DNP)
),

-- Médias por jogo de cada jogador na temporada
per_player as (
    select
        player_key,
        bbr_id,
        player_name,
        season,
        count(*)              as games_played,
        avg(minutes_played)   as minutes_per_game,
        avg(pts)              as pts_pg,
        avg(trb)              as trb_pg,
        avg(ast)              as ast_pg,
        avg(stocks)           as stocks_pg,
        avg(three_p)          as three_p_pg,
        avg(plus_minus)       as plus_minus_pg,
        avg(tov)              as tov_pg
    from categories
    group by player_key, bbr_id, player_name, season
),

-- Marca quem entra no cálculo da referência (pool rosterável)
flagged as (
    select
        *,
        (games_played >= {{ min_games }} and minutes_per_game >= {{ min_mpg }})
            as is_reference_pool
    from per_player
),

-- Média e desvio-padrão de cada categoria, SÓ sobre o pool de referência
pool_stats as (
    select
        avg(pts_pg)        as pts_mean,        stddev_samp(pts_pg)        as pts_std,
        avg(trb_pg)        as trb_mean,        stddev_samp(trb_pg)        as trb_std,
        avg(ast_pg)        as ast_mean,        stddev_samp(ast_pg)        as ast_std,
        avg(stocks_pg)     as stocks_mean,     stddev_samp(stocks_pg)     as stocks_std,
        avg(three_p_pg)    as three_p_mean,    stddev_samp(three_p_pg)    as three_p_std,
        avg(plus_minus_pg) as plus_minus_mean, stddev_samp(plus_minus_pg) as plus_minus_std,
        avg(tov_pg)        as tov_mean,        stddev_samp(tov_pg)        as tov_std
    from flagged
    where is_reference_pool
),

-- Z-score por categoria (nullif protege contra desvio zero)
z as (
    select
        f.*,
        (f.pts_pg        - p.pts_mean)        / nullif(p.pts_std, 0)        as z_pts,
        (f.trb_pg        - p.trb_mean)        / nullif(p.trb_std, 0)        as z_trb,
        (f.ast_pg        - p.ast_mean)        / nullif(p.ast_std, 0)        as z_ast,
        (f.stocks_pg     - p.stocks_mean)     / nullif(p.stocks_std, 0)     as z_stocks,
        (f.three_p_pg    - p.three_p_mean)    / nullif(p.three_p_std, 0)    as z_three_p,
        (f.plus_minus_pg - p.plus_minus_mean) / nullif(p.plus_minus_std, 0) as z_plus_minus,
        -- Turnovers invertidos
        (p.tov_mean      - f.tov_pg)          / nullif(p.tov_std, 0)        as z_tov
    from flagged f
    cross join pool_stats p
),

final as (
    select
        {{ generate_id(['bbr_id', 'season']) }}  as fantasy_value_key,

        -- Chaves / identidade
        player_key,
        bbr_id,
        player_name,
        season,

        -- Contexto do pool
        games_played,
        minutes_per_game,
        is_reference_pool,

        -- Médias por jogo das 7 categorias (insumo do z-score, útil para display)
        pts_pg,
        trb_pg,
        ast_pg,
        stocks_pg,
        three_p_pg,
        plus_minus_pg,
        tov_pg,

        -- Z-score por categoria
        z_pts,
        z_trb,
        z_ast,
        z_stocks,
        z_three_p,
        z_plus_minus,
        z_tov,

        -- Agregados (D-22: soma E média; escolha final adiada)
        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov)
            as z_total,
        (z_pts + z_trb + z_ast + z_stocks + z_three_p + z_plus_minus + z_tov) / 7.0
            as z_mean

    from z
)

select * from final
