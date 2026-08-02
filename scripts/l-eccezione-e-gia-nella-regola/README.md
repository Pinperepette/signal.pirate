# Dati e script: "L'eccezione è già nella regola"

Articolo: [`articoli/l-eccezione-e-gia-nella-regola.html`](../../articoli/l-eccezione-e-gia-nella-regola.html)

Otto grafici, quarantanove valori, una riga per valore. Ogni numero che compare
nell'articolo sta in `fonti.csv` con la fonte, l'URL e il livello di affidabilità,
così chiunque può rifare i conti o smontarli.

## Come si rigenera

```
python3 build_data.py                    # valida e scrive grafici.json
python3 build_data.py --check            # valida soltanto, non scrive niente
python3 build_data.py --inject ../../articoli/l-eccezione-e-gia-nella-regola.html
```

Solo libreria standard, nessuna rete, nessun timestamp nell'output: rilanciare lo
script due volte di fila produce byte identici. Se `git diff` sporca qualcosa,
sono cambiati i dati e non l'orologio.

L'iniezione sostituisce il blocco fra i marcatori `/* DATI:INIZIO */` e
`/* DATI:FINE */` dentro la pagina. Lo stesso comando funziona anche sulla copia
di laboratorio dell'articolo, che ha gli stessi marcatori.

## Livelli di affidabilità

| livello | significato | quanti |
|---|---|---|
| A | fonte primaria o istituzionale verificata | 33 |
| B | fonte secondaria affidabile | 5 |
| C | fonte advocacy o giornalistica, da ricontrollare prima di pubblicare | 11 |

Gli undici valori **[C]** stanno tutti nei grafici 5 e 6 (Chat Control: cronologia
2026 e tassi di falsi positivi). La fonte principale è Patrick Breyer, ex
europarlamentare e parte in causa. Il quadro d'insieme è coerente con la stampa
specializzata, i singoli passaggi vanno confermati su verbali di Consiglio e
Parlamento. Finché restano **[C]**, l'articolo lo dichiara in didascalia e la
pagina li marca in rosso sotto il grafico.

## I grafici

| id | tipo | cosa mostra | note sui dati |
|---|---|---|---|
| g1 | dumbbell | peso di autonomia e privacy prima e dopo la dichiarazione OMS | i due soli attributi riportati nel dossier, non tutti e cinque |
| g2 | forbice | consenso Pew che scende contro leggi antiterrorismo che salgono | la serie delle leggi ha **due soli punti documentati**, 2001 e 2012: il tratto fra i due è interpolazione dichiarata, e la linea piatta dopo il 2012 segna la fine del conteggio HRW, non la fine delle leggi |
| g3 | filiera | ogni misura con la giustificazione con cui è stata presentata | date al mese |
| g4 | stack | gli atti biometrici europei: ogni barra parte e non finisce | l'assenza di scadenza è il punto, non un'assunzione grafica |
| g5 | gradino | base giuridica della scansione delle comunicazioni: 1 o 0 | tutti i punti sono **[C]** |
| g6 | barre | quota di segnalazioni automatiche che non regge | tutti i punti sono **[C]** |
| g7 | discesa | consenso britannico che cala man mano che la misura si fa concreta | stessa rilevazione, tre formulazioni |
| g8 | confronto | 2004 contro 2025 su documento sempre addosso e timori per le libertà civili | serve a non fare cherry picking sul 57 per cento |

Nell'articolo g8 compare come "grafico 7" e g7 come "grafico 8": l'ordine di lettura
è quello, gli identificativi dei dati sono rimasti quelli di partenza.

`x` accetta `YYYY`, `YYYY-MM` o `YYYY-MM-DD`: la precisione dichiarata è quella che
la fonte regge davvero, per questo alcuni eventi hanno solo il mese. `y` resta vuoto
per le righe che sono eventi e non misure. Lo script rifiuta il file se manca una
fonte, se manca un URL, se l'affidabilità non è A, B o C, o se un grafico che ha
bisogno di valori numerici ne trova uno vuoto.

## Gli altri file

- `fonti.csv` — i 49 valori, uno per riga, con fonte, URL, affidabilità e nota
- `grafici.json` — l'output dello script, cioè quello che finisce nella pagina
- `dossier-fonti.md` — il dossier completo da cui è stato estratto il CSV: dieci
  sezioni, ogni fatto marcato [A], [B] o [C], con anche il materiale che
  nell'articolo non è entrato

## Cosa manca

Una serie annuale delle leggi antiterrorismo nel mondo. Con quella il grafico 2
smetterebbe di avere un tratto interpolato, ed è l'unico miglioramento davvero
sostanziale rimasto.
