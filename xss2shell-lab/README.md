# XSS2Shell Lab

Lab riproducibile per dimostrare la catena XSS → Application Password → RCE su WordPress.

> ⚠️ Questo repository è solo per scopo didattico e per test in ambiente controllato. Non usarlo su sistemi senza autorizzazione.

## Cosa replica

Il lab riproduce **CVE-2026-64638**, una vulnerabilità XSS pre-autenticazione nel core di WordPress (CVSS 8.9) corretta il 6 agosto 2026 con la versione 7.0.3. Il bug da solo non equivale a RCE: per arrivare all'esecuzione di codice serve che un amministratore già autenticato interagisca con una pagina controllata dall'attaccante.

La catena completa dimostrata nel lab è:

1. **XSS su `wp-login.php`**: il campo `log` viene reflectato nella pagina di errore senza un escaping sufficiente.
2. **DOM clobbering di `ajaxurl`**: il payload XSS sovrascrive `window.ajaxurl` con un elemento HTML, reindirizzando le richieste interne verso un endpoint REST controllato dall'attaccante.
3. **Application Password via REST**: usando un nonce REST valido, il payload crea un'Application Password per l'utente loggato.
4. **Exfiltration**: la password viene inviata al server attaccante.
5. **RCE**: il server attaccante usa l'Application Password per creare un utente amministratore backdoor, caricare e attivare un plugin malevolo, e verificare l'esecuzione di codice.

## Struttura

| File | Scopo |
|------|-------|
| `docker-compose.yml` | Container WordPress 6.7.0 + MariaDB |
| `mu-plugins/enable-app-passwords.php` | Abilita le Application Password nel container |
| `mu-plugins/expose-rest-nonce.php` | Espone un nonce REST via JSONP (simula il leak necessario al PoC) |
| `exploit.php` | Pagina di exploit autenticata in `/wp-admin/xss2shell-exploit.php`, usa `wpApiSettings.nonce` |
| `exploit.html` | Pagina di exploit esterna, apre popup su WordPress e non richiede autenticazione sul sito attaccante |
| `exploit-server.py` | Server Flask che serve `exploit.html` e riceve la password esfiltrata |
| `run-poc.py` | Automazione Playwright: avvia il server, logga l'admin, clicca l'exploit e verifica il marker RCE |
| `payload/pwnplugin.zip` | Plugin malevolo di esempio |

## Requisiti

- Docker + Docker Compose
- Python 3.9+
- Playwright per Python

Installa le dipendenze:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests flask playwright
playwright install chromium
```

## Avvio rapido

```bash
# 1. Avvia WordPress
docker compose up -d

# 2. Attiva l'ambiente Python
source .venv/bin/activate

# 3. Esegui il PoC end-to-end
python run-poc.py
```

Se tutto funziona vedrai:

- `Application Password creata: ...`
- `"status": "pwned"`
- `"marker_ok": true`

## Credenziali di default

- WordPress admin: `admin` / `adminpass`
- Database root: `rootpass`

## Arresto

```bash
docker compose down -v
```

## Note tecniche

- Il container usa WordPress 6.7.0, una versione precedente alla 7.0.3 in cui WordPress ha corretto CVE-2026-64638.
- `mu-plugins/expose-rest-nonce.php` è un helper di laboratorio: nella realtà un XSS pre-auth può ottenere un nonce REST in altri modi (es. da script già presenti nella pagina o da endpoint non protetti).
- Il payload sfrutta tag HTML con spazio iniziale (`< area`, `< div`, `< button`) per bypassare filtri di sanificazione che riconoscono solo tag canonici.

## Riferimenti

- Articolo sul blog: `../articoli/xss2shell-wordpress-core-rce.html`
