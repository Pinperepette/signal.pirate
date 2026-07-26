/-
  QUATTRO MODI DI OTTENERE IL ✓ SENZA DIMOSTRARE NIENTE.

  Tutto quello che segue e' dimostrato su `bsearchBuggy`, cioe' su una
  funzione che sbaglia su 3 elementi su 7 realmente presenti nell'array.
  Ogni teorema qui sotto compila. Ogni teorema qui sotto e' vero.
  Nessuno di questi teoremi dice che la funzione funziona.
-/
import LaProvaCheMente.Basic

namespace LPCM

/--
  La specifica ONESTA, quella che vorremmo davvero.
  Due direzioni: se trova qualcosa e' giusto, e se non trova niente
  allora davvero non c'era niente.
-/
def FullSpec (f : Array Int → Int → Option Nat) (a : Array Int) (t : Int) : Prop :=
  (∀ i, f a t = some i → i < a.size ∧ a[i]! = t) ∧
  (f a t = none → ¬ Contains a t)

/- ------------------------------------------------------------------ -/
/- TRUFFA 1 — `sorry`                                                   -/
/- ------------------------------------------------------------------ -/

/--
  L'enunciato e' quello giusto, completo, senza ipotesi di comodo.
  La dimostrazione e' un buco.
-/
theorem bsearchBuggy_spec_v1 (a : Array Int) (t : Int) (_h : Sorted a) :
    FullSpec bsearchBuggy a t := by
  sorry

/- ------------------------------------------------------------------ -/
/- TRUFFA 2 — ipotesi contraddittorie (il teorema e' VACUO)             -/
/- ------------------------------------------------------------------ -/

/-- Strettamente decrescente. Da sola e' una condizione sensatissima. -/
def StrictDecr (a : Array Int) : Prop :=
  ∀ i j, i < j → j < a.size → a[j]! < a[i]!

/--
  Stesso enunciato di prima, e stavolta niente `sorry`: dimostrazione vera.
  Peccato che `Sorted a` e `StrictDecr a` insieme, su un array con almeno
  due elementi, non possano valere contemporaneamente. Le ipotesi non hanno
  **nessun modello**: il teorema e' vero perche' non parla di niente.
-/
theorem bsearchBuggy_spec_v2 (a : Array Int) (t : Int)
    (hs : Sorted a) (hd : StrictDecr a) (hsz : 2 ≤ a.size) :
    FullSpec bsearchBuggy a t := by
  exfalso
  have h1 : a[0]! ≤ a[1]! := hs 0 1 (by omega) (by omega)
  have h2 : a[1]! < a[0]! := hd 0 1 (by omega) (by omega)
  omega

/- ------------------------------------------------------------------ -/
/- TRUFFA 3 — precondizione che esclude ogni caso interessante          -/
/- ------------------------------------------------------------------ -/

/--
  Questa ipotesi NON e' contraddittoria: l'array vuoto la soddisfa.
  Sembra una condizione di buona formazione. In realta' dice
  "l'array e' vuoto" scritto in modo che non si veda.
-/
theorem bsearchBuggy_spec_v3 (a : Array Int) (t : Int)
    (_hs : Sorted a) (hwf : ∀ i, i < a.size → i < 0) :
    FullSpec bsearchBuggy a t := by
  have hempty : a.size = 0 := by
    match h : a.size with
    | 0 => rfl
    | n + 1 => have := hwf 0 (by omega); omega
  have hnone : bsearchBuggy a t = none := by
    unfold bsearchBuggy
    rw [hempty, bsearchBuggy.go.eq_def]
    simp
  constructor
  · intro i hi
    rw [hnone] at hi
    exact absurd hi (by simp)
  · intro _ hc
    obtain ⟨i, hi, _⟩ := hc
    omega

/- ------------------------------------------------------------------ -/
/- TRUFFA 4 — il teorema indebolito (una direzione sola)                -/
/- ------------------------------------------------------------------ -/

/--
  Questo e' **vero**, e non e' vacuo: dice qualcosa di reale.
  Dice che quando la funzione risponde, non mente.
  Non dice una parola su cosa succede quando tace.

  E' la truffa piu' pericolosa delle quattro, perche' e' onesta.
  Semplicemente non e' la specifica che serviva.
-/
theorem bsearchBuggy_sound (a : Array Int) (t : Int) :
    ∀ i, bsearchBuggy a t = some i → i < a.size ∧ a[i]! = t := by
  have key : ∀ lo hi, hi ≤ a.size → ∀ i,
      bsearchBuggy.go a t lo hi = some i → i < a.size ∧ a[i]! = t := by
    intro lo hi
    induction lo, hi using bsearchBuggy.go.induct (a := a) (t := t) with
    | case1 lo hi hlt mid heq =>
      intro hle i h
      have heq' : a[(lo + hi) / 2]! = t := heq
      rw [bsearchBuggy.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_pos heq'] at h
      simp only [Option.some.injEq] at h
      subst h
      exact ⟨by omega, heq'⟩
    | case2 lo hi hlt mid hne hlt2 ih =>
      intro hle i h
      have hne' : ¬ a[(lo + hi) / 2]! = t := hne
      have hlt2' : a[(lo + hi) / 2]! < t := hlt2
      rw [bsearchBuggy.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_neg hne', if_pos hlt2'] at h
      exact ih hle i h
    | case3 lo hi hlt mid hne hge ih =>
      intro hle i h
      have hne' : ¬ a[(lo + hi) / 2]! = t := hne
      have hge' : ¬ a[(lo + hi) / 2]! < t := hge
      rw [bsearchBuggy.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_neg hne', if_neg hge'] at h
      exact ih (by omega) i h
    | case4 lo hi hge =>
      intro _ i h
      rw [bsearchBuggy.go.eq_def, dif_neg hge] at h
      exact absurd h (by simp)
  intro i h
  exact key 0 a.size (Nat.le_refl _) i h

/- ------------------------------------------------------------------ -/
/- IL COLPO DI GRAZIA                                                   -/
/- ------------------------------------------------------------------ -/

/--
  Esattamente lo stesso enunciato di `bsearchBuggy_sound`.
  Stessa firma, stessa promessa, stesso ✓.
  Ma qui la funzione e' `fun _ _ => none`: non trova mai niente.

  Se una specifica e' soddisfatta da una funzione che non fa nulla,
  quella specifica non stava misurando il tuo codice.
-/
theorem bsearchNever_sound (a : Array Int) (t : Int) :
    ∀ i, bsearchNever a t = some i → i < a.size ∧ a[i]! = t := by
  intro i h
  exact absurd h (by simp [bsearchNever])

end LPCM
