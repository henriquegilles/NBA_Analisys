{% snapshot player_contract_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='player_name',
        strategy='check',
        check_cols=[
            'team_abbr',
            'salary_2025_26',
            'salary_2026_27',
            'salary_2027_28',
            'salary_2028_29',
            'signed_using',
            'guaranteed',
        ],
        invalidate_hard_deletes=True,
    )
}}

-- Captures contract changes over time.
-- Cases recorded automatically:
--   • Team change (buyout + signing with a new team)
--   • Renegotiation (new guaranteed amount or extension)
--   • Player option exercised or declined
--   • Two-way contract converted to standard
--
-- Columns added by the dbt snapshot:
--   dbt_scd_id, dbt_updated_at, dbt_valid_from, dbt_valid_to
--
-- To see a player's history:
--   SELECT * FROM analytics_snapshots.player_contract_snapshot
--   WHERE player_name = 'LeBron James'
--   ORDER BY dbt_valid_from;

select
    player_name,
    team_abbr,
    salary_2024_25,
    salary_2025_26,
    salary_2026_27,
    salary_2027_28,
    salary_2028_29,
    signed_using,
    guaranteed
from {{ ref('stg_bbr__contracts') }}

{% endsnapshot %}
