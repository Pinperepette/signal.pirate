#!/usr/bin/env python3
"""
Organizzatore della cartella Download.

Filosofia (vedi articolo "Diecimila File, Zero Agenti"):
  - niente framework, niente colonia di agenti: un loop (qui con 3 fasi nette).
  - all'LLM (DeepSeek) UNA cosa sola: capire COSA e' un file.
  - tutto cio' che e' deterministico (hash, dedup, conteggi, policy delle
    cartelle, collisioni di nomi) lo fa Python, che non si paga a token.
  - prima i conti, poi i token: si fa l'hash e la dedup PRIMA di classificare,
    cosi' i duplicati non costano nemmeno una chiamata.
  - se la classificazione e' incerta -> raccogli piu' contesto e RIPROVA una
    volta; se resta incerta, metti in quarantena invece di indovinare.
  - logga qualsiasi cosa si muova (JSONL). Da quel log si fa --undo.

Fasi:
  1) deterministica: elenca i file in radice, calcola SHA-256, raggruppa i
     duplicati (un "keeper" per hash, gli altri vanno in _Duplicati).
  2) LLM (in parallelo): classifica i soli keeper.
  3) deterministica: applica gli spostamenti, gestisce le collisioni, logga.

Uso:
  python3 organize.py <cartella> [--apply] [--workers N] [--limit N]
  python3 organize.py <cartella> --undo <file-log.jsonl>     # annulla una run

Di default e' DRY-RUN: non sposta niente.
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

KEY_FILE = os.path.expanduser("~/.server/deepseek.txt")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"          # risolve a deepseek-v4-flash: economico, ok cosi'
CONFIDENCE_THRESHOLD = 0.70      # sotto questa soglia: raccogli contesto e riprova

# Vocabolario CHIUSO di categorie -> nome cartella. Tenere la tassonomia ferma
# e' una scelta deterministica: il modello sceglie tra queste, non ne inventa
# di nuove a ogni file (altrimenti due lanci = due tassonomie diverse).
CATEGORIES = {
    "Fatture": "Fatture",
    "Documenti": "Documenti",
    "Foto": "Foto",
    "Screenshot": "Screenshot",
    "Installer": "Installer",
    "Archivi": "Archivi",
    "Codice": "Codice",
    "Audio": "Audio",
    "Video": "Video",
    "Ebook": "Ebook",
    "Modelli3D": "Modelli3D",
    "Altro": "Altro",
}
DUP_DIR = "_Duplicati"           # gestione duplicati: deterministica, niente LLM
QUARANTINE_DIR = "_DaRivedere"   # classificazione incerta: si rivede a mano
SYSTEM_DIRS = set(CATEGORIES.values()) | {DUP_DIR, QUARANTINE_DIR, ".git"}

STATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "organizer-state")


# ----------------------------------------------------------------------------
# Utility deterministiche (Python, non LLM)
# ----------------------------------------------------------------------------

def load_api_key():
    env = os.environ.get("DEEPSEEK_API_KEY")
    if env:
        return env.strip()
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    sys.exit("ERRORE: chiave DeepSeek non trovata (ne' DEEPSEEK_API_KEY ne' %s)" % KEY_FILE)


def sha256_of(path, buf=1024 * 1024):
    """Hash deterministico del contenuto. Questa e' la VERA deduplica:
    due file o sono identici o non lo sono, niente giudizio probabilistico."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def content_preview(path, n_bytes):
    """Anteprima testuale per dare segnale al classificatore. Sui binari
    (foto, dmg, zip) restituisce un marcatore: li' conta il nome, non i byte."""
    try:
        with open(path, "rb") as f:
            raw = f.read(n_bytes)
    except OSError:
        return "[illeggibile]"
    if b"\x00" in raw[:512]:
        return "[binario]"
    text = raw.decode("utf-8", errors="ignore")
    printable = sum(c.isprintable() or c in "\n\r\t" for c in text)
    if not text or printable / max(len(text), 1) < 0.85:
        return "[binario]"
    return text.strip()[:n_bytes]


