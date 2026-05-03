-- Singular test: Win Shares por temporada não deve ultrapassar 25 (recorde histórico ~21).
-- Retorna linhas que FALHAM — resultado vazio = teste passou.
select
    player_key,
    player_name,
    season,
    season_type,
    win_shares
from {{ ref('fct_player_advanced_stats') }}
where win_shares is not null
  and win_shares > 25
