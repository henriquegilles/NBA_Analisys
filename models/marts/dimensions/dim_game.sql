-- dim_game
-- Grain: 1 linha por jogo.
-- Entidade central de contexto de jogo, separada das stats dos jogadores.
--
-- Por que isso importa:
--   Sem dim_game, atributos do jogo (resultado, margem, adversário) ficam
--   repetidos ~24 vezes no fct_player_game_log (uma por jogador em quadra).
--   Isso torna COUNT(DISTINCT game_date) incorreto para contar jogos quando
--   dois times jogam no mesmo dia.
--
-- Fonte: derivado de int_games__from_gamelogs (dados de player game logs).
-- Quando box_scores.py estiver ativo, essa dimensão pode ser enriquecida
-- com venue, arena_timezone e game_status.

with games as (
    select * from {{ ref('int_games__from_gamelogs') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

final as (
    select
        {{ generate_id(['g.game_date', 'g.home_team_abbr']) }}            as game_key,

        -- Datas e temporada
        g.game_date,
        g.season,
        extract(year from g.game_date)::integer             as game_year,

        -- Times (FKs para dim_team)
        g.home_team_abbr,
        g.away_team_abbr,
        ht.team_key                                         as home_team_key,
        at_.team_key                                        as away_team_key,

        -- Resultado do ponto de vista do time da casa
        g.home_result,
        g.home_point_diff

        -- Futuro: venue, arena_timezone, tipoff_utc, game_status, attendance

    from games g
    left join dim_team ht  on g.home_team_abbr = ht.team_abbr
    left join dim_team at_ on g.away_team_abbr = at_.team_abbr
)

select * from final
