/-! # Ricerca binaria su `Array Int`, con prova di correttezza. -/

namespace Ricerca

/-- Un array è ordinato (in senso non decrescente). -/
def Sorted (a : Array Int) : Prop :=
  ∀ i j : Nat, i ≤ j → j < a.size → a[i]! ≤ a[j]!

/-- Ricerca binaria nell'intervallo semiaperto `[lo, hi)`. -/
def go (a : Array Int) (t : Int) (lo hi : Nat) : Option Nat :=
  if lo < hi then
    let mid := lo + (hi - lo) / 2
    if a[mid]! = t then some mid
    else if a[mid]! < t then go a t (mid + 1) hi
    else go a t lo mid
  else
    none
termination_by hi - lo

/-- Ricerca binaria su tutto l'array. -/
def binarySearch (a : Array Int) (t : Int) : Option Nat :=
  go a t 0 a.size

/-- Correttezza (soundness): se `go` restituisce un indice, quell'indice sta
nell'intervallo esplorato e contiene davvero `t`. -/
theorem go_sound (a : Array Int) (t : Int) :
    ∀ lo hi i, go a t lo hi = some i → lo ≤ i ∧ i < hi ∧ a[i]! = t := by
  intro lo hi
  induction lo, hi using go.induct a t
  next lo hi hlt mid hfound =>
    intro i h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_pos hfound] at h
    have : mid = i := Option.some.inj h
    subst this
    exact ⟨by omega, by omega, hfound⟩
  next lo hi hlt mid hne hlt2 ih =>
    intro i h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_neg hne, if_pos hlt2] at h
    have := ih i h
    omega
  next lo hi hlt mid hne hnlt ih =>
    intro i h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_neg hne, if_neg hnlt] at h
    have := ih i h
    omega
  next lo hi hnlt =>
    intro i h
    rw [go, if_neg hnlt] at h
    exact absurd h (by simp)

/-- Completezza: se l'array è ordinato, gli elementi fuori da `[lo, hi)` stanno
già dalla parte sbagliata rispetto a `t` e `go` fallisce, allora `t` non compare
da nessuna parte nell'array. -/
theorem go_complete (a : Array Int) (t : Int) (hs : Sorted a) :
    ∀ lo hi, hi ≤ a.size →
      (∀ j, j < lo → a[j]! < t) →
      (∀ j, hi ≤ j → j < a.size → t < a[j]!) →
      go a t lo hi = none →
      ∀ j, j < a.size → a[j]! ≠ t := by
  intro lo hi
  induction lo, hi using go.induct a t
  next lo hi hlt mid hfound =>
    intro _ _ _ h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_pos hfound] at h
    exact absurd h (by simp)
  next lo hi hlt mid hne hlt2 ih =>
    intro hhi hlow hhigh h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_neg hne, if_pos hlt2] at h
    -- a sinistra di `mid` tutto è `≤ a[mid]! < t`
    refine ih hhi (fun j hj => ?_) hhigh h
    have : a[j]! ≤ a[mid]! := hs j mid (by omega) (by omega)
    omega
  next lo hi hlt mid hne hnlt ih =>
    intro hhi hlow hhigh h
    have hm : mid = lo + (hi - lo) / 2 := rfl
    rw [go, if_pos hlt, ← hm, if_neg hne, if_neg hnlt] at h
    -- a destra di `mid` tutto è `≥ a[mid]! > t`
    refine ih (by omega) hlow (fun j hj hjs => ?_) h
    have : a[mid]! ≤ a[j]! := hs mid j hj hjs
    omega
  next lo hi hnlt =>
    intro _ hlow hhigh _ j hj
    rcases Nat.lt_or_ge j lo with h1 | h1
    · have := hlow j h1
      omega
    · have := hhigh j (by omega) hj
      omega

/-- Se `binarySearch` restituisce un indice, quell'indice è valido e contiene `t`.
Vale per ogni array, anche non ordinato. -/
theorem binarySearch_some (a : Array Int) (t : Int) (i : Nat)
    (h : binarySearch a t = some i) : i < a.size ∧ a[i]! = t :=
  let ⟨_, h2, h3⟩ := go_sound a t 0 a.size i h
  ⟨h2, h3⟩

/-- Se l'array è ordinato e `binarySearch` restituisce `none`, allora `t` davvero
non compare nell'array. -/
theorem binarySearch_none (a : Array Int) (t : Int) (hs : Sorted a)
    (h : binarySearch a t = none) : ∀ j, j < a.size → a[j]! ≠ t :=
  go_complete a t hs 0 a.size (Nat.le_refl _)
    (fun _ hj => absurd hj (by omega))
    (fun _ h1 h2 => absurd h1 (by omega)) h

/-- Correttezza piena su array ordinati: la ricerca trova qualcosa se e solo se
`t` è presente. -/
theorem binarySearch_isSome_iff (a : Array Int) (t : Int) (hs : Sorted a) :
    (binarySearch a t).isSome = true ↔ ∃ i, i < a.size ∧ a[i]! = t := by
  constructor
  · intro h
    cases hb : binarySearch a t with
    | none => rw [hb] at h; simp at h
    | some i => exact ⟨i, binarySearch_some a t i hb⟩
  · rintro ⟨i, hi, hval⟩
    cases hb : binarySearch a t with
    | none => exact absurd hval (binarySearch_none a t hs hb i hi)
    | some _ => rfl

/-! ## Controlli eseguibili -/

#guard binarySearch #[1, 3, 5, 7, 9] 5 = some 2
#guard binarySearch #[1, 3, 5, 7, 9] 1 = some 0
#guard binarySearch #[1, 3, 5, 7, 9] 9 = some 4
#guard binarySearch #[1, 3, 5, 7, 9] 4 = none
#guard binarySearch #[] 0 = none

end Ricerca
