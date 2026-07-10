{#
  Normaliza nome de jogador para JOIN entre camadas (fantasy seeds <-> valoração NBA).
  Remove acentos comuns (pt/es/sr), minúsculas, tira pontuação/espaços.
  Centraliza a regra p/ evitar o bug de acento (Dončić/Jokić apareciam como FA).
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
