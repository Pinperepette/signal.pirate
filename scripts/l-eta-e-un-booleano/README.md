# L'Eta' E' Un Booleano — Lab scripts

PoC scripts per le vulnerabilita' descritte in [`l-eta-e-un-booleano.html`](../../articoli/l-eta-e-un-booleano.html).

**Target:** `eu-digital-identity-wallet/av-app-android-wallet-ui`, build `devDebug`.
**Ambiente:** emulatore Android API 30 x86_64, test issuer `test.issuer.dev.ageverification.dev`.
**Nessuna produzione toccata, nessun dato utente reale coinvolto.**

## Prerequisiti

- Emulatore Android API 30+ avviato
- App AV installata (`com.scytales.av.dev`) e avviata almeno una volta
- `adb` nel PATH (`$ANDROID_HOME/platform-tools/adb`)
- `sqlite3` per gli script di estrazione DB
- `python3` per `04-decode-shuffle.py`
- `mitmproxy` per `05-mitm-setup.sh` (opzionale)

## Script

| File | VULN | Cosa fa |
|------|------|---------|
| `00-common.sh` | — | Funzioni condivise (adb, read_prefs, write_prefs, restart_app) |
| `01-pin-bypass.sh` | VULN-01 | Rimuove PinEnc/PinIv, dimostra che le credenziali restano |
| `02-ratelimit-bypass.sh` | VULN-02 | Forza lockout, resetta, dimostra che i tentativi tornano infiniti |
| `03-biometric-bypass.sh` | VULN-03 | Flippa UseBiometricsAuth da true a false |
| `04-decode-shuffle.py` | VULN-04 | Inverte il Fisher-Yates con seed `[1,3,5,7,9,2,4,6,8]` |
| `05-mitm-setup.sh` | VULN-06 | Verifica assenza pinning, documenta setup mitmproxy |
| `06-extract-credentials.sh` | VULN-07 | Dump del DB SQLite delle credenziali |
| `07-full-demo.sh` | all | Catena tutti i test in sequenza |
| `08-credential-replay-poc.sh` | VULN-08 | Estrae CBOR + keys, analizza fattibilita' replay |
| `av-security-test.sh` | all | Versione standalone (self-contained, no 00-common) |

## Uso

```bash
# Test singolo
./01-pin-bypass.sh

# Demo completa
./07-full-demo.sh
```

Ogni script fa **backup** delle SharedPreferences prima di modificarle e **ripristina** lo stato originale alla fine (dove possibile).

## Security Report

[`SECURITY_REPORT.md`](./SECURITY_REPORT.md) — assessment completo, 8 VULN con file/riga del sorgente, impact, proof, raccomandazioni.

## Nota etica

Paul Moore ([@Paul_Reviews](https://twitter.com/Paul_Reviews)) ha gia' pubblicamente dimostrato sia il PIN bypass sia una Chrome extension funzionante che bypassa la verifica end-to-end su infrastruttura reale. Gli script in questo repository automatizzano su emulatore verifiche che sono ormai di pubblico dominio; non aggiungono capability di attacco che non esistessero gia'. La pubblicazione serve a permettere la replica indipendente del lavoro e a rendere accountable l'intero stack di verifica dell'eta' europeo.

Il team EUDI Wallet / Scytales / EU Commission puo' contattarmi per coordinamento su disclosure o chiarimenti.
