{#
    Thin wrapper around dbt_utils.generate_surrogate_key.
    Delegates to dbt_utils so NULL handling, type coercion, and
    cross-database portability are all handled by the package.

    Run `dbt deps` once to install dbt_utils before using this.

    Usage:
        {{ generate_surrogate_key(['col_a', 'col_b']) }}
#}

{% macro generate_surrogate_key(field_list) %}
    {{ return(dbt_utils.generate_surrogate_key(field_list)) }}
{% endmacro %}
