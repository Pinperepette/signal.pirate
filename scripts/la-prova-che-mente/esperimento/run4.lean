/-!
# Ricerca binaria su `Array Int` con dimostrazione di correttezza

Implementazione della ricerca binaria classica sull'intervallo semiaperto `[lo, hi)`
e prova che è corretta:

* **soundness**: se restituisce `some i`, allora `i` è un indice valido e `a[i] = t`
  (vale per qualunque array, anche non ordinato);
* **completeness**: se restituisce `none` e l'array è ordinato, allora `t` non compare
  in nessuna posizione dell'array.
-/

namespace Ricerca

/-- `a` è ordinato in senso non decrescente. -/
def Sorted (a : Array Int) : Prop :=
  ∀ i j : Nat, i ≤ j → j < a.size → a[i]! ≤ a[j]!

/-- Ricerca binaria di `t` in `a` ristretta all'intervallo semiaperto `[lo, hi)`. -/
def bsearchAux (a : Array Int) (t : Int) (lo hi : Nat) : Option Nat :=
  if _h : lo < hi then
    if a[(lo + hi) / 2]! = t then
      some ((lo + hi) / 2)
    else if a[(lo + hi) / 2]! < t then
      bsearchAux a t ((lo + hi) / 2 + 1) hi
    else
      bsearchAux a t lo ((lo + hi) / 2)
  else
    none
termination_by hi - lo
decreasing_by all_goals omega

/-- Ricerca binaria di `t` sull'intero array `a`. -/
def binarySearch (a : Array Int) (t : Int) : Option Nat :=
  bsearchAux a t 0 a.size

/-! ## Soundness -/

/-- Se `bsearchAux` restituisce un indice, quell'indice è valido e contiene `t`.
Non serve alcuna ipotesi di ordinamento. -/
theorem bsearchAux_sound (a : Array Int) (t : Int) (lo hi : Nat) (hhi : hi ≤ a.size)
    (i : Nat) (h : bsearchAux a t lo hi = some i) :
    i < a.size ∧ a[i]! = t := by
  rw [bsearchAux] at h
  split at h
  next hlt =>
    split at h
    next heq =>
      have hmid : (lo + hi) / 2 = i := Option.some.inj h
      subst hmid
      exact ⟨by omega, heq⟩
    next hne =>
      split at h
      next _ => exact bsearchAux_sound a t ((lo + hi) / 2 + 1) hi hhi i h
      next _ => exact bsearchAux_sound a t lo ((lo + hi) / 2) (by omega) i h
  next _ => simp at h
termination_by hi - lo
decreasing_by all_goals omega

/-! ## Completeness -/

/-- Se `bsearchAux` fallisce su un array ordinato, e tutto ciò che sta a sinistra di `lo`
è `< t` mentre tutto ciò che sta a destra di `hi` è `> t`, allora `t` non compare
da nessuna parte nell'array. -/
theorem bsearchAux_complete (a : Array Int) (t : Int) (hs : Sorted a) (lo hi : Nat)
    (hhi : hi ≤ a.size)
    (hlow : ∀ k, k < lo → k < a.size → a[k]! < t)
    (hhigh : ∀ k, hi ≤ k → k < a.size → t < a[k]!)
    (h : bsearchAux a t lo hi = none) :
    ∀ k, k < a.size → a[k]! ≠ t := by
  rw [bsearchAux] at h
  split at h
  next hlt =>
    split at h
    next _ => simp at h
    next hne =>
      split at h
      next hless =>
        -- il valore centrale è `< t`: tutto ciò che sta a sinistra di `mid+1` è `< t`
        refine bsearchAux_complete a t hs ((lo + hi) / 2 + 1) hi hhi ?_ hhigh h
        intro k hk hks
        have hmono := hs k ((lo + hi) / 2) (by omega) (by omega)
        omega
      next hge =>
        -- il valore centrale è `> t`: tutto ciò che sta a destra di `mid` è `> t`
        refine bsearchAux_complete a t hs lo ((lo + hi) / 2) (by omega) hlow ?_ h
        intro k hk hks
        have hmono := hs ((lo + hi) / 2) k hk hks
        omega
  next hempty =>
    -- intervallo vuoto: ogni indice cade a sinistra di `lo` o a destra di `hi`
    intro k hks
    rcases Nat.lt_or_ge k lo with hk | hk
    · have := hlow k hk hks; omega
    · have := hhigh k (by omega) hks; omega
