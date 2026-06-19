-- int_player__fantasy_categories
-- Grão: 1 linha por jogador × jogo.
--
-- Isola as 7 categorias da liga Bandeja de 3 a partir do game log e deriva
-- STOCKS (stl + blk). Mantém `tov` como categoria normal — a inversão
-- ("menos é melhor") é aplicada no cálculo de z-score, não aqui.
--
-- É a base das agregações de valoração (fct_player_fantasy_value_season
-- e _recent). Projeção pura: não filtra nem agrega, só recorta e renomeia.

with game_log as (
    select * from {{ ref('fct_player_game_log') }}
),

final as (
    select
        -- Chaves
        game_player_key,
        player_key,
        bbr_id,
        player_name,
        season,

        -- Contexto
        game_date,
        minutes_played,

        -- As 7 categorias da liga
        pts,                       -- 1. Pontos
        trb,                       -- 2. Rebotes
        ast,                       -- 3. Assistências
        stl + blk    as stocks,    -- 4. STOCKS = roubos + tocos
        three_p,                   -- 5. Bolas de 3
        plus_minus,                -- 6. Plus/Minus
        tov,                       -- 7. Turnovers (invertida — tratada no z-score)

        -- Componentes do STOCKS mantidos para rastreabilidade
        stl,
        blk

    from game_log
)

select * from final
