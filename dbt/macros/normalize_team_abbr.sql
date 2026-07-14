{#
    Normalizes BBR team codes to canonical NBA abbreviations.

    Basketball Reference uses legacy codes for 3 franchises:
      BRK → BKN (Brooklyn Nets)
      CHO → CHA (Charlotte Hornets)
      PHO → PHX (Phoenix Suns)

    The other 27 teams already use standard NBA codes.

    Usage:
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