termination_by hi - lo
decreasing_by all_goals omega

/-! ## Teoremi principali -/

/-- **Soundness**: `binarySearch` non mente mai. -/
theorem binarySearch_sound (a : Array Int) (t : Int) (i : Nat)
    (h : binarySearch a t = some i) : i < a.size ∧ a[i]! = t :=
  bsearchAux_sound a t 0 a.size (Nat.le_refl _) i h

/-- **Completeness**: su un array ordinato, se `binarySearch` restituisce `none`
allora `t` davvero non c'è. -/
theorem binarySearch_complete (a : Array Int) (t : Int) (hs : Sorted a)
    (h : binarySearch a t = none) : ∀ k, k < a.size → a[k]! ≠ t := by
  refine bsearchAux_complete a t hs 0 a.size (Nat.le_refl _) ?_ ?_ h
  · intro k hk _; omega
  · intro k hk hks; omega

/-- **Correttezza completa**: su un array ordinato, la ricerca binaria trova un indice
se e solo se il valore è presente. -/
theorem binarySearch_correct (a : Array Int) (t : Int) (hs : Sorted a) :
    (∃ i, binarySearch a t = some i) ↔ (∃ k, k < a.size ∧ a[k]! = t) := by
  constructor
  · rintro ⟨i, hi⟩
    exact ⟨i, binarySearch_sound a t i hi⟩
  · rintro ⟨k, hk, hkt⟩
    cases hres : binarySearch a t with
    | none => exact absurd hkt (binarySearch_complete a t hs hres k hk)
    | some i => exact ⟨i, rfl⟩

/-- Versione con l'indicizzazione dipendente `a[i]'h` invece di `a[i]!`. -/
theorem binarySearch_sound' (a : Array Int) (t : Int) (i : Nat)
    (h : binarySearch a t = some i) : ∃ hlt : i < a.size, a[i]'hlt = t := by
  obtain ⟨hlt, heq⟩ := binarySearch_sound a t i h
  exact ⟨hlt, by rwa [getElem!_pos a i hlt] at heq⟩

/-- Su un array ordinato, la ricerca binaria ha successo esattamente quando
`t` appartiene all'array. -/
theorem binarySearch_isSome_iff_mem (a : Array Int) (t : Int) (hs : Sorted a) :
    (binarySearch a t).isSome ↔ t ∈ a := by
  rw [Option.isSome_iff_exists, Array.mem_iff_getElem]
  constructor
  · rintro ⟨i, hi⟩
    obtain ⟨hlt, heq⟩ := binarySearch_sound' a t i hi
    exact ⟨i, hlt, heq⟩
  · rintro ⟨k, hk, hkt⟩
    have hbang : a[k]! = t := by rw [getElem!_pos a k hk]; exact hkt
    obtain ⟨i, hi⟩ := (binarySearch_correct a t hs).mpr ⟨k, hk, hbang⟩
    exact ⟨i, hi⟩

/-! ## Prove di funzionamento -/

/-- info: some 3 -/
#guard_msgs in
#eval binarySearch #[-5, 0, 2, 7, 11, 40] 7

/-- info: none -/
#guard_msgs in
#eval binarySearch #[-5, 0, 2, 7, 11, 40] 8

/-- info: some 0 -/
#guard_msgs in
#eval binarySearch #[-5, 0, 2, 7, 11, 40] (-5)

/-- info: none -/
#guard_msgs in
#eval binarySearch #[] 0

end Ricerca
