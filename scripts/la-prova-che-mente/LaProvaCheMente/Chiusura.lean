/-
  COME SI CHIUDE IL BUCO.

  Le sezioni precedenti mostrano quattro modi in cui un ✓ verde non vale
  niente, e `#print axioms` ne becca solo due. Qui costruisco i controlli
  che beccano gli altri, e li verifico.

  Quattro controlli:
    1. TESTIMONE      — le ipotesi hanno almeno un modello non degenere?
    2. MUTAZIONE      — la specifica rifiuta un'implementazione rotta?
    3. IMPLEMENTAZIONE IDIOTA — la specifica e' soddisfatta da una funzione che non fa niente?
    4. DETERMINATEZZA — due funzioni che soddisfano la specifica fanno la stessa cosa?

  I primi tre sono meccanici e chiudono tutte le truffe.
  Il quarto e' quello che rompe l'esperimento del rimborso, e qui
  lo si vede fallire, poi lo si vede chiudersi.
-/
import LaProvaCheMente.Onesta

namespace LPCM

/- ================================================================== -/
/-  PARTE A — i tre controlli meccanici, sulla ricerca binaria         -/
/- ================================================================== -/

/-! ### Controllo 1 — il testimone

Regola: per ogni teorema con ipotesi, devi esibire un caso concreto che
le soddisfa. Se non riesci, il teorema potrebbe non parlare di niente. -/

/-- La specifica ONESTA passa: ecco un array che soddisfa le sue ipotesi,
    e non e' degenere (ha piu' di un elemento). -/
theorem testimone_onesta : Sorted #[1, 3] ∧ 2 ≤ (#[1, 3] : Array Int).size := by
  refine ⟨?_, by decide⟩
  intro i j hij hj
  have hj2 : j < 2 := hj
  have hij2 : i = 0 ∧ j = 1 := by omega
  obtain ⟨hi, hjj⟩ := hij2
  subst hi; subst hjj; decide

/-- **Truffa 2 bocciata.** Il testimone non esiste, e si dimostra:
    nessun array al mondo soddisfa quelle ipotesi. -/
theorem testimone_truffa2 :
    ¬ ∃ a : Array Int, Sorted a ∧ StrictDecr a ∧ 2 ≤ a.size := by
  rintro ⟨a, hs, hd, hsz⟩
  have h1 : a[0]! ≤ a[1]! := hs 0 1 (by omega) (by omega)
  have h2 : a[1]! < a[0]! := hd 0 1 (by omega) (by omega)
  omega

/-- **Truffa 3 bocciata.** Il testimone esiste ma e' degenere: le ipotesi
    obbligano l'array a essere vuoto. Il teorema non parla mai di un caso vero. -/
theorem testimone_truffa3 (a : Array Int) (hwf : ∀ i, i < a.size → i < 0) :
    a.size = 0 := by
  match h : a.size with
  | 0 => rfl
  | n + 1 => have := hwf 0 (by omega); omega

/-! ### Controllo 2 — la mutazione

Regola: rompi l'implementazione apposta e chiedi alla specifica di
rifiutarla. Se la accetta, la specifica e' troppo debole.
E' il mutation testing di Uncle Bob, spostato di un livello: non muti
il codice per testare i test, muti il codice per testare la SPECIFICA. -/

/-- La specifica onesta **rifiuta** il codice rotto. Controllo superato. -/
theorem mutazione_onesta : ¬ FullSpec bsearchBuggy #[1, 3] 1 := by
  rintro ⟨-, hnone⟩
  exact hnone (by simp [bsearchBuggy, bsearchBuggy.go.eq_def]) ⟨0, by decide, by decide⟩

/-- La specifica indebolita (truffa 4) **accetta** lo stesso codice rotto.
    Controllo fallito: quella specifica non stava misurando niente. -/
theorem mutazione_truffa4 :
    ∀ i, bsearchBuggy #[1, 3] 1 = some i → i < (#[1,3] : Array Int).size ∧ (#[1,3] : Array Int)[i]! = 1 :=
  bsearchBuggy_sound #[1, 3] 1

/-! ### Controllo 3 — l'implementazione idiota

Regola: prova a dimostrare la tua specifica per una funzione che non fa
niente. Se ci riesci, la specifica non stava misurando il tuo codice. -/

/-- La specifica onesta **rifiuta** la funzione che non fa niente. Superato. -/
theorem idiota_onesta : ¬ FullSpec bsearchNever #[1, 3] 1 := by
  rintro ⟨-, hnone⟩
  exact hnone rfl ⟨0, by decide, by decide⟩

