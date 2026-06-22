# Organizzatore Download — diecimila file, zero agenti

Implementazione di accompagnamento all'articolo *"Diecimila File, Zero Agenti"*.
Nessun framework, nessuna colonia di agenti: **un loop**.

- All'LLM (DeepSeek, modello `deepseek-chat` → `deepseek-v4-flash`) **una sola cosa**:
  capire *cosa* è un file (categoria + nome suggerito + confidenza).
- Tutto il resto è **deterministico in Python**: hash SHA-256 per la deduplica,
  conteggi e statistiche, policy delle cartelle (vocabolario chiuso), collisioni
  di nomi (non si sovrascrive mai).
- **Retry su incertezza**: se la confidenza è sotto soglia, raccoglie più contesto
  e riprova *una* volta; se resta incerta → quarantena (`_DaRivedere`), non indovina.
- **Log JSONL** di ogni decisione (prompt esito, confidenza, token, azione).
- **git come audit log / undo**: snapshot prima e dopo, riordino tracciato come
  rename, `git reset --hard <baseline>` riporta tutto com'era.

## File

- `organize.py` — il sistema (solo stdlib + `urllib` per l'API; zero `pip install`).
- `make_sandbox.py` — genera una cartella Download finta ma realistica per provare.

## Uso

```bash
# 1. chiave DeepSeek: da ~/.server/deepseek.txt oppure export DEEPSEEK_API_KEY=...

# 2. sandbox di prova
python3 make_sandbox.py                 # crea ./sandbox-downloads

# 3. dry-run: non sposta niente, scrive solo il piano + log
python3 organize.py sandbox-downloads

# 4. applica davvero, con tracciamento git nella cartella stessa
git -C sandbox-downloads init -q && git -C sandbox-downloads add -A \
  && git -C sandbox-downloads commit -qm baseline
python3 organize.py sandbox-downloads --apply --git --git-init

# vedere cosa è cambiato / annullare
git -C sandbox-downloads diff --stat -M HEAD~1 HEAD
git -C sandbox-downloads reset --hard HEAD~1     # undo completo
```

### Sulla cartella vera (~/Downloads, grande)

Non fare `git init` su decine di GB di binari. Usa il **dry-run** per vedere il
piano senza muovere niente:

```bash
python3 organize.py ~/Downloads            # dry-run, solo log + piano
python3 organize.py ~/Downloads --limit 50 # prova su un sottoinsieme
```

Lo stato (hash già visti, log per run) sta in `./organizer-state/<cartella>/`.

## Costo

Una chiamata a un modello economico per file (~250–300 token), tutto il resto è
codice che non si paga a token. È il punto dell'articolo: il benchmark che conta
non è "funziona", è *quanto costa* farlo funzionare.
