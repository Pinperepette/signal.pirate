/-
  LA SPECIFICA ONESTA.

  Nessuna ipotesi di comodo, nessun `sorry`, nessun assioma,
  e soprattutto: **entrambe le direzioni**.

    se trova qualcosa, e' giusto      (soundness)
    se non trova niente, non c'era    (completeness)

  La seconda direzione e' quella che tutte le truffe evitavano.
  E' anche l'unica che costringe il codice a essere corretto davvero.
-/
import LaProvaCheMente.Truffe

namespace LPCM

/- ------------------------------------------------------------------ -/
/- Direzione 1: soundness. Identica a quella su bsearchBuggy.           -/
/- Nota: passa anche sul codice rotto. Non e' lei che trova il bug.     -/
/- ------------------------------------------------------------------ -/

theorem bsearch_sound (a : Array Int) (t : Int) :
    ∀ i, bsearch a t = some i → i < a.size ∧ a[i]! = t := by
  have key : ∀ lo hi, hi ≤ a.size → ∀ i,
      bsearch.go a t lo hi = some i → i < a.size ∧ a[i]! = t := by
    intro lo hi
    induction lo, hi using bsearch.go.induct (a := a) (t := t) with
    | case1 lo hi hlt mid heq =>
      intro hle i h
      have heq' : a[(lo + hi) / 2]! = t := heq
      rw [bsearch.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_pos heq'] at h
      simp only [Option.some.injEq] at h
      subst h
      exact ⟨by omega, heq'⟩
    | case2 lo hi hlt mid hne hlt2 ih =>
      intro hle i h
      have hne' : ¬ a[(lo + hi) / 2]! = t := hne
      have hlt2' : a[(lo + hi) / 2]! < t := hlt2
      rw [bsearch.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_neg hne', if_pos hlt2'] at h
      exact ih hle i h
    | case3 lo hi hlt mid hne hge ih =>
      intro hle i h
      have hne' : ¬ a[(lo + hi) / 2]! = t := hne
      have hge' : ¬ a[(lo + hi) / 2]! < t := hge
      rw [bsearch.go.eq_def] at h
      simp only [hlt, dif_pos] at h
      rw [if_neg hne', if_neg hge'] at h
      exact ih (by omega) i h
    | case4 lo hi hge =>
      intro _ i h
      rw [bsearch.go.eq_def, dif_neg hge] at h
      exact absurd h (by simp)
  intro i h
  exact key 0 a.size (Nat.le_refl _) i h

/- ------------------------------------------------------------------ -/
/- Direzione 2: completeness. Qui serve l'invariante di ricerca.        -/
/- ------------------------------------------------------------------ -/

/--
  Il cuore della dimostrazione: l'invariante che la ricerca binaria
  mantiene a ogni passo e che nessuna delle truffe nominava.

  * tutto quello che sta **sotto** `lo` e' strettamente minore di `t`
  * tutto quello che sta **sopra o su** `hi` e' strettamente maggiore di `t`

  Se l'intervallo si svuota, `t` non puo' stare da nessuna parte.
-/
theorem bsearch_complete_aux (a : Array Int) (t : Int) (hs : Sorted a) :
    ∀ lo hi, hi ≤ a.size →
      (∀ k, k < lo → a[k]! < t) →
      (∀ k, hi ≤ k → k < a.size → t < a[k]!) →
      bsearch.go a t lo hi = none →
      ∀ i, i < a.size → a[i]! ≠ t := by
  intro lo hi
  induction lo, hi using bsearch.go.induct (a := a) (t := t) with
  | case1 lo hi hlt mid heq =>
    -- ha trovato qualcosa: l'ipotesi "restituisce none" e' falsa
    intro hle _ _ h
    have heq' : a[(lo + hi) / 2]! = t := heq
    rw [bsearch.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_pos heq'] at h
    exact absurd h (by simp)
  | case2 lo hi hlt mid hne hlt2 ih =>
    -- a[mid] < t : scarta la meta' bassa, INCLUSO mid
    intro hle hlow hhigh h
    have hne' : ¬ a[(lo + hi) / 2]! = t := hne
    have hlt2' : a[(lo + hi) / 2]! < t := hlt2
    have hmid : (lo + hi) / 2 < a.size := by omega
    rw [bsearch.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_neg hne', if_pos hlt2'] at h
    refine ih hle ?_ hhigh h
    intro k hk
    rcases Nat.lt_or_ge k ((lo + hi) / 2) with hkm | hkm
    · exact Int.lt_of_le_of_lt (hs k _ hkm hmid) hlt2'
    · have : k = (lo + hi) / 2 := by omega
      subst this; exact hlt2'
  | case3 lo hi hlt mid hne hge ih =>
    -- a[mid] > t : scarta la meta' alta, mid COMPRESO
    intro hle hlow hhigh h
    have hne' : ¬ a[(lo + hi) / 2]! = t := hne
    have hge' : ¬ a[(lo + hi) / 2]! < t := hge
    have hmid : (lo + hi) / 2 < a.size := by omega
    have hgt : t < a[(lo + hi) / 2]! := by omega
    rw [bsearch.go.eq_def] at h
    simp only [hlt, dif_pos] at h
    rw [if_neg hne', if_neg hge'] at h
    refine ih (by omega) hlow ?_ h
    intro k hk hka
    rcases Nat.lt_or_ge ((lo + hi) / 2) k with hkm | hkm
    · exact Int.lt_of_lt_of_le hgt (hs _ k hkm hka)
    · have : k = (lo + hi) / 2 := by omega
      subst this; exact hgt
  | case4 lo hi hge =>
    -- intervallo vuoto: ogni indice e' o sotto lo, o sopra hi
    intro _ hlow hhigh _ i hi_lt
    rcases Nat.lt_or_ge i lo with h1 | h1
    · exact Int.ne_of_lt (hlow i h1)
    · have : hi ≤ i := by omega
      exact Int.ne_of_gt (hhigh i this hi_lt)

/--
  **La specifica onesta, dimostrata.**

  Nessun `sorry`. Nessun assioma iniettato. Ipotesi soddisfacibili
  (qualunque array ordinato le soddisfa). Ed entrambe le direzioni.
-/
theorem bsearch_spec (a : Array Int) (t : Int) (hs : Sorted a) :
    FullSpec bsearch a t := by
  constructor
  · exact bsearch_sound a t
  · intro hnone hc
    obtain ⟨i, hi, hval⟩ := hc
    exact bsearch_complete_aux a t hs 0 a.size (Nat.le_refl _)
      (fun k hk => absurd hk (by omega))
      (fun k hk hka => absurd hka (by omega))
      hnone i hi hval

end LPCM
