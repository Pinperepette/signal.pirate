"""Seed del corpus RAG: glossario di cucina (per la query 1, knowledge).

Documenti brevi su tecniche e termini base. Quando arriva una domanda
"cos'e' X" la query 1 NON usa questo: la definizione del soffritto sta
gia' nel system prompt CAG (vedi context.py). Il corpus RAG serve per
domande che il CAG non copre, ad esempio "tecnica della mantecatura".

Tenuto piccolo apposta. Il punto della demo non e' la qualita' del
RAG, e' mostrare quando il RAG si attiva e quando viene saltato.
"""
from __future__ import annotations

from memory import Doc, VectorMemory


_DOCS: list[Doc] = [
    Doc(
        id="glossario:soffritto",
        text=(
            "Il soffritto e' la base di moltissime preparazioni italiane. "
            "Si ottiene rosolando in olio o burro un trito di cipolla, "
            "carota e sedano (soffritto classico) a fuoco basso fino a "
            "imbiondimento, senza far prendere colore eccessivo."
        ),
        meta={"tipo": "tecnica"},
    ),
    Doc(
        id="glossario:mantecatura",
        text=(
            "La mantecatura e' la fase finale in cui si lega un risotto "
            "o una pasta con grasso (burro, olio, formaggio) e amido di "
            "cottura. Si fa lontano dal fuoco per evitare che le proteine "
            "del formaggio impazziscano."
        ),
        meta={"tipo": "tecnica"},
    ),
    Doc(
        id="glossario:cottura-risottata",
        text=(
            "La cottura risottata applica al primo piatto la tecnica del "
            "risotto: il liquido viene aggiunto a poco a poco, e l'amido "
            "rilasciato dalla pasta o dal cereale crea una crema naturale. "
            "Tipica di pasta e patate alla napoletana."
        ),
        meta={"tipo": "tecnica"},
    ),
    Doc(
        id="glossario:san-marzano",
        text=(
            "Il pomodoro San Marzano DOP e' un pomodoro lungo coltivato "
            "nell'agro nocerino-sarnese. E' la varieta' tipica della pizza "
            "napoletana, schiacciato a mano e mai frullato."
        ),
        meta={"tipo": "ingrediente"},
    ),
    Doc(
        id="glossario:guanciale",
        text=(
            "Il guanciale si ricava dalla guancia del maiale, stagionato "
            "con sale, pepe ed erbe. E' piu' grasso e saporito della "
            "pancetta, ed e' l'ingrediente corretto per Carbonara, "
            "Amatriciana e Gricia (le Romane classiche)."
        ),
        meta={"tipo": "ingrediente"},
    ),
]


def seed(ltm: VectorMemory) -> int:
    for d in _DOCS:
        ltm.upsert(d)
    return len(_DOCS)
