-- Singular test: no player can have negative points in a game.
-- Returns FAILING rows — empty result = test passed.
select
    game_player_key,
    player_name,
    game_date,
    pts
from {{ ref('fct_player_game_log') }}
where pts is not null
  and pts < 0
