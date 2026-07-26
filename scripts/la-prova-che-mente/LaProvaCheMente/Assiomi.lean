/-
  LA GERARCHIA DI RILEVABILITA'.

  Lean sa dirti su cosa poggia davvero una dimostrazione: `#print axioms`.
  Questo file esegue quel comando su tutte le truffe e mostra il risultato.

  La domanda a cui rispondere e': quali truffe becca uno strumento,
  e quali richiedono un essere umano che legge l'enunciato?
-/
import LaProvaCheMente.Truffe

namespace LPCM

/- ------------------------------------------------------------------ -/
/- TRUFFA 5 — l'assioma iniettato                                       -/
/- ------------------------------------------------------------------ -/

/--
  A differenza di `sorry`, dichiarare un assioma **non produce nessun
  warning**. Il file compila in perfetto silenzio.
-/
axiom oracolo : ∀ (a : Array Int) (t : Int), FullSpec bsearchBuggy a t

theorem bsearchBuggy_spec_v5 (a : Array Int) (t : Int) :
    FullSpec bsearchBuggy a t := oracolo a t

/- ------------------------------------------------------------------ -/
/- IL VERDETTO                                                          -/
/- ------------------------------------------------------------------ -/

section Verdetto

-- Le tre costanti qui sotto (propext, Classical.choice, Quot.sound) sono
-- gli assiomi standard di Lean. Vederle e' normale: sono la logica di base.
-- Quello che conta e' cosa compare OLTRE a loro.

/-- info: 'LPCM.bsearchBuggy_spec_v1' depends on axioms: [propext, sorryAx, Quot.sound] -/
#guard_msgs in
#print axioms bsearchBuggy_spec_v1        -- TRUFFA 1: BECCATA (sorryAx)

/-- info: 'LPCM.bsearchBuggy_spec_v5' depends on axioms: [propext, oracolo, Quot.sound] -/
#guard_msgs in
#print axioms bsearchBuggy_spec_v5        -- TRUFFA 5: BECCATA (oracolo)

/-- info: 'LPCM.bsearchBuggy_spec_v2' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms bsearchBuggy_spec_v2        -- TRUFFA 2: PULITA. Ed e' vacua.

/-- info: 'LPCM.bsearchBuggy_spec_v3' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms bsearchBuggy_spec_v3        -- TRUFFA 3: PULITA. E parla solo di array vuoti.

/-- info: 'LPCM.bsearchBuggy_sound' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms bsearchBuggy_sound          -- TRUFFA 4: PULITA. Ed e' su codice rotto al 43%.

/-
  E qui la cosa piu' brutta di tutto il laboratorio.

  La funzione che non fa NIENTE ha l'impronta assiomatica **piu' pulita
  di tutte**: le manca perfino `Quot.sound`. Se ordinassi questi teoremi
  per purezza delle fondamenta logiche, vincerebbe `fun _ _ => none`.
-/

/-- info: 'LPCM.bsearchNever_sound' depends on axioms: [propext] -/
#guard_msgs in
#print axioms bsearchNever_sound

end Verdetto

/-
  RISULTATO.

    truffa                      #print axioms     serve un umano?
    ------------------------------------------------------------
    1. sorry                    BECCATA           no
    5. assioma iniettato        BECCATA           no
    2. ipotesi contraddittorie  pulita            SI
    3. precondizione degenere   pulita            SI
    4. teorema indebolito       pulita            SI

  Le due truffe che uno strumento intercetta sono le due che nessuno
  farebbe apposta. Le tre che restano in piedi sono esattamente quelle
  che richiedono di leggere l'enunciato e chiedersi se dice quello che
  volevi dire.

  La verifica formale non elimina la lettura. La comprime.
-/

end LPCM
