#!/usr/bin/env python3
"""
La misura decisiva dell'esperimento 2.

Carica le quattro implementazioni di `rimborso` in un unico file Lean,
ognuna nel proprio namespace, e le valuta sugli stessi ordini.

Ogni implementazione ha il suo ✓ verde. La domanda e': danno lo stesso numero?

I casi sono costruiti per sondare le quattro decisioni che il ticket
NON specificava:
  A. il coupon si ripartisce sugli articoli resi?
  B. la spedizione si rimborsa?
  C. se il reso fa scendere sotto la soglia, si riaddebita la spedizione?
  D. il rimborso puo' essere negativo?
"""
import re, os, subprocess, pathlib, shutil

BASE = pathlib.Path("/private/tmp/claude-501/-Users-pinperepette-Github-blog-articoli/"
                    "79f1d3aa-d083-4480-836e-4018a213f872/scratchpad/esperimento2")
ENV = {**os.environ, "PATH": os.path.expanduser("~/.elan/bin:") + os.environ["PATH"]}

# (etichetta, prezzi, resi, coupon, quale ambiguita' sonda)
CASI = [
    ("reso parziale, con coupon",        [3000, 2000], [True,  False], 500, "A"),
    ("reso totale, ordine sotto soglia", [1000],       [True],         0,   "B"),
    ("reso totale, con coupon",          [1000, 2000], [True,  True],  300, "A+B"),
    ("reso fa scendere sotto soglia",    [3000, 3000], [True,  False], 0,   "C"),
    ("reso piccolo sotto soglia",        [4900, 150],  [False, True],  0,   "C+D"),
    ("non rende niente",                 [3000, 2000], [False, False], 500, "-"),
    ("coupon > articoli resi",           [1000, 4000], [True,  False], 1500,"A+D"),
    ("ordine vuoto",                     [],           [],             0,   "-"),
]

RUMORE = re.compile(r'^\s*(#eval|#guard_msgs|#check|#print|#reduce|/--\s*info:)')


def pulisci(src: str) -> str:
    """Toglie i comandi diagnostici: qui servono solo le definizioni e i teoremi."""
    fuori = []
    for riga in src.splitlines():
        if RUMORE.match(riga):
            continue
        fuori.append(riga)
    return "\n".join(fuori)


def qualifica(src: str) -> str:
    """Prefisso di namespace in cui e' dichiarato `def rimborso`."""
    stack = []
    for riga in src.splitlines():
        m = re.match(r'^\s*namespace\s+([\w.]+)', riga)
        if m:
            stack.append(m.group(1))
            continue
        if re.match(r'^\s*end\s+[\w.]+', riga) and stack:
            stack.pop()
            continue
        if re.match(r'^\s*(?:def|noncomputable def)\s+rimborso\b', riga):
            return ".".join(stack)
    return ""


def costruisci() -> str:
    pezzi, nomi = [], {}
    for i in (1, 2, 3, 4):
        src = (BASE / f"run{i}" / "Rimborso.lean").read_text()
        pref = qualifica(src)
        nomi[i] = f"R{i}." + (pref + "." if pref else "") + "rimborso"
        pezzi.append(f"namespace R{i}\n{pulisci(src)}\nend R{i}\n")

    righe = ["-- confronto incrociato delle quattro implementazioni", ""]
    righe += pezzi
    righe.append("def _mostra (etichetta : String) (prezzi : Array Int) "
                 "(resi : Array Bool) (coupon : Int) : IO Unit := do")
    for i in (1, 2, 3, 4):
        righe.append(f"  let v{i} := {nomi[i]} prezzi resi coupon")
    righe.append('  IO.println s!"{etichetta}|{v1}|{v2}|{v3}|{v4}"')
    righe.append("")
    righe.append("def main : IO Unit := do")
    for et, pr, re_, co, _amb in CASI:
        pa = "#[" + ", ".join(str(x) for x in pr) + "]"
        ra = "#[" + ", ".join("true" if b else "false" for b in re_) + "]"
        righe.append(f'  _mostra "{et}" ({pa} : Array Int) ({ra} : Array Bool) ({co})')
    righe.append("")
    righe.append("#eval main")
    return "\n".join(righe)


def main():
    w = BASE / ".confronto"
    if w.exists():
        shutil.rmtree(w)
    w.mkdir(parents=True)
    shutil.copy(BASE / "run1" / "lakefile.toml", w / "lakefile.toml")
    shutil.copy(BASE / "run1" / "lean-toolchain", w / "lean-toolchain")
    (w / "Rimborso.lean").write_text(costruisci())
    r = subprocess.run("lake env lean Rimborso.lean", shell=True, cwd=w, env=ENV,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr

    righe = [l for l in out.splitlines() if l.count("|") == 4]
    if not righe:
        print("NESSUN RISULTATO — output grezzo:\n")
        print(out[:3000])
        print("\nfile assemblato in:", w / "Rimborso.lean")
        return

    amb = {c[0]: c[4] for c in CASI}
    print(f"{'caso':34s} {'?':5s} {'run1':>8s} {'run2':>8s} {'run3':>8s} {'run4':>8s}   esito")
    print("-" * 88)
    disaccordi = 0
    for l in righe:
        et, *vals = l.split("|")
        concordi = len(set(vals)) == 1
        if not concordi:
            disaccordi += 1
        esito = "concordi" if concordi else f"** {len(set(vals))} RISPOSTE DIVERSE **"
        print(f"{et:34s} {amb.get(et,''):5s} " + " ".join(f"{v:>8s}" for v in vals) + f"   {esito}")
    print("-" * 88)
    print(f"casi su cui le quattro funzioni 'dimostrate corrette' non concordano: "
          f"{disaccordi}/{len(righe)}")


if __name__ == "__main__":
    main()
