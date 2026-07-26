#!/usr/bin/env python3
"""
Test differenziale: la funzione prodotta dall'agente e' CORRETTA davvero?

Indipendente dal teorema che l'agente ha dimostrato. Genera array ordinati,
cerca ogni elemento presente + valori assenti, e confronta con la semantica
attesa (trova <=> presente).

Uso: differenziale.py <run> <nomeFunzione>
"""
import subprocess, os, sys, pathlib, random

BASE = pathlib.Path("/private/tmp/claude-501/-Users-pinperepette-Github-blog-articoli/"
                    "79f1d3aa-d083-4480-836e-4018a213f872/scratchpad/esperimento")
ENV = {**os.environ, "PATH": f"{os.path.expanduser('~')}/.elan/bin:" + os.environ["PATH"]}

TEMPLATE = """
-- ===== test differenziale appeso in coda =====
def _refFind (a : Array Int) (t : Int) : Option Nat :=
  let rec go (i : Nat) : Option Nat :=
    if h : i < a.size then (if a[i]! = t then some i else go (i+1)) else none
  termination_by a.size - i
  go 0

def _casi : List (Array Int × Int) := {CASI}

/-- Conta i casi in cui la funzione dell'agente diverge dalla semantica attesa
    "trova se e solo se presente". Un indice diverso ma valido non conta come errore. -/
def _diff : List (Array Int × Int) :=
  _casi.filter (fun (a, t) =>
    match {FN} a t, _refFind a t with
    | some i, some _ => !(decide (i < a.size) && decide (a[i]! = t))
    | none,   none   => false
    | _,      _      => true)

#eval (_casi.length, _diff.length)
#eval _diff.take 5
"""


def genera_casi(n=60, seed=20260726):
    rnd = random.Random(seed)
    casi = []
    for _ in range(n):
        size = rnd.randint(0, 12)
        arr = sorted(rnd.randint(-20, 20) for _ in range(size))
        # cerca sia elementi presenti sia assenti
        if arr and rnd.random() < 0.7:
            t = rnd.choice(arr)
        else:
            t = rnd.randint(-25, 25)
        casi.append((arr, t))
    lean = ", ".join(f"(#[{', '.join(str(x) for x in a)}], {t})" for a, t in casi)
    return "[" + lean + "]"


def main():
    run, fn = sys.argv[1], sys.argv[2]
    d = BASE / run
    w = BASE / f".diff_{run}"
    import shutil
    if w.exists():
        shutil.rmtree(w)
    shutil.copytree(d, w)
    src = (d / "Ricerca.lean").read_text()
    body = TEMPLATE.replace("{CASI}", genera_casi()).replace("{FN}", fn)
    (w / "Ricerca.lean").write_text(src + "\n" + body)
    r = subprocess.run("lake env lean Ricerca.lean", shell=True, cwd=w, env=ENV,
                       capture_output=True, text=True, timeout=900)
    print(r.stdout + r.stderr)
    shutil.rmtree(w, ignore_errors=True)


if __name__ == "__main__":
    main()
