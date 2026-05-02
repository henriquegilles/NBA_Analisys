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

-- Captura mudanças de roster ao longo do tempo.
-- Casos registrados automaticamente:
--   • Troca de time (trade, waiver, free agency)
--   • Mudança de posição reportada pelo BBR
--   • Jogador que saiu (hard delete → dbt_valid_to preenchido)
--
-- Excluímos linhas agregadas (2TM/3TM/TOT) — queremos apenas o estado
-- real de cada jogador por time específico.
--
-- Para detectar trocas durante a temporada:
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