def sanitize_name(name):
    """Nome pulito e prevedibile. Deterministico: niente fantasia a runtime."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\s\-.]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._")
    return name[:80] or "file"


def unique_destination(folder, base, ext):
    """Collisioni gestite in modo deterministico: NON si sovrascrive mai."""
    candidate = os.path.join(folder, base + ext)
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, "%s_%d%s" % (base, i, ext))
        i += 1
    return candidate


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.0f%s" % (n, unit)
        n /= 1024
    return "%.1fTB" % n


# ----------------------------------------------------------------------------
# L'unica chiamata all'LLM: capire COSA e' il file
# ----------------------------------------------------------------------------

def _api_call(api_key, user):
    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Sei un classificatore di file. Rispondi solo JSON valido."},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
        method="POST",
    )
    # piccola resilienza di rete: ritenta su errori transitori (timeout, 429, 5xx)
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def classify(api_key, filename, ext, size, preview, decisive=False):
    """Una sola responsabilita': data la descrizione del file, dire categoria
    (dal vocabolario chiuso), nome suggerito e confidenza. Niente altro."""
    cats = ", ".join(CATEGORIES.keys())
    extra = ""
    if decisive:
        extra = ("\nQuesto e' il SECONDO tentativo con piu' contesto. Sii deciso. "
                 "Se davvero non e' classificabile usa categoria 'Altro' con confidence bassa.")
    user = (
        "Classifica questo file di una cartella Download.\n"
        f"- nome: {filename}\n- estensione: {ext or '(nessuna)'}\n- dimensione: {human(size)}\n"
        f"- anteprima contenuto: {preview!r}\n\n"
        f"Categorie ammesse (usane ESATTAMENTE una): {cats}.\n"
        "Rispondi SOLO con un JSON: "
        '{"category": "...", "suggested_name": "nome breve descrittivo in italiano '
        'senza estensione, parole separate da spazio", "confidence": numero tra 0 e 1, '
        '"reason": "motivo in una riga"}.' + extra
    )
    data = _api_call(api_key, user)
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    parsed = json.loads(content)
    cat = parsed.get("category", "Altro")
    if cat not in CATEGORIES:
        cat = "Altro"
    conf = parsed.get("confidence", 0.0)
    try:
        conf = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        conf = 0.0
    return {
        "category": cat,
        "suggested_name": str(parsed.get("suggested_name") or "").strip(),
        "confidence": conf,
        "reason": str(parsed.get("reason") or "").strip(),
        "tokens": usage.get("total_tokens", 0),
    }


def classify_with_retry(api_key, path):
    """esegui -> verifica -> se incerto raccogli piu' contesto e riprova.
    Thread-safe: legge solo il file e l'API, non tocca stato condiviso."""
    filename = os.path.basename(path)
    _, ext = os.path.splitext(filename)
    size = os.path.getsize(path)
    res = classify(api_key, filename, ext, size, content_preview(path, 2000))
    attempts, tokens = 1, res["tokens"]
    if res["confidence"] < CONFIDENCE_THRESHOLD:
        res2 = classify(api_key, filename, ext, size, content_preview(path, 8000), decisive=True)
        attempts = 2
        tokens += res2["tokens"]
        if res2["confidence"] >= res["confidence"]:
            res = res2
    res["attempts"] = attempts
    res["tokens"] = tokens
    return res


# ----------------------------------------------------------------------------
# Undo: rigioca il log al contrario
# ----------------------------------------------------------------------------

def journal_commit(message):
    """git come GIORNALE, solo testo: versiona lo stato/log dell'organizzatore,
    NON i 26 GB di Download. Da qui esce la storia: `git log` = cosa e' cambiato
    e quando. Strumento giusto (versioning di testo) per il lavoro giusto."""
    os.makedirs(STATE_ROOT, exist_ok=True)
    if not os.path.isdir(os.path.join(STATE_ROOT, ".git")):
        subprocess.run(["git", "-C", STATE_ROOT, "init", "-q"])
    subprocess.run(["git", "-C", STATE_ROOT, "add", "-A"])
    subprocess.run(["git", "-C", STATE_ROOT, "commit", "-q", "-m", message],
                   capture_output=True, text=True)


def do_undo(target, logpath):
    recs = [json.loads(l) for l in open(logpath)]
    restored = 0
    for r in reversed(recs):
        if r.get("action") in ("sposta", "duplicato") and r.get("dest"):
            dest = os.path.join(target, r["dest"])
            orig = os.path.join(target, r["file"])
            if os.path.exists(dest) and not os.path.exists(orig):
                os.rename(dest, orig)
                restored += 1
    # rimuovi le cartelle di sistema rimaste vuote
    for d in SYSTEM_DIRS:
        p = os.path.join(target, d)
        if os.path.isdir(p) and not os.listdir(p):
            os.rmdir(p)
    print("UNDO: ripristinati %d file in %s" % (restored, target))


