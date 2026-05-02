-- int_games__from_gamelogs
-- Deriva entidades únicas de jogo a partir dos game logs individuais.
-- Grain: 1 linha por jogo (game_date × home_team_abbr).
--
-- Como o BBR game log é por jogador, cada jogo aparece ~12 vezes por time.
-- Aqui fazemos DISTINCT para extrair apenas os atributos do JOGO, não do jogador.
--
-- Lógica home/away:
--   home_away = 'home' → team_abbr é o time da casa
--   home_away = 'away' → team_abbr é o visitante; opponent_abbr é a casa
--
-- Limitação: point_diff e result vêm do ponto de vista do jogador e são
-- convertidos para a perspectiva do time da casa.

with logs as (
    select * from {{ ref('stg_bbr__player_gamelogs') }}
    where home_away is not null
      and team_abbr is not null
      and opponent_abbr is not null
),

games as (
    select distinct
        game_date,
        season,

        case when home_away = 'home' then team_abbr
             else opponent_abbr
        end                                                     as home_team_abbr,

        case when home_away = 'away' then team_abbr
             else opponent_abbr
        end                                                     as away_team_abbr,

        -- Resultado do time da casa (W = casa ganhou)
        case
            when home_away = 'home' and result = 'W' then 'W'
            when home_away = 'home' and result = 'L' then 'L'
            when home_away = 'away' and result = 'W' then 'L'
            when home_away = 'away' and result = 'L' then 'W'
        end                                                     as home_result,

        -- Margem do ponto de vista da casa (positivo = casa ganhou)
        case
            when home_away = 'home' then point_diff
            when home_away = 'away' then -point_diff
        end                                                     as home_point_diff

    from logs
)

select * from games
