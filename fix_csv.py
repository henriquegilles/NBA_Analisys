import csv, os, sys


def analyze(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter=",", quotechar='"')
        header = next(r, None)
        if header is None:
            return 0, []
        exp = len(header)
        bad = []
        n = 1
        for row in r:
            n += 1
            # linha totalmente vazia?
            if not row or all((c or "").strip() == "" for c in row):
                bad.append((n, "blank", 0))
            elif len(row) != exp:
                bad.append((n, "ragged", len(row)))
        return exp, bad


def fix(path):
    tmp = path + ".tmp"
    with (
        open(path, "r", encoding="utf-8", newline="") as f_in,
        open(tmp, "w", encoding="utf-8", newline="") as f_out,
    ):
        r = csv.reader(f_in, delimiter=",", quotechar='"')
        w = csv.writer(f_out, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        header = next(r, None)
        if header is None:
            return
        exp = len(header)
        w.writerow(header)
        for row in r:
            # pula linhas 100% vazias
            if not row or all((c or "").strip() == "" for c in row):
                continue
            if len(row) < exp:
                row = row + [""] * (exp - len(row))
            elif len(row) > exp:
                # junta excesso no último campo
                row = row[: exp - 1] + [",".join(row[exp - 1 :])]
            w.writerow(row)
    os.replace(tmp, path)


def main():
    paths = sys.argv[1:]
    if not paths:
        print("Use: python fix_csv.py caminho1.csv caminho2.csv ...")
        sys.exit(1)
    for p in paths:
        print(f"==> Verificando: {p}")
        exp, bad = analyze(p)
        print(f"   Colunas esperadas: {exp}")
        print(f"   Linhas problemáticas: {len(bad)}")
        if bad[:10]:
            print("   Amostras (até 10):", bad[:10])
        print("   Corrigindo...")
        fix(p)
        exp2, bad2 = analyze(p)
        print(f"   Depois: {len(bad2)} problemas\n")


if __name__ == "__main__":
    main()
