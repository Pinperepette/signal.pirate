/-
  Runner del laboratorio: `lake exe la-prova-che-mente`

  Mostra il divario fra quello che i teoremi promettono
  e quello che la funzione fa davvero.
-/
import LaProvaCheMente

open LPCM

def campione : Array Int := #[1, 3, 5, 7, 9, 11, 13]

def main : IO Unit := do
  IO.println "== La funzione su cui abbiamo dimostrato 5 teoremi di correttezza ==\n"
  IO.println "array ordinato: #[1, 3, 5, 7, 9, 11, 13]"
  IO.println "cerco ogni elemento REALMENTE PRESENTE nell'array:\n"
  IO.println "  target | bsearchBuggy | bsearch (corretta)"
  IO.println "  -------+--------------+-------------------"
  let mut persi := 0
  for t in campione do
    let b := bsearchBuggy campione t
    let c := bsearch campione t
    if b != c then persi := persi + 1
    let mark := if b != c then "   <-- PERSO" else ""
    IO.println s!"  {t}\t | {b}\t| {c}{mark}"
  IO.println ""
  IO.println s!"elementi presenti non trovati: {persi} su {campione.size}"
  IO.println ""
  IO.println "Teoremi dimostrati su questa funzione, tutti col check verde:"
  IO.println "  bsearchBuggy_spec_v1  spec completa      (truffa: sorry)"
  IO.println "  bsearchBuggy_spec_v2  spec completa      (truffa: ipotesi contraddittorie)"
  IO.println "  bsearchBuggy_spec_v3  spec completa      (truffa: solo array vuoti)"
  IO.println "  bsearchBuggy_sound    solo una direzione (nessuna truffa: e' vero)"
  IO.println "  bsearchBuggy_spec_v5  spec completa      (truffa: assioma iniettato)"
