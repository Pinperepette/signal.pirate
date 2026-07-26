/-!
# Ricerca binaria su `Array Int`, con dimostrazione di correttezza

L'algoritmo lavora sulla finestra semiaperta `[lo, hi)` e mantiene come
invariante di tipo `hi ≤ a.size`, così ogni accesso all'array è dimostrato
in bounds (nessun `a[i]!`, nessun `panic`).

Sono dimostrati due enunciati, che insieme danno la specifica completa:

* `binarySearch_sound`   — se ritorna `some i`, in posizione `i` c'è davvero `x`
                            (vale per QUALSIASI array, anche non ordinato);
* `binarySearch_complete` — se ritorna `none` e l'array è ordinato,
                            allora `x` non compare in nessuna posizione.
-/

/-- Un array di interi è ordinato se gli elementi crescono (debolmente) con l'indice. -/
def Sorted (a : Array Int) : Prop :=
  ∀ (i j : Nat) (hi : i < a.size) (hj : j < a.size), i ≤ j → a[i] ≤ a[j]

/-- Ricerca binaria di `x` nella finestra semiaperta `[lo, hi)` di `a`.
    Il punto medio è `lo + (hi - lo) / 2`: non trabocca e sta sempre in `[lo, hi)`. -/
def bsearchIn (a : Array Int) (x : Int) (lo hi : Nat) (hle : hi ≤ a.size) : Option Nat :=
  if h : lo < hi then
    if a[lo + (hi - lo) / 2]'(by omega) = x then
      some (lo + (hi - lo) / 2)
    else if a[lo + (hi - lo) / 2]'(by omega) < x then
      bsearchIn a x (lo + (hi - lo) / 2 + 1) hi hle
    else
      bsearchIn a x lo (lo + (hi - lo) / 2) (by omega)
  else
    none
termination_by hi - lo

/-- Ricerca binaria su tutto l'array. -/
def binarySearch (a : Array Int) (x : Int) : Option Nat :=
  bsearchIn a x 0 a.size (Nat.le_refl _)

/-! ## Correttezza -/

/-- Soundness: se la ricerca restituisce un indice, lì c'è davvero `x`.
    Non serve alcuna ipotesi di ordinamento. -/
theorem bsearchIn_sound (a : Array Int) (x : Int) :
    ∀ (lo hi : Nat) (hle : hi ≤ a.size) (i : Nat),
      bsearchIn a x lo hi hle = some i → a[i]? = some x := by
  intro lo hi hle
  induction lo, hi, hle using bsearchIn.induct (a := a) (x := x) with
  | case1 lo hi hle h heq =>
      -- trovato al punto medio
      intro i hres
      rw [bsearchIn, dif_pos h, if_pos heq] at hres
      injection hres with hres
      subst hres
      rw [Array.getElem?_eq_getElem (show lo + (hi - lo) / 2 < a.size by omega)]
      exact congrArg some heq
  | case2 lo hi hle h hne hlt ih =>
      -- a[mid] < x: si prosegue a destra
      intro i hres
      rw [bsearchIn, dif_pos h, if_neg hne, if_pos hlt] at hres
      exact ih i hres
  | case3 lo hi hle h hne hnlt ih =>
      -- a[mid] > x: si prosegue a sinistra
      intro i hres
      rw [bsearchIn, dif_pos h, if_neg hne, if_neg hnlt] at hres
      exact ih i hres
  | case4 lo hi hle h =>
      -- finestra vuota: il risultato è `none`, l'ipotesi è assurda
      intro i hres
      rw [bsearchIn, dif_neg h] at hres
      simp at hres

/-- Completezza: se la ricerca fallisce su un array ordinato,
    allora `x` non compare nella finestra `[lo, hi)`. -/
