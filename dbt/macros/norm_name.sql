{#
  Normalizes a player name for JOINs across layers (fantasy seeds <-> NBA valuation).
  Strips common accents (pt/es/sr), lowercases, removes punctuation/whitespace.
  Centralizes the rule to avoid the accent bug (Dončić/Jokić showed up as FAs).
#}
{% macro norm_name(col) %}
  regexp_replace(
    lower(translate(
      {{ col }},
      'áàâãäåéèêëíìîïóòôõöøúùûüçñčćšžđýÿ'
      || 'ÁÀÂÃÄÅÉÈÊËÍÌÎÏÓÒÔÕÖØÚÙÛÜÇÑČĆŠŽĐ',
      'aaaaaaeeeeiiiiooooooouuuucnccszdyy'
      || 'aaaaaaeeeeiiiiooooooouuuucnccszd'
    )),
    '[^a-z0-9]', '', 'g'
  )
{% endmacro %}
