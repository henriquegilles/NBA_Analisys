{#
    Gera um ID inteiro de 8 dígitos a partir de uma lista de campos.

    Usa hashtext() do PostgreSQL (32-bit hash) com cast para bigint
    antes de abs() para evitar overflow no valor INT_MIN.
    O módulo 90_000_000 + offset 10_000_000 garante sempre 8 dígitos
    (10000000 a 99999999) sem valores menores.

    Uso:
        {{ generate_id(['col_a', 'col_b']) }}

    Colisões: probabilidade desprezível para os volumes deste projeto
    (<100k linhas por tabela). Para conjuntos maiores, preferir UUID.
#}

{% macro generate_id(field_list) %}
    (10000000 + (
        abs(hashtext(
            concat_ws('|',
                {% for field in field_list %}
                    cast({{ field }} as varchar)
                    {%- if not loop.last %},{% endif %}
                {% endfor %}
            )
        ))::bigint % 90000000
    ))
{% endmacro %}
