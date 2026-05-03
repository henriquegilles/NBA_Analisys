-- Singular test: nenhum jogador pode ter pontos negativos num jogo.
-- Retorna linhas que FALHAM — resultado vazio = teste passou.
select
    game_player_key,
    player_name,
    game_date,
    pts
from {{ ref('fct_player_game_log') }}
where pts is not null
  and pts < 0
