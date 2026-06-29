# Sei lo 0,1%

Codice dell'articolo. Misura quanto del contesto di un agente di coding sei
davvero **tu**, e quanto invece e' roba che la harness mette dentro senza che
tu la veda.

## Cosa c'e'

| File | Cosa fa |
|---|---|
| `scenari.py` | I due scenari neutri (task corto / sessione lunga), conteggio token con tiktoken. Stampa la scomposizione. |
| `grafico.py` | Genera il grafico `tu_sei_lo_zero_virgola_uno.png` (legge `scenari.py`). |
| `analizza.py` | Versione minima a uno scenario, piu' commentata. |
| `persistenza.py` | La seconda dimensione: quante volte ogni token viene riletto (read amplification). Tabella "vita di un token" + numero reale (55x su 99 turni). |
| `analizza-la-tua-sessione.py` | **Lancialo sul TUO transcript.** Dice la stessa scomposizione sulla tua sessione reale. Privacy-safe: conta e basta, non stampa mai il contenuto. |
| `cart.py`, `test_cart.py` | Il toy project con il bug usato come esempio neutro. |

## Come si usa

```bash
pip install tiktoken matplotlib

# i due scenari di esempio
python scenari.py

# il grafico
python grafico.py

# sulla tua sessione (prende la piu' recente se ometti il path)
python analizza-la-tua-sessione.py ~/.claude/projects/<progetto>/<id>.jsonl
```

## Metodo, in breve

- Il **costo fisso della harness** (system prompt + definizioni dei tool +
  CLAUDE.md + hook + skill) e' un numero reale, misurato dai campi `usage`
  dell'API: nel setup di esempio sono 19.694 token. Dipende dal tuo setup: una
  installazione spoglia ne ha meno, una piena di hook e MCP molto di piu'.
- Tutto il resto e' contato con `tiktoken` (encoding `cl100k_base`). E' il
  tokenizer di OpenAI, non quello di Anthropic: i valori assoluti sono una
  stima entro circa il 10-15%, le proporzioni reggono.
- Nello script sul transcript reale il **TOTALE** e' il numero vero dell'API
  (`input + cache_read + cache_creation` al turno piu' pieno); la voce
  "harness" e' il resto, cioe' tutto cio' che non e' un messaggio visibile.
