/-
  QUESTO FILE NON COMPILA. E' il punto del laboratorio.

  E' la copia carbone di `bsearch_complete_aux` (in LaProvaCheMente/Onesta.lean),
  con una sola differenza: e' applicata a `bsearchBuggy` invece che a `bsearch`.

  La stessa specifica che le quattro truffe soddisfacevano senza fatica,
  scritta ONESTAMENTE, rifiuta di essere dimostrata. E non fallisce a caso:
  fallisce nel `case3`, cioe' esattamente nel ramo dove sta l'off-by-one.

  Eseguilo con:  ./dimostra.sh
-/
import LaProvaCheMente.Truffe

namespace LPCM

theorem bsearchBuggy_complete_aux (a : Array Int) (t : Int) (hs : Sorted a) :
    ∀ lo hi, hi ≤ a.size →
      (∀ k, k < lo → a[k]! < t) →
      (∀ k, hi ≤ k → k < a.size → t < a[k]!) →
      bsearchBuggy.go a t lo hi = none →
      ∀ i, i < a.size → a[i]! ≠ t := by
  intro lo hi
  induction lo, hi using bsearchBuggy.go.induct (a := a) (t := t) with
  | case1 lo hi hlt mid heq =>
    intro hle _ _ h
    have heq' : a[(lo + hi) / 2]! = t := heq
    rw [bsearchBuggy.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_pos heq'] at h
    exact absurd h (by simp)
  | case2 lo hi hlt mid hne hlt2 ih =>
    intro hle hlow hhigh h
    have hne' : ¬ a[(lo + hi) / 2]! = t := hne
    have hlt2' : a[(lo + hi) / 2]! < t := hlt2
    have hmid : (lo + hi) / 2 < a.size := by omega
    rw [bsearchBuggy.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_neg hne', if_pos hlt2'] at h
    refine ih hle ?_ hhigh h
    intro k hk
    rcases Nat.lt_or_ge k ((lo + hi) / 2) with hkm | hkm
    · exact Int.lt_of_le_of_lt (hs k _ hkm hmid) hlt2'
    · have : k = (lo + hi) / 2 := by omega
      subst this; exact hlt2'
  | case3 lo hi hlt mid hne hge ih =>
    intro hle hlow hhigh h
    have hne' : ¬ a[(lo + hi) / 2]! = t := hne
    have hge' : ¬ a[(lo + hi) / 2]! < t := hge
    have hmid : (lo + hi) / 2 < a.size := by omega
    have hgt : t < a[(lo + hi) / 2]! := by omega
    rw [bsearchBuggy.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_neg hne', if_neg hge'] at h
    refine ih (by omega) hlow ?_ h
    -- QUI SI ROMPE.
    -- La chiamata ricorsiva e' `go lo (mid - 1)`, quindi l'invariante da
    -- ristabilire e':   ∀ k, mid - 1 ≤ k → k < a.size → t < a[k]!
    -- Ma di `a[mid - 1]!` non sappiamo NIENTE: l'unica cosa che abbiamo
    -- e' `t < a[mid]!`, e mid - 1 sta sotto mid, non sopra.
    -- Nessun ordinamento puo' salvarci: quell'elemento potrebbe valere t.
    intro k hk hka
    rcases Nat.lt_or_ge ((lo + hi) / 2) k with hkm | hkm
    · exact Int.lt_of_lt_of_le hgt (hs _ k hkm hka)
    · have : k = (lo + hi) / 2 := by omega
      subst this; exact hgt
  | case4 lo hi hge =>
    intro _ hlow hhigh _ i hi_lt
    rcases Nat.lt_or_ge i lo with h1 | h1
    · exact Int.ne_of_lt (hlow i h1)
    · have : hi ≤ i := by omega
      exact Int.ne_of_gt (hhigh i this hi_lt)

end LPCM
