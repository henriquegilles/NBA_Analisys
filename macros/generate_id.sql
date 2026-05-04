{#
    Surrogate key varchar a partir de uma lista de campos.

    Delega para dbt_utils.generate_surrogate_key, que produz um MD5
    de 32 chars. Domínio de 2^128 valores — colisões são praticamente
    impossíveis independente do volume de dados.

    Uso:
        {{ generate_id(['col_a', 'col_b']) }}
#}

{% macro generate_id(field_list) %}
    {{ dbt_utils.generate_surrogate_key(field_list) }}
{% endmacro %}
