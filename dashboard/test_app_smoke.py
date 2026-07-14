"""
Headless smoke test of the unified dashboard (project standard — runbook #28):
runs the whole app with streamlit.testing.v1.AppTest and fails if ANY tab
raises an exception. In Streamlit tabs are not lazy — a single run executes
the code of all of them — but beyond that this test:

  1. validates the full run (every tab, with or without the DB);
  2. interacts with the War tab's dropdown (switching rivals re-renders);
  3. simulates Postgres DOWN (invalid port) and requires the app to stay up,
     with a warning on the DB tabs instead of a stacktrace.

Run:  source .venv/bin/activate && python dashboard/test_app_smoke.py
Exits with code 0 = all green; 1 = failed (prints the reason).
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
    print("== 1. Full run (all tabs execute in one run) ==")
    at = run_app()
    check("app runs without an exception", not at.exception,
          str(at.exception[0].value) if at.exception else "")
    check("16 tabs rendered", len(at.tabs) == 16, f"found {len(at.tabs)}")
    # content anchors for each tab family
    subheaders = " | ".join(s.value for s in at.subheader)
    for anchor in ["Roster —", "League players", "Predicts v2", "War",
                   "Free Agency", "Draft Board", "League strength",
                   "League salaries"]:
        check(f"tab with anchor '{anchor}'", anchor in subheaders)

    print("== 2. Interaction: rival dropdown on the War tab ==")
    rival_sb = [sb for sb in at.selectbox if sb.label == "Rival"]
    check("Rival dropdown exists", len(rival_sb) == 1)
    if rival_sb:
        opts = rival_sb[0].options
        check("23 rivals in the dropdown", len(opts) == 23, f"{len(opts)} options")
        rival_sb[0].select(opts[-1])
        at.run()                              # re-render on top of the same AppTest
        check("switching rivals re-renders without an exception", not at.exception,
              str(at.exception[0].value) if at.exception else "")

    print("== 2b. Interaction: toggle heatmap -> radar on the FA tab ==")
    viz = [r for r in at.radio if r.key == "fa_viz"]
    check("view toggle exists", len(viz) == 1)
    if viz:
        viz[0].set_value("🕸️ Radar (compare)")
        at.run()
        check("radar renders without an exception", not at.exception,
              str(at.exception[0].value) if at.exception else "")

    print("== 3. Fallback: Postgres down ==")
    os.environ["DBT_PORT"] = "59999"          # dead port → connection fails
    import ui_common
    ui_common.reset_db_caches()               # simulates a dead connection after a restart
    try:
        at3 = run_app()
        check("app runs without an exception WITH the DB down", not at3.exception,
              str(at3.exception[0].value) if at3.exception else "")
        warnings = " ".join(w.value for w in at3.warning)
        check("DB tabs show a clear warning", "Postgres is down" in warnings)
        subheaders3 = " | ".join(s.value for s in at3.subheader)
        check("seed tabs keep working", "Roster —" in subheaders3
              and "Predicts v2" in subheaders3)
    finally:
        os.environ.pop("DBT_PORT", None)

    print()
    if FAILS:
        print(f"FAILED ({len(FAILS)}):")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("SMOKE GREEN — all tabs OK (with and without Postgres).")


if __name__ == "__main__":
    main()
