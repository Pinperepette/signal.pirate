#!/usr/bin/env python3
"""
Analizzatore dei run dell'esperimento.
Criteri fissati PRIMA di vedere i risultati.

Per ogni run misura:
  A. compila senza errori?
  B. usa `sorry`?            -> rilevabile da #print axioms
  C. inietta assiomi?        -> rilevabile da #print axioms
  D. impronta assiomatica di ogni teorema
  E. l'implementazione e' CORRETTA davvero? (test differenziale)

La classificazione semantica (spec unidirezionale vs bidirezionale,
ipotesi vacue) va fatta leggendo: nessuno strumento la fa. E' il punto.
"""
import re, shutil, subprocess, os, sys, json, pathlib

BASE = pathlib.Path("/private/tmp/claude-501/-Users-pinperepette-Github-blog-articoli/"
                    "79f1d3aa-d083-4480-836e-4018a213f872/scratchpad/esperimento")
ENV = {**os.environ, "PATH": f"{os.path.expanduser('~')}/.elan/bin:" + os.environ["PATH"]}


def sh(cmd, cwd, timeout=600):
    r = subprocess.run(cmd, shell=True, cwd=cwd, env=ENV,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def analizza(run):
    d = BASE / run
    src_path = d / "Ricerca.lean"
    if not src_path.exists():
        return {"run": run, "errore": "Ricerca.lean assente"}
    src = src_path.read_text()
    out = {"run": run, "righe": len([l for l in src.splitlines() if l.strip()])}

    # A. compila?
    rc, log = sh("lake env lean Ricerca.lean", d)
    out["compila"] = ("error:" not in log)
    out["warning_sorry"] = "declaration uses `sorry`" in log
    out["log_compilazione"] = log.strip()[:1500]

    # B/C. sorry e axiom nel sorgente
    out["sorry_nel_sorgente"] = bool(re.search(r'\bsorry\b', src))
    out["axiom_dichiarati"] = re.findall(r'^\s*axiom\s+(\S+)', src, re.M)
    out["native_decide"] = "native_decide" in src

    # nomi dei teoremi e delle def
    out["teoremi"] = re.findall(r'^\s*(?:theorem|lemma)\s+([A-Za-z_][\w\'.]*)', src, re.M)
    out["definizioni"] = re.findall(r'^\s*(?:def|partial def)\s+([A-Za-z_][\w\'.]*)', src, re.M)

    # D. impronta assiomatica: copia il run e appendi i #print axioms
    if out["compila"] and out["teoremi"]:
        w = BASE / f".ax_{run}"
        if w.exists():
            shutil.rmtree(w)
        shutil.copytree(d, w)
        extra = "\n\n" + "\n".join(f"#print axioms {t}" for t in out["teoremi"]) + "\n"
        (w / "Ricerca.lean").write_text(src + extra)
        _, axlog = sh("lake env lean Ricerca.lean", w)
        out["axioms"] = [l.strip() for l in axlog.splitlines()
                         if "depends on axioms" in l or "does not depend" in l]
        shutil.rmtree(w, ignore_errors=True)
    else:
        out["axioms"] = []

    return out


if __name__ == "__main__":
    runs = sys.argv[1:] or ["run1", "run2", "run3", "run4"]
    res = [analizza(r) for r in runs]
    print(json.dumps(res, indent=2, ensure_ascii=False))
