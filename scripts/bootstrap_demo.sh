#!/usr/bin/env bash
# Bootstrap de demonstração — roda o projeto inteiro a partir de um clone novo,
# SEM scraping, usando as amostras consistentes versionadas em ci/sample_seeds/
# (as mesmas do CI). Dá pra ver o pipeline + o painel funcionando em minutos.
#
# Dados de verdade vêm dos scrapers (ver README "Data Sources") — isto é só o
# atalho reproduzível. Requer Postgres de pé (docker compose up -d postgres).
#
# Uso:
#   ./scripts/bootstrap_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Guarda: não sobrescrever dados reais já presentes (gamelog real ~4MB; demo ~184KB).
if [ -f seeds/player_gamelogs.csv ] && [ "$(wc -c < seeds/player_gamelogs.csv)" -gt 1000000 ]; then
  echo "⚠️  seeds/ já tem dados reais (player_gamelogs grande)."
  echo "    Este script é para clone novo/demo e SOBRESCREVERIA seus seeds."
  echo "    Se realmente quer usar os dados de amostra, rode: BOOTSTRAP_FORCE=1 $0"
  [ "${BOOTSTRAP_FORCE:-0}" = "1" ] || exit 1
fi

echo "→ copiando amostras de demo para seeds/"
cp ci/sample_seeds/*.csv seeds/

echo "→ dbt deps"
dbt deps --profiles-dir .dbt

echo "→ dbt build (seed + run + test) com dados de amostra"
dbt build --profiles-dir .dbt

echo
echo "✓ Pronto. O warehouse de demo está populado e testado."
echo "  Abra o painel:  streamlit run dashboard/app.py   →  http://localhost:8501"
