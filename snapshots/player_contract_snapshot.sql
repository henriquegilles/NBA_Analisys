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

-- Captura mudanças de contrato ao longo do tempo.
-- Casos registrados automaticamente:
--   • Troca de time (buyout + assinatura com novo time)
--   • Renegociação (novo valor garantido ou extensão)
--   • Opção de jogador exercida ou rejeitada
--   • Conversão de contrato two-way para standard
--
-- Colunas adicionadas pelo dbt snapshot:
--   dbt_scd_id, dbt_updated_at, dbt_valid_from, dbt_valid_to
--
-- Para ver o histórico de um jogador:
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
