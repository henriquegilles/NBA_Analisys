-- Singular test: minutes played must be between 0 and 60 (covers up to 3 overtimes).
-- Returns FAILING rows — empty result = test passed.
select
    game_player_key,
    player_name,
    game_date,
    minutes_played
from {{ ref('fct_player_game_log') }}
where minutes_played is not null
  and (minutes_played < 0 or minutes_played > 60)
