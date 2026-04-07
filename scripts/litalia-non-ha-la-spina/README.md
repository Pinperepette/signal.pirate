# L'Italia Non Ha La Spina

Script di calcolo per l'articolo: quanto costerebbe elettrificare
l'intero parco auto italiano (40.3 milioni di veicoli)?

## Script

| Script | Cosa calcola | Output |
|--------|-------------|--------|
| `01_fabbisogno.py` | Energia (TWh) vs Potenza (GW), profilo di carico | 01-03 |
| `02_cabina.py` | Vincolo cabina MT/BT, saturazione, heatmap | 04-06 |
| `03_code.py` | Erlang-C per colonnine, dimensionamento rete | 07-09 |
| `04_costi.py` | Breakdown costi, confronto carburanti, payback | 10-12 |

## Esecuzione

```bash
python3 01_fabbisogno.py
python3 02_cabina.py
python3 03_code.py
python3 04_costi.py
```

Requisiti: `numpy`, `matplotlib`, `scipy`

## Risultati chiave

| Metrica | Valore |
|---------|--------|
| Energia aggiuntiva | 74.2 TWh/anno (+24%) |
| Picco potenza EV | +27.6 GW (totale 84.6 GW, +47%) |
| Auto max per cabina 400 kVA | 50 (su 70 utenze) |
| Punti ricarica necessari | ~200.000 (oggi: 73.000) |
| Investimento totale | ~146 mld EUR |
| Payback vs carburanti | 2.3-3.0 anni |

## Fonti

### Parco auto e mobilita
- ACI, Annuario Statistico 2025: 40.3M autovetture, 701/1000 abitanti
  https://aci.gov.it/comunicati-stampa/annuario-statistico-2025-tutti-i-numeri-delle-auto-in-italia/
- ISTAT, Percorrenze veicoli stradali 2025: 10.231 km/anno media
  https://www.istat.it/wp-content/uploads/2025/06/Le-percorrenze-dei-veicoli-stradali-circolanti.pdf

### Energia e rete
- Terna 2024: fabbisogno 312.2 TWh, picco 57.5 GW
  https://www.terna.it/it/media/comunicati-stampa/dettaglio/consumi-elettrici-2024
- e-distribuzione 2024: 445.144 cabine secondarie, ~70 utenze/cabina
  https://www.e-distribuzione.it/Azienda/I-nostri-numeri.html
  https://www.e-distribuzione.it/archivio-news/2024/05/come-funziona-la-rete-di-distribuzione--le-cabine-secondarie.html
- ABB: taglie trasformatori 100/250/400/630 kVA
  https://library.e.abb.com/public/5d00023092cb45469e87fc614efc78b8/Gu_Cabine_MT-BT_it_1VCP000591_1511.pdf

### Veicoli elettrici
- ENGIE/Sorgenia: consumo medio EV ~18 kWh/100km
  https://www.engie.it/casa/magazine/consumo-auto-elettrica/
- MOTUS-E 2025: 73.047 punti di ricarica pubblici
  https://www.motus-e.org/news-associative/auto-elettriche-litalia-supera-la-soglia-dei-70-000-punti-di-ricarica-lappello-del-settore-senza-regole-chiare-e-collaborazione-la-crescita-rischia-di-fermarsi/
- Ingenio 2025: wallbox 700-1300 EUR
  https://www.ingenio-web.it/articoli/guida-2025-alle-wallbox-che-cosa-sono-le-caratteristiche-quali-scegliere/

### Costi e economia
- Energy & Strategy, Politecnico di Milano 2024: LCOE Italia
  https://www.rinnovabili.it/energia/fotovoltaico/lcoe-rinnovabili-costo-livellato-energia/
- Phase S.r.l.: costo cabine MT/BT 40-120k EUR
  https://www.phasesrl.com/quanto-costa-una-cabina-elettrica/
- Il Sole 24 Ore 2024: spesa carburanti 69.8 mld EUR
  https://en.ilsole24ore.com/art/benzina-e-gasolio-autotrazione-2024-spesi-italia-quasi-70-miliardi-AGM6LqmD
- I-Com 2024: fattura energetica 48.5 mld EUR
  https://www.i-com.it/2025/07/04/fattura-energetica-italiana-spesa-in-calo-nel-2024-grazie-a-minori-importazioni-ed-euro-piu-forte/
- ARERA: prezzo elettricita, tariffe
  https://web.archive.org/web/2024/https://www.arera.it/comunicati-stampa/dettaglio/elettricita-bollette-in-calo-del-198-nel-secondo-trimestre-2024
