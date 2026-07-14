{#
    Varchar surrogate key built from a list of fields.

    Delegates to dbt_utils.generate_surrogate_key, which produces a
    32-char MD5. With a 2^128 value space, collisions are practically
    impossible regardless of data volume.

    Usage:
        {{ generate_id(['col_a', 'col_b']) }}
#}

{% macro generate_id(field_list) %}
    {{ dbt_utils.generate_surrogate_key(field_list) }}
{% endmacro %}
