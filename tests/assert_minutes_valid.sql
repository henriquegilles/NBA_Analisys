-- Singular test: minutos jogados devem estar entre 0 e 60 (cobre até 3 prorrogações).
-- Retorna linhas que FALHAM — resultado vazio = teste passou.
select
    game_player_key,
    player_name,
    game_date,
    minutes_played
from {{ ref('fct_player_game_log') }}
where minutes_played is not null
  and (minutes_played < 0 or minutes_played > 60)
