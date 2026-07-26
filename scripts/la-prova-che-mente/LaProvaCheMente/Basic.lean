/-
  Definizioni di base per il laboratorio.

  Due implementazioni di ricerca binaria su `Array Int`:
    * `bsearchBuggy` — contiene un off-by-one deliberato
    * `bsearch`      — la versione corretta

  e una terza funzione, `bsearchNever`, che non trova mai niente.
  Serve piu' avanti come colpo di grazia.
-/

namespace LPCM

/-- L'array e' ordinato in senso crescente (ordinamento largo). -/
def Sorted (a : Array Int) : Prop :=
  ∀ i j, i < j → j < a.size → a[i]! ≤ a[j]!

/-- Il valore `t` compare da qualche parte dentro `a`. -/
def Contains (a : Array Int) (t : Int) : Prop :=
  ∃ i, i < a.size ∧ a[i]! = t

/--
  Ricerca binaria **con un bug**.

  Nel ramo "ho guardato troppo in alto" restringe a `[lo, mid-1)`
  invece che a `[lo, mid)`, buttando via l'indice `mid-1`.
-/
def bsearchBuggy (a : Array Int) (t : Int) : Option Nat :=
  go 0 a.size
where
  go (lo hi : Nat) : Option Nat :=
    if _h : lo < hi then
      let mid := (lo + hi) / 2
      if a[mid]! = t then some mid
      else if a[mid]! < t then go (mid + 1) hi
      else go lo (mid - 1)   -- BUG: dovrebbe essere `go lo mid`
    else none
  termination_by hi - lo
  decreasing_by all_goals omega

/-- Ricerca binaria corretta. Identica alla precedente tranne un carattere. -/
def bsearch (a : Array Int) (t : Int) : Option Nat :=
  go 0 a.size
where
  go (lo hi : Nat) : Option Nat :=
    if _h : lo < hi then
      let mid := (lo + hi) / 2
      if a[mid]! = t then some mid
      else if a[mid]! < t then go (mid + 1) hi
      else go lo mid
    else none
  termination_by hi - lo
  decreasing_by all_goals omega

/-- Non trova mai niente. Restituisce sempre `none`. -/
def bsearchNever (_a : Array Int) (_t : Int) : Option Nat := none

end LPCM