theorem bsearchIn_complete (a : Array Int) (hs : Sorted a) (x : Int) :
    ∀ (lo hi : Nat) (hle : hi ≤ a.size),
      bsearchIn a x lo hi hle = none →
        ∀ (j : Nat) (hj : j < a.size), lo ≤ j → j < hi → a[j] ≠ x := by
  intro lo hi hle
  induction lo, hi, hle using bsearchIn.induct (a := a) (x := x) with
  | case1 lo hi hle h heq =>
      intro hres
      rw [bsearchIn, dif_pos h, if_pos heq] at hres
      simp at hres
  | case2 lo hi hle h hne hlt ih =>
      intro hres j hj hjlo hjhi
      rw [bsearchIn, dif_pos h, if_neg hne, if_pos hlt] at hres
      by_cases hjm : j ≤ lo + (hi - lo) / 2
      · -- a sinistra del medio: a[j] ≤ a[mid] < x, quindi a[j] ≠ x
        intro hjx
        have hmono := hs j (lo + (hi - lo) / 2) hj (by omega) hjm
        omega
      · -- a destra: lo dice l'ipotesi induttiva
        exact ih hres j hj (by omega) hjhi
  | case3 lo hi hle h hne hnlt ih =>
      intro hres j hj hjlo hjhi
      rw [bsearchIn, dif_pos h, if_neg hne, if_neg hnlt] at hres
      by_cases hjm : j < lo + (hi - lo) / 2
      · exact ih hres j hj hjlo hjm
      · -- a destra del medio: a[j] ≥ a[mid] > x, quindi a[j] ≠ x
        intro hjx
        have hmono := hs (lo + (hi - lo) / 2) j (by omega) hj (by omega)
        omega
  | case4 lo hi hle h =>
      -- finestra vuota: non esiste alcun `j` con `lo ≤ j < hi`
      intro hres j hj hjlo hjhi
      exfalso; omega

/-- Se `binarySearch` restituisce `some i`, allora `i` è in bounds e `a[i] = x`. -/
theorem binarySearch_sound {a : Array Int} {x : Int} {i : Nat}
    (h : binarySearch a x = some i) : a[i]? = some x :=
  bsearchIn_sound a x 0 a.size (Nat.le_refl _) i h

/-- Su un array ordinato, se `binarySearch` restituisce `none`
    allora `x` non compare in nessuna posizione. -/
theorem binarySearch_complete {a : Array Int} (hs : Sorted a) {x : Int}
    (h : binarySearch a x = none) : ∀ (j : Nat) (hj : j < a.size), a[j] ≠ x := by
  intro j hj
  exact bsearchIn_complete a hs x 0 a.size (Nat.le_refl _) h j hj (Nat.zero_le _) hj

/-- Specifica completa su array ordinati: la ricerca fallisce
    se e solo se l'elemento non c'è. -/
theorem binarySearch_eq_none_iff {a : Array Int} (hs : Sorted a) {x : Int} :
    binarySearch a x = none ↔ ∀ (j : Nat) (hj : j < a.size), a[j] ≠ x := by
  constructor
  · exact binarySearch_complete hs
  · intro hnone
    cases hfound : binarySearch a x with
    | none => rfl
    | some i =>
        obtain ⟨hlt, heq⟩ := Array.getElem?_eq_some_iff.mp (binarySearch_sound hfound)
        exact absurd heq (hnone i hlt)

/-- La stessa specifica in termini di appartenenza:
    su un array ordinato la ricerca trova un indice esattamente quando `x ∈ a`. -/
theorem binarySearch_isSome_iff_mem {a : Array Int} (hs : Sorted a) {x : Int} :
    (binarySearch a x).isSome ↔ x ∈ a := by
  constructor
  · intro hsome
    match hfound : binarySearch a x, hsome with
    | some i, _ =>
        obtain ⟨hlt, heq⟩ := Array.getElem?_eq_some_iff.mp (binarySearch_sound hfound)
        exact heq ▸ Array.getElem_mem hlt
  · intro hmem
    obtain ⟨j, hj, heq⟩ := Array.mem_iff_getElem.mp hmem
    cases hfound : binarySearch a x with
    | some i => rfl
    | none => exact absurd heq (binarySearch_complete hs hfound j hj)

/-! ## Prove di esecuzione -/

#eval binarySearch #[-5, -1, 0, 3, 7, 12, 42] 7     -- some 4
#eval binarySearch #[-5, -1, 0, 3, 7, 12, 42] (-5)  -- some 0
#eval binarySearch #[-5, -1, 0, 3, 7, 12, 42] 42    -- some 6
#eval binarySearch #[-5, -1, 0, 3, 7, 12, 42] 8     -- none
#eval binarySearch (#[] : Array Int) 0              -- none

example : binarySearch #[-5, -1, 0, 3, 7, 12, 42] 7 = some 4 := by native_decide
example : binarySearch #[-5, -1, 0, 3, 7, 12, 42] 8 = none := by native_decide
