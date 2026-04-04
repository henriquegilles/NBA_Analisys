{#
    Generates a deterministic surrogate key by hashing a list of columns
    using MD5. Null values in any column are treated as the literal string
    '__NULL__' so they still produce a stable key.

    Usage:
        {{ generate_surrogate_key(['col_a', 'col_b']) }}
#}

{% macro generate_surrogate_key(field_list) %}

    md5(
        {%- for field in field_list %}
            coalesce(cast({{ field }} as text), '__NULL__')
            {%- if not loop.last %} || '|' || {% endif %}
        {%- endfor %}
    )

{% endmacro %}
