"""Seed del Knowledge Graph: sei ricette in markdown.

Ogni ricetta e' una nota nel KG, salvata via RedisArray (mock del tipo
Array di antirez). ARGREP fa il retrieval con regex sul rendered text.

Tre romane (Carbonara, Amatriciana, Cacio e Pepe), tre napoletane
(Pizza Margherita, Pasta e Patate, Genovese). La query "pattern delle
ricette napoletane" filtra via regex `stile:.*napolet`.
"""
from __future__ import annotations

import time

from memory import KGNote, KnowledgeMemory


_RECIPES: list[KGNote] = [
    KGNote(
        title="Carbonara",
        tags=["pasta", "romana", "classico"],
        content="""stile: romana
servings: 4
tempo: 20min

## Ingredienti
- 320g spaghetti
- 150g guanciale
- 4 tuorli
- 1 uovo intero
- 80g pecorino romano
- pepe nero
- sale grosso

## Procedimento
1. Tagliare il guanciale a listarelle e rosolarlo a fuoco basso senza olio.
2. Cuocere gli spaghetti in acqua salata.
3. Sbattere tuorli e uovo con il pecorino e abbondante pepe.
4. Scolare la pasta al dente, mantecare con il guanciale e poi con la
   crema d'uovo lontano dal fuoco.

## Tecniche
- Mantecatura a fuoco spento (rischio di strapazzare le uova).
- Uso del grasso del guanciale come legante.

note: niente panna, niente aglio, niente cipolla.
""",
    ),
    KGNote(
        title="Amatriciana",
        tags=["pasta", "romana", "pomodoro"],
        content="""stile: romana
servings: 4
tempo: 25min

## Ingredienti
- 320g bucatini
- 150g guanciale
- 400g pomodori pelati
- 80g pecorino romano
- 1 peperoncino
- vino bianco
- pepe nero
- sale

## Procedimento
1. Rosolare il guanciale, sfumare con vino bianco.
2. Aggiungere pelati e peperoncino, cuocere 10 min.
3. Cuocere i bucatini al dente, mantecare con il sugo.
4. Pecorino e pepe a crudo.

## Tecniche
- Sfumatura con vino bianco prima del pomodoro.
- Pomodori pelati interi schiacciati con la forchetta in padella.

note: senza cipolla nella versione tradizionale.
""",
    ),
    KGNote(
        title="Cacio e Pepe",
        tags=["pasta", "romana", "essenziale"],
        content="""stile: romana
servings: 4
tempo: 15min

## Ingredienti
- 320g tonnarelli
- 200g pecorino romano
- pepe nero in grani
- sale grosso

## Procedimento
1. Tostare il pepe in padella, aggiungere acqua di cottura.
2. Cuocere i tonnarelli molto al dente in poca acqua (acqua piu' amidosa).
3. Mantecare con il pecorino grattugiato e l'acqua di cottura, fuori dal fuoco.

## Tecniche
- Acqua di cottura ridotta = piu' amido = crema piu' stabile.
- Mantecatura fuori dal fuoco per evitare che il pecorino impazzisca.

note: tre ingredienti, ma e' la piu' difficile da fare bene.
""",
    ),
    KGNote(
        title="Pizza Margherita",
        tags=["pizza", "napoletana", "pomodoro", "mozzarella"],
        content="""stile: napoletana
servings: 4
tempo: 90min

## Ingredienti
- 500g farina 00
- 320ml acqua
- 10g sale
- 2g lievito di birra fresco
- 400g pomodoro san marzano
- 250g fior di latte
- basilico fresco
- olio extravergine d'oliva
- sale

## Procedimento
1. Impastare farina, acqua, sale, lievito. Lievitazione lunga 24-48h.
2. Stagliare in 4 panetti da circa 200g, far rilievitare.
3. Stendere a mano lasciando il cornicione.
4. Condire con pomodoro san marzano schiacciato, fior di latte, basilico, olio.
5. Cottura in forno molto caldo (>400 gradi) per 90 secondi.

## Tecniche
- Lievitazione lunga a temperatura controllata.
- Stesura solo manuale, mai col matterello (uccide il cornicione).
- San Marzano schiacciato a mano, mai frullato.

note: pomodoro e mozzarella separati, mai mescolati prima.
""",
    ),
    KGNote(
        title="Pasta e Patate",
        tags=["pasta", "napoletana", "patate", "tradizionale"],
        content="""stile: napoletana
variante: alla napoletana
servings: 4
tempo: 50min

## Ingredienti
- 320g pasta mista
- 500g patate
- 100g pancetta
- 1 cipolla
- 1 carota
- 1 costa di sedano
- 50g parmigiano
- 50g provolone piccante
- olio extravergine d'oliva
- pepe nero
- sale

## Procedimento
1. Soffritto di cipolla, carota, sedano e pancetta in olio EVO.
2. Aggiungere le patate a tocchetti, coprire con poca acqua, cuocere 20 min.
3. Aggiungere la pasta direttamente nella pentola con poca acqua per volta
   (cottura risottata).
4. A fine cottura mantecare con parmigiano e provolone a tocchetti.

## Tecniche
- Cottura risottata della pasta nelle patate (no acqua bollente separata).
- Uso del soffritto napoletano (cipolla, carota, sedano).
- Provolone aggiunto a fine per una crosticina filante.

note: deve essere "azzeccata" (collante), non brodosa.
""",
    ),
    KGNote(
        title="Genovese",
        tags=["pasta", "napoletana", "carne", "cipolla"],
        content="""stile: napoletana
servings: 4
tempo: 4h

## Ingredienti
- 400g ziti
- 800g cipolle ramate
- 600g girello di vitello
- 1 carota
- 1 costa di sedano
- 100g pancetta
- vino bianco
- olio extravergine d'oliva
- 80g parmigiano
- pepe nero
- sale

## Procedimento
1. Soffritto napoletano (cipolla, carota, sedano) con pancetta.
2. Rosolare la carne intera, sfumare con vino bianco.
3. Aggiungere altre cipolle a velo, coprire e cuocere 3-4 ore a fuoco basso.
4. Le cipolle si sciolgono e diventano un sugo cremoso color caramello.
5. Cuocere gli ziti spezzati a mano nel sugo, mantecare con parmigiano.

## Tecniche
- Cottura lunghissima a fuoco basso (le cipolle si caramellano da sole).
- Niente pomodoro: il colore viene solo dalle cipolle e dal vino.
- Ziti spezzati a mano per tradizione.

note: servono sei ore tra preparazione e cottura. La cipolla e' il vero
ingrediente, la carne insaporisce.
""",
    ),
]


def seed(kg: KnowledgeMemory) -> int:
    for note in _RECIPES:
        kg.upsert(note)
    return len(_RECIPES)
