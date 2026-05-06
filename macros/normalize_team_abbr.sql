{#
    Normaliza códigos de time do BBR para abreviações NBA canônicas.

    O Basketball Reference usa códigos legados para 3 franquias:
      BRK → BKN (Brooklyn Nets)
      CHO → CHA (Charlotte Hornets)
      PHO → PHX (Phoenix Suns)

    Os demais 27 times já usam códigos NBA padrão.

    Uso:
        {{ normalize_team_abbr('"Team"') }}                         as team_abbr
        {{ normalize_team_abbr('"opponent"') }}                     as opponent_abbr
#}

{% macro normalize_team_abbr(column) %}
    case upper(trim({{ column }}))
        when 'BRK' then 'BKN'
        when 'CHO' then 'CHA'
        when 'PHO' then 'PHX'
        else upper(trim({{ column }}))
    end
{% endmacro %}
