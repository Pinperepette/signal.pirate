"""Carrello e calcolo del totale con sconti a soglia (toy project per l'articolo)."""

class Carrello:
    def __init__(self):
        self.righe = []

    def aggiungi(self, nome, prezzo, quantita=1):
        self.righe.append({"nome": nome, "prezzo": prezzo, "quantita": quantita})

    def subtotale(self):
        return sum(r["prezzo"] * r["quantita"] for r in self.righe)

    def sconto_percentuale(self):
        s = self.subtotale()
        if s >= 100:
            return 0.10
        if s >= 50:
            return 0.05
        return 0.0

    def totale(self):
        s = self.subtotale()
        # BUG: lo sconto viene sommato invece che sottratto
        return s + (s * self.sconto_percentuale())
