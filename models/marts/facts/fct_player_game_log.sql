-- fct_player_game_log
-- Grain: 1 linha por jogador × jogo.
-- Fonte: páginas de game log individuais do BBR.
--
-- game_key → FK para dim_game (entidade do jogo: quem jogou quem, resultado do jogo)
-- player_key → FK via bbr_id (estável — não quebra com correções de nome no BBR)
--
-- Atributos do jogador mantidos como dimensões degeneradas (Kimball):
--   home_away, result, games_started — são do ponto de vista do jogador e
--   consultados frequentemente sem necessidade de JOIN com dim_game.
--
-- point_diff foi movido para dim_game (medida do jogo, não do jogador).

with logs as (
    select * from {{ ref('stg_bbr__player_gamelogs') }}
),

dim_player as (
    select * from {{ ref('dim_player') }}
),

dim_team as (
    select * from {{ ref('dim_team') }}
),

dim_game as (
    select * from {{ ref('dim_game') }}
),

final as (
    select
        -- PK: bbr_id + game_date — um jogador não joga duas vezes no mesmo dia
        {{ generate_id(['l.bbr_id', 'l.game_date']) }}               as game_player_key,

        -- Foreign keys
        dp.player_key,
        dt.team_key,
        opp.team_key                                        as opponent_team_key,
        dg.game_key,

        -- Identificadores naturais
        l.bbr_id,
        l.player_name,
        l.season,

        -- Contexto do jogo (dimensões degeneradas — do ponto de vista do jogador)
        l.game_date,
        l.team_abbr,
        l.opponent_abbr,
        l.home_away,                -- 'home' | 'away' (perspectiva do jogador)
        l.result,                   -- 'W' | 'L'       (perspectiva do time do jogador)
        l.games_started,            -- 1 = titular | 0 = reserva

        -- Tempo de jogo
        l.minutes_played,           -- decimal (ex: 32.23)
        l.minutes_played_str,       -- string original "MM:SS" para display

        -- Arremessos de quadra
        l.fg,
        l.fga,
        l.fg_pct,
        l.three_p,
        l.three_pa,
        l.three_p_pct,

        -- Lances livres
        l.ft,
        l.fta,
        l.ft_pct,

        -- Rebotes
        l.orb,
        l.drb,
        l.trb,

        -- Outros
        l.ast,
        l.stl,
        l.blk,
        l.tov,
        l.pf,
        l.pts,

        -- Métrica composta
        -- Game Score (Hollinger): resume a performance em um número
        -- pts + 0.4*fg − 0.7*fga − 0.4*(fta−ft) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk − 0.4*pf − tov
        l.game_score,
        l.plus_minus

    from logs l
    left join dim_player dp on l.bbr_id        = dp.bbr_id
    left join dim_team   dt  on l.team_abbr     = dt.team_abbr
    left join dim_team   opp on l.opponent_abbr = opp.team_abbr
    left join dim_game   dg  on l.game_date     = dg.game_date
        and (
            (l.home_away = 'home' and l.team_abbr     = dg.home_team_abbr)
            or
            (l.home_away = 'away' and l.opponent_abbr = dg.home_team_abbr)
        )
)

select * from final
