-- Singular test: Win Shares per season must not exceed 25 (all-time record ~21).
-- Returns FAILING rows — empty result = test passed.
select
    player_key,
    player_name,
    season,
    season_type,
    win_shares
from {{ ref('fct_player_advanced_stats') }}
where win_shares is not null
  and win_shares > 25
