"""
Smoke-test headless do painel unificado (padrão do projeto — runbook #28):
roda o app inteiro com streamlit.testing.v1.AppTest e falha se QUALQUER aba
levantar exceção. No Streamlit as abas não são lazy — um único run executa o
código de todas — mas além disso este teste:

  1. valida o run completo (todas as abas, DB disponível ou não);
  2. interage com o dropdown da aba Guerra (troca de rival re-renderiza);
  3. simula Postgres FORA (porta inválida) e exige que o app continue de pé,
     com aviso nas abas de DB em vez de stacktrace.

Rodar:  source .venv/bin/activate && python dashboard/test_app_smoke.py
Sai com código 0 = tudo verde; 1 = falhou (imprime o motivo).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app.py")
sys.path.insert(0, HERE)

from streamlit.testing.v1 import AppTest

FAILS: list[str] = []


def check(label: str, cond: bool, detail: str = ""):
    print(f"  {'✅' if cond else '❌'} {label}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(f"{label}: {detail}")


def run_app(timeout=300) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.run()
    return at


def main():
    print("== 1. Run completo (todas as abas executam num run) ==")
    at = run_app()
    check("app roda sem exceção", not at.exception,
          str(at.exception[0].value) if at.exception else "")
    check("15 abas renderizadas", len(at.tabs) == 15, f"encontradas {len(at.tabs)}")
    # âncoras de conteúdo de cada família de abas
    subheaders = " | ".join(s.value for s in at.subheader)
    for anchor in ["Elenco do", "Predicts v2", "Guerra", "Free Agency",
                   "Board de Draft", "Força da liga", "Salários da liga"]:
        check(f"aba com âncora '{anchor}'", anchor in subheaders)

    print("== 2. Interação: dropdown de rival na aba Guerra ==")
    rival_sb = [sb for sb in at.selectbox if sb.label == "Rival"]
    check("dropdown Rival existe", len(rival_sb) == 1)
    if rival_sb:
        opts = rival_sb[0].options
        check("23 rivais no dropdown", len(opts) == 23, f"{len(opts)} opções")
        rival_sb[0].select(opts[-1])
        at.run()                              # re-render em cima do mesmo AppTest
        check("troca de rival re-renderiza sem exceção", not at.exception,
              str(at.exception[0].value) if at.exception else "")

    print("== 2b. Interação: alternar calor -> radar na aba FA ==")
    viz = [r for r in at.radio if r.key == "fa_viz"]
    check("toggle de visualização existe", len(viz) == 1)
    if viz:
        viz[0].set_value("🕸️ Radar (comparar)")
        at.run()
        check("radar renderiza sem exceção", not at.exception,
              str(at.exception[0].value) if at.exception else "")

    print("== 3. Fallback: Postgres fora do ar ==")
    os.environ["DBT_PORT"] = "59999"          # porta morta → conexão falha
    import ui_common
    ui_common.reset_db_caches()               # simula conexão morta pós-restart
    try:
        at3 = run_app()
        check("app roda sem exceção COM banco fora", not at3.exception,
              str(at3.exception[0].value) if at3.exception else "")
        warnings = " ".join(w.value for w in at3.warning)
        check("abas de DB mostram aviso claro", "Postgres fora do ar" in warnings)
        subheaders3 = " | ".join(s.value for s in at3.subheader)
        check("abas de seed seguem funcionando", "Elenco do" in subheaders3
              and "Predicts v2" in subheaders3)
    finally:
        os.environ.pop("DBT_PORT", None)

    print()
    if FAILS:
        print(f"FALHOU ({len(FAILS)}):")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("SMOKE VERDE — todas as abas OK (com e sem Postgres).")


if __name__ == "__main__":
    main()