# ----------------------------------------------------------------------------
# Loop principale (3 fasi)
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Organizza una cartella Download.")
    ap.add_argument("target", help="cartella da organizzare")
    ap.add_argument("--apply", action="store_true", help="sposta davvero (default: dry-run)")
    ap.add_argument("--workers", type=int, default=8, help="classificazioni in parallelo")
    ap.add_argument("--limit", type=int, default=0, help="processa al massimo N file (0 = tutti)")
    ap.add_argument("--undo", metavar="LOG", help="annulla una run dal suo file di log")
    ap.add_argument("--journal", action="store_true", help="committa in git lo stato/log (giornale testuale)")
    ap.add_argument("--quiet", action="store_true", help="meno output per file")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        sys.exit("ERRORE: %s non e' una cartella" % target)

    if args.undo:
        do_undo(target, args.undo)
        return

    dry = not args.apply

    # --- Raccolta file di radice (niente dotfile, niente sottocartelle) ---
    # La radice E' la coda di lavoro: i download nuovi atterrano qui, le
    # categorie sono sottocartelle che ignoriamo. Questo rende l'organizzatore
    # incrementale per costruzione, senza bisogno di un rilevatore di modifiche.
    files = []
    for fn in sorted(os.listdir(target)):
        p = os.path.join(target, fn)
        if os.path.isfile(p) and not fn.startswith(".") and fn != "MANIFEST.tsv":
            files.append(p)
    if args.limit:
        files = files[:args.limit]

    # Tick a vuoto (es. il demone ogni ora): se in radice non c'e' niente di
    # nuovo, non si apre nemmeno un log e non si spende un solo token.
    if not files:
        print("nessun nuovo file in radice di %s: niente da fare." % target)
        return

    api_key = load_api_key()

    state_dir = os.path.join(STATE_ROOT, sanitize_name(os.path.basename(target)))
    os.makedirs(state_dir, exist_ok=True)
    seen_path = os.path.join(state_dir, "seen_hashes.json")
    seen = json.load(open(seen_path)) if os.path.exists(seen_path) else {}

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(state_dir, "run-%s.jsonl" % ts)
    logf = open(log_path, "w")
    log_lock = threading.Lock()

    def log(rec):
        with log_lock:
            logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            logf.flush()

    print("== Organizzatore Download ==")
    print("cartella : %s" % target)
    print("modalita': %s" % ("DRY-RUN (nessuna modifica)" if dry else "APPLY (sposta davvero)"))
    print("modello  : %s | soglia: %.2f | worker: %d" % (MODEL, CONFIDENCE_THRESHOLD, args.workers))
    print("log      : %s" % log_path)
    print("-" * 64)

    # --- FASE 1: hash + dedup (deterministica, zero token) ---
    print("[fase 1] hash di %d file e deduplica..." % len(files))
    by_hash = {}
    file_hash = {}
    for p in files:
        try:
            h = sha256_of(p)
        except OSError as e:
            log({"file": os.path.basename(p), "action": "errore", "error": "hash: %s" % e})
            continue
        file_hash[p] = h
        by_hash.setdefault(h, []).append(p)

    keepers, dups = [], []
    for p in files:
        h = file_hash.get(p)
        if h is None:
            continue
        if h in seen:                      # duplicato di una run precedente
            dups.append((p, seen[h]))
        elif by_hash[h][0] == p:           # prima occorrenza in questa run
            keepers.append(p)
        else:                              # duplicato interno a questa run
            dups.append((p, None))
    print("[fase 1] %d unici da classificare, %d duplicati gia' individuati" % (len(keepers), len(dups)))

    # --- FASE 2: classificazione in parallelo (LLM) ---
    print("[fase 2] classificazione (%d worker)..." % args.workers)
    results = {}
    done = {"n": 0}

    def work(p):
        try:
            return p, classify_with_retry(api_key, p), None
        except Exception as e:  # noqa: BLE001
            return p, None, str(e)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for p, res, err in ex.map(work, keepers):
            results[p] = (res, err)
            done["n"] += 1
            if done["n"] % 25 == 0 or done["n"] == len(keepers):
                print("  classificati %d/%d" % (done["n"], len(keepers)))

    # --- FASE 3: applica gli spostamenti (deterministica) ---
    print("[fase 3] %s..." % ("simulazione spostamenti" if dry else "spostamento file"))
    stats = {"totali": len(files), "spostati": 0, "duplicati": 0,
             "quarantena": 0, "errori": 0, "token": 0, "per_categoria": {}}

    for p in keepers:
        fn = os.path.basename(p)
        rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"), "file": fn,
               "sha256": file_hash[p]}
        res, err = results.get(p, (None, "nessun risultato"))
        if err:
            rec.update(action="errore", error=err)
            stats["errori"] += 1
            if not args.quiet:
                print("  [ERR ] %-40s -> %s" % (fn[:40], err[:60]))
            log(rec)
            continue
        stats["token"] += res["tokens"]
        rec.update(confidence=res["confidence"], attempts=res["attempts"], reason=res["reason"])

        if res["confidence"] < CONFIDENCE_THRESHOLD:
            category, folder, tag = "DaRivedere", QUARANTINE_DIR, "QUAR"
            stats["quarantena"] += 1
        else:
            category, folder, tag = res["category"], CATEGORIES[res["category"]], "OK  "
            stats["spostati"] += 1
            stats["per_categoria"][category] = stats["per_categoria"].get(category, 0) + 1

        ext = os.path.splitext(fn)[1]
        base = sanitize_name(res["suggested_name"] or os.path.splitext(fn)[0])
        dest_dir = os.path.join(target, folder)
        dest = unique_destination(dest_dir, base, ext)
        rec.update(action="sposta", category=category, suggested_name=res["suggested_name"],
                   dest=os.path.relpath(dest, target))
        if not dry:
            os.makedirs(dest_dir, exist_ok=True)
            os.rename(p, dest)
        seen[file_hash[p]] = os.path.relpath(dest, target)
        if not args.quiet:
            print("  [%s] %-40s -> %s/%s  (conf %.2f, %dt)"
                  % (tag, fn[:40], folder, os.path.basename(dest), res["confidence"], res["attempts"]))
        log(rec)

    # duplicati: spostati in coda, cosi' il "keeper" e' gia' al suo posto
    for p, keeper_rel in dups:
        fn = os.path.basename(p)
        of = keeper_rel or seen.get(file_hash[p])
        ext = os.path.splitext(fn)[1]
        dest_dir = os.path.join(target, DUP_DIR)
        dest = unique_destination(dest_dir, sanitize_name(os.path.splitext(fn)[0]), ext)
        rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"), "file": fn,
               "sha256": file_hash[p], "action": "duplicato", "of": of,
               "dest": os.path.relpath(dest, target)}
        if not dry:
            os.makedirs(dest_dir, exist_ok=True)
            os.rename(p, dest)
        stats["duplicati"] += 1
        if not args.quiet:
            print("  [DUP ] %-40s -> %s/  (copia di %s)" % (fn[:40], DUP_DIR, of))
        log(rec)

    json.dump(seen, open(seen_path, "w"), ensure_ascii=False, indent=2)
    logf.close()

    if args.journal and not dry:
        journal_commit("%s: +%d organizzati, %d duplicati, %d in quarantena"
                       % (os.path.basename(target), stats["spostati"],
                          stats["duplicati"], stats["quarantena"]))

    # --- Statistiche: conteggi deterministici, non chiacchiere del modello ---
    print("-" * 64)
    print("RIEPILOGO  (i conti li fa Python, non l'LLM)")
    print("  file totali  : %d" % stats["totali"])
    print("  spostati     : %d" % stats["spostati"])
    print("  duplicati    : %d" % stats["duplicati"])
    print("  in quarantena: %d" % stats["quarantena"])
    print("  errori       : %d" % stats["errori"])
    classificati = stats["spostati"] + stats["quarantena"]
    print("  token usati  : %d (~%d per file classificato)"
          % (stats["token"], stats["token"] // max(1, classificati)))
    if stats["per_categoria"]:
        print("  per categoria:")
        for cat, n in sorted(stats["per_categoria"].items(), key=lambda x: -x[1]):
            print("    %-12s %d" % (cat, n))
    print("  log/undo     : python3 organize.py %s --undo %s" % (target, log_path))
    if dry:
        print("\n  (DRY-RUN: non e' stato spostato niente. Rilancia con --apply per applicare.)")


if __name__ == "__main__":
    main()
