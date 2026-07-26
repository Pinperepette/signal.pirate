/-!
# Ricerca binaria su `Array Int`, con dimostrazione di correttezza

Solo libreria standard di Lean 4 (nessuna dipendenza da mathlib).
-/

namespace Ricerca

/-- `Sorted a`: l'array è ordinato in senso debolmente crescente. -/
def Sorted (a : Array Int) : Prop :=
  ∀ i j : Nat, (hi : i < a.size) → (hj : j < a.size) → i ≤ j → a[i] ≤ a[j]

/-- Ricerca binaria nella finestra semiaperta `[lo, hi)`. -/
def go (a : Array Int) (x : Int) (lo hi : Nat) (hhi : hi ≤ a.size) : Option Nat :=
  if hlt : lo < hi then
    have hmid : (lo + hi) / 2 < a.size := by omega
    if a[(lo + hi) / 2] = x then
      some ((lo + hi) / 2)
    else if a[(lo + hi) / 2] < x then
      go a x ((lo + hi) / 2 + 1) hi hhi
    else
      go a x lo ((lo + hi) / 2) (by omega)
  else
    none
termination_by hi - lo

/-- Ricerca binaria di `x` in `a`. Restituisce `some i` se `a[i] = x`, altrimenti `none`. -/
def bsearch (a : Array Int) (x : Int) : Option Nat :=
  go a x 0 a.size (Nat.le_refl _)

/-! ## Correttezza -/

/-- **Soundness**: se `go` restituisce un indice, in quella posizione c'è davvero `x`.
    Non serve che l'array sia ordinato. -/
theorem go_sound (a : Array Int) (x : Int) :
    ∀ (lo hi : Nat) (hhi : hi ≤ a.size) (i : Nat),
      go a x lo hi hhi = some i → a[i]? = some x := by
  intro lo hi hhi
  induction lo, hi, hhi using go.induct (x := x) with
  | case1 lo hi hhi hlt hmid heq =>
    intro i hgo
    rw [go] at hgo
    simp only [hlt, heq, dif_pos, if_pos, Option.some.injEq] at hgo
    subst hgo
    simp [hmid, heq]
  | case2 lo hi hhi hlt hmid hne hlss ih =>
    intro i hgo
    rw [go] at hgo
    simp only [hlt, hne, hlss, dif_pos, if_pos, reduceIte] at hgo
    exact ih i hgo
  | case3 lo hi hhi hlt hmid hne hnlt ih =>
    intro i hgo
    rw [go] at hgo
    simp only [hlt, hne, hnlt, dif_pos, reduceIte] at hgo
    exact ih i hgo
  | case4 lo hi hhi hnlt =>
    intro i hgo
    rw [go, dif_neg hnlt] at hgo
    simp at hgo

/-- **Completeness** (passo induttivo): se `go` fallisce sulla finestra `[lo, hi)`,
    allora in quella finestra `x` non c'è. Qui serve l'ipotesi di ordinamento. -/
theorem go_none (a : Array Int) (x : Int) (hs : Sorted a) :
    ∀ (lo hi : Nat) (hhi : hi ≤ a.size),
      go a x lo hi hhi = none → ∀ j, lo ≤ j → j < hi → a[j]? ≠ some x := by
  intro lo hi hhi
  induction lo, hi, hhi using go.induct (x := x) with
  | case1 lo hi hhi hlt hmid heq =>
    intro hgo
    rw [go] at hgo
    simp only [hlt, heq, dif_pos, if_pos] at hgo
    exact absurd hgo (by simp)
  | case2 lo hi hhi hlt hmid hne hlss ih =>
    intro hgo j hlo hhij
    rw [go] at hgo
    simp only [hlt, hne, hlss, dif_pos, if_pos, reduceIte] at hgo
    by_cases hj : (lo + hi) / 2 + 1 ≤ j
    · exact ih hgo j hj hhij
    · -- `j ≤ mid`, quindi `a[j] ≤ a[mid] < x`
      have hjs : j < a.size := by omega
      have hle : a[j] ≤ a[(lo + hi) / 2] := hs j ((lo + hi) / 2) hjs hmid (by omega)
      simp only [hjs, getElem?_pos, ne_eq, Option.some.injEq]
      omega
  | case3 lo hi hhi hlt hmid hne hnlt ih =>
    intro hgo j hlo hhij
    rw [go] at hgo
    simp only [hlt, hne, hnlt, dif_pos, reduceIte] at hgo
    by_cases hj : j < (lo + hi) / 2
    · exact ih hgo j hlo hj
    · -- `mid ≤ j`, quindi `x < a[mid] ≤ a[j]`
      have hjs : j < a.size := by omega
      have hle : a[(lo + hi) / 2] ≤ a[j] := hs ((lo + hi) / 2) j hmid hjs (by omega)
      simp only [hjs, getElem?_pos, ne_eq, Option.some.injEq]
      omega
  | case4 lo hi hhi hnlt =>
    intro _ j hlo hhij
    omega

