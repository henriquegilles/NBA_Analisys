{% snapshot player_roster_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='player_name',
        strategy='check',
        check_cols=['team_abbr', 'position', 'age'],
        invalidate_hard_deletes=True,
    )
}}

-- Captures roster changes over time.
-- Cases recorded automatically:
--   • Team change (trade, waiver, free agency)
--   • Position change reported by BBR
--   • Player who left (hard delete → dbt_valid_to filled in)
--
-- Aggregate rows (2TM/3TM/TOT) are excluded — we only want each
-- player's actual state on a specific team.
--
-- To detect in-season team changes:
--   SELECT player_name, team_abbr, dbt_valid_from, dbt_valid_to
--   FROM analytics_snapshots.player_roster_snapshot
--   WHERE dbt_valid_to IS NOT NULL
--   ORDER BY dbt_valid_from DESC;

select
    player_name,
    bbr_id,
    team_abbr,
    position,
    age,
    season
from {{ ref('stg_bbr__players') }}
where team_abbr != 'TOT'
  and team_abbr !~ '^\d+TM$'

{% endsnapshot %}