/- La specifica indebolita la accetta: e' `bsearchNever_sound`, gia'
   dimostrato in Truffe.lean. Controllo fallito. -/

/- ================================================================== -/
/-  PARTE B — il controllo 4, sul rimborso                             -/
/- ================================================================== -/

/-!
Modello minimo del problema del rimborso, ridotto all'essenziale:
il totale dell'ordine e quanto se ne rende. Coupon fuori, perche' le
due divergenze da 4,99 € misurate nell'esperimento avevano coupon = 0.
-/

namespace Rimborso

-- spedizione 4,99 € ; soglia spedizione gratuita 50,00 €
-- (letterali inline: `omega` deve poterli vedere)

/-- Quanto ha pagato il cliente: merce piu' spedizione, gratis sopra soglia. -/
def pagato (tot : Int) : Int := if tot ≥ 5000 then tot else tot + 499

/-! Le proprieta' che i quattro agenti hanno dimostrato davvero. -/

def NonNeg (f : Int → Int → Int) : Prop :=
  ∀ tot resi, 0 < tot → 0 ≤ resi → resi ≤ tot → 0 ≤ f tot resi

def LePagato (f : Int → Int → Int) : Prop :=
  ∀ tot resi, 0 < tot → 0 ≤ resi → resi ≤ tot → f tot resi ≤ pagato tot

def NessunReso (f : Int → Int → Int) : Prop :=
  ∀ tot, 0 < tot → f tot 0 = 0

def TuttoReso (f : Int → Int → Int) : Prop :=
  ∀ tot, 0 < tot → f tot tot = pagato tot

/-- Il pacchetto di garanzie che l'esperimento ha prodotto. Tutte vere,
    tutte dimostrate, tutte sensate. -/
def Base (f : Int → Int → Int) : Prop :=
  NonNeg f ∧ LePagato f ∧ NessunReso f ∧ TuttoReso f

/-! Le due politiche osservate nell'esperimento, in forma minima. -/

/-- **Politica P** (run1 e run2): se il reso fa scendere sotto la soglia,
    la spedizione si riaddebita. Il negativo si taglia a zero. -/
def P (tot resi : Int) : Int :=
  if resi = tot then pagato tot
  else
    let r := if tot ≥ 5000 ∧ tot - resi < 5000 then resi - 499 else resi
    if r < 0 then 0 else r

/-- **Politica Q** (run3 e run4): spedizione gratis una volta,
    gratis per sempre. -/
def Q (tot resi : Int) : Int :=
  if resi = tot then pagato tot else resi

theorem pagato_ge (tot : Int) : tot ≤ pagato tot := by
  unfold pagato; split <;> omega

theorem P_base : Base P := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro tot resi ht h0 hle
    unfold P; split
    · unfold pagato; split <;> omega
    · dsimp only; split <;> split <;> omega
  · intro tot resi ht h0 hle
    have := pagato_ge tot
    unfold P; split
    · omega
    · dsimp only; split <;> split <;> omega
  · intro tot ht
    unfold P; split
    · omega
    · dsimp only; split <;> split <;> omega
  · intro tot ht; unfold P; simp

theorem Q_base : Base Q := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro tot resi ht h0 hle
    unfold Q; split
    · unfold pagato; split <;> omega
    · omega
  · intro tot resi ht h0 hle
    have := pagato_ge tot
    unfold Q; split <;> omega
  · intro tot ht; unfold Q; split <;> omega
  · intro tot ht; unfold Q; simp

/-- **Il controllo 4 fallisce.**

    Due funzioni che soddisfano entrambe l'intero pacchetto di garanzie,
    e che sullo stesso ordine pagano cifre diverse: 25,01 € contro 30,00 €.

    Questa e' una dimostrazione formale che la specifica e' incompleta,
    ottenuta senza andare in produzione e senza aspettare il reclamo. -/
theorem base_non_determina :
    ∃ f g, Base f ∧ Base g ∧ ∃ tot resi,
      0 < tot ∧ 0 ≤ resi ∧ resi ≤ tot ∧ f tot resi ≠ g tot resi :=
  ⟨P, Q, P_base, Q_base, 6000, 3000, by decide, by decide, by decide, by decide⟩

/-! ### Come si chiude: primo giro, una proprieta' generica -/

/-- Rendere di piu' non puo' mai rimborsare di meno. Vincolo di buon senso,
    valido in qualunque dominio, non serve conoscere il business. -/