/-- Se `bsearch` restituisce un indice, quell'indice contiene davvero `x`.
    Vale per un array qualsiasi, anche non ordinato. -/
theorem bsearch_sound (a : Array Int) (x : Int) (i : Nat) (h : bsearch a x = some i) :
    a[i]? = some x :=
  go_sound a x 0 a.size (Nat.le_refl _) i h

/-- Corollario: l'indice restituito è dentro i limiti dell'array. -/
theorem bsearch_lt_size (a : Array Int) (x : Int) (i : Nat) (h : bsearch a x = some i) :
    i < a.size := by
  have h2 := bsearch_sound a x i h
  match Nat.lt_or_ge i a.size with
  | .inl hlt => exact hlt
  | .inr hge =>
    rw [getElem?_neg a i (by omega)] at h2
    exact absurd h2 (by simp)

/-- Corollario: `a[i] = x` in forma diretta. -/
theorem bsearch_getElem (a : Array Int) (x : Int) (i : Nat) (h : bsearch a x = some i) :
    a[i]'(bsearch_lt_size a x i h) = x := by
  have hs := bsearch_sound a x i h
  rw [getElem?_pos a i (bsearch_lt_size a x i h)] at hs
  exact Option.some.inj hs

/-- Se `bsearch` fallisce su un array **ordinato**, allora `x` non è nell'array. -/
theorem bsearch_complete (a : Array Int) (x : Int) (hs : Sorted a)
    (h : bsearch a x = none) : ∀ j : Nat, a[j]? ≠ some x := by
  intro j
  by_cases hj : j < a.size
  · exact go_none a x hs 0 a.size (Nat.le_refl _) h j (Nat.zero_le _) hj
  · rw [getElem?_neg a j hj]
    simp

/-- **Correttezza totale**: su un array ordinato, `bsearch` trova un'occorrenza di `x`
    se e solo se `x` è presente. -/
theorem bsearch_isSome_iff (a : Array Int) (x : Int) (hs : Sorted a) :
    (bsearch a x).isSome ↔ ∃ j : Nat, a[j]? = some x := by
  constructor
  · intro h
    match hb : bsearch a x with
    | some i => exact ⟨i, bsearch_sound a x i hb⟩
    | none => rw [hb] at h; exact absurd h (by simp)
  · intro ⟨j, hj⟩
    match hb : bsearch a x with
    | some i => simp
    | none => exact absurd hj (bsearch_complete a x hs hb j)

/-! ## Qualche prova di esecuzione -/

/-- info: some 3 -/
#guard_msgs in
#eval bsearch #[-5, 0, 2, 7, 11, 42] 7

/-- info: none -/
#guard_msgs in
#eval bsearch #[-5, 0, 2, 7, 11, 42] 8

/-- info: some 0 -/
#guard_msgs in
#eval bsearch #[-5, 0, 2, 7, 11, 42] (-5)

/-- info: some 5 -/
#guard_msgs in
#eval bsearch #[-5, 0, 2, 7, 11, 42] 42

/-- info: none -/
#guard_msgs in
#eval bsearch (#[] : Array Int) 0

end Ricerca
