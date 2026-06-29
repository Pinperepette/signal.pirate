from cart import Carrello

def test_sconto_soglia_100():
    c = Carrello()
    c.aggiungi("tastiera", 60.0)
    c.aggiungi("mouse", 40.0)        # subtotale 100 -> sconto 10%
    assert c.totale() == 90.0        # atteso 90, non 110