def Monotono (f : Int → Int → Int) : Prop :=
  ∀ tot r₁ r₂, 0 ≤ r₁ → r₁ ≤ r₂ → r₂ ≤ tot → f tot r₁ ≤ f tot r₂

/-- **La monotonia uccide la politica P da sola.**

    Su un ordine da 51,00 €: rendendo 1,00 € ti danno 1,00 €,
    rendendone 2,00 € ti danno 0,00 €. Rendere di piu' rimborsa di meno.
    Nessuno l'aveva notato, ed e' un controllo automatico. -/
theorem P_non_monotono : ¬ Monotono P := by
  intro h
  have := h 5100 100 200 (by decide) (by decide) (by decide)
  revert this
  decide

theorem Q_monotono : Monotono Q := by
  intro tot r₁ r₂ h0 h12 h2
  have := pagato_ge tot
  unfold Q; split <;> split <;> omega

/-! ### Secondo giro: e non basta ancora -/

/-- La politica "ti ridiamo meta' di quello che rendi". Assurda,
    ma soddisfa ogni garanzia dell'elenco, monotonia inclusa. -/
def Meta (tot resi : Int) : Int :=
  if resi = tot then pagato tot else resi / 2

theorem Meta_base : Base Meta := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro tot resi ht h0 hle
    unfold Meta; split
    · unfold pagato; split <;> omega
    · omega
  · intro tot resi ht h0 hle
    have := pagato_ge tot
    unfold Meta; split
    · omega
    · omega
  · intro tot ht; unfold Meta; split <;> simp_all
  · intro tot ht; unfold Meta; simp

theorem Meta_monotono : Monotono Meta := by
  intro tot r₁ r₂ h0 h12 h2
  have := pagato_ge tot
  unfold Meta; split <;> split <;> omega

/-- **Le proprieta' generiche non bastano.** `Q` e `Meta` soddisfano
    entrambe tutto il pacchetto piu' la monotonia, e su un reso da
    30,00 € una paga 30,00 e l'altra 15,00.

    Qui si tocca il fondo: nessuna proprieta' generica ti dira' mai
    quale delle due voleva l'azienda. -/
theorem base_e_monotonia_non_bastano :
    ∃ f g, Base f ∧ Monotono f ∧ Base g ∧ Monotono g ∧ ∃ tot resi,
      0 < tot ∧ 0 ≤ resi ∧ resi ≤ tot ∧ f tot resi ≠ g tot resi :=
  ⟨Q, Meta, Q_base, Q_monotono, Meta_base, Meta_monotono,
   6000, 3000, by decide, by decide, by decide, by decide⟩

/-! ### Terzo giro: la riga che chiude -/

/-- **La decisione, resa esplicita.** Una riga. Questa e' la cosa che
    un umano deve leggere e firmare, e non c'e' modo di dedurla. -/
def RimborsoParzialeEsatto (f : Int → Int → Int) : Prop :=
  ∀ tot resi, 0 ≤ resi → resi < tot → f tot resi = resi

def Politica (f : Int → Int → Int) : Prop :=
  Base f ∧ RimborsoParzialeEsatto f

/-- **Il controllo 4 passa.**

    Aggiunta quella riga, la specifica ha esattamente UNA soluzione:
    due funzioni qualunque che la soddisfano coincidono ovunque.
    Il buco e' chiuso, e adesso e' chiuso in modo dimostrato. -/
theorem politica_determina (f g : Int → Int → Int)
    (hf : Politica f) (hg : Politica g) :
    ∀ tot resi, 0 < tot → 0 ≤ resi → resi ≤ tot → f tot resi = g tot resi := by
  intro tot resi ht h0 hle
  by_cases heq : resi = tot
  · subst heq
    rw [hf.1.2.2.2 resi ht, hg.1.2.2.2 resi ht]
  · have hlt : resi < tot := by omega
    rw [hf.2 tot resi h0 hlt, hg.2 tot resi h0 hlt]

theorem Q_politica : Politica Q := by
  refine ⟨Q_base, ?_⟩
  intro tot resi h0 hlt
  unfold Q; split
  · omega
  · rfl

/-- E la politica P viene esclusa esplicitamente, come deve essere. -/
theorem P_non_politica : ¬ Politica P := by
  rintro ⟨-, hp⟩
  have := hp 6000 3000 (by decide) (by decide)
  revert this
  decide

end Rimborso

end LPCM
