#!/usr/bin/env bash
# Laboratorio: cosa vale davvero un check verde di Lean.
# Uso: ./dimostra.sh
set -uo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.elan/bin:$PATH"

command -v lake >/dev/null || { echo "Lean non trovato. Installa con:"; \
  echo "  curl https://elan.lean-lang.org/elan-init.sh -sSf | sh"; exit 1; }

hr() { printf '%*s\n' 72 '' | tr ' ' '-'; }
titolo() { echo; hr; echo "$1"; hr; }

titolo "1. LA LIBRERIA COMPILA"
lake build 2>&1 | grep -E "warning|error|completed" || true
echo
echo "L'unica diagnostica dell'intero progetto e' il warning su 'sorry'."
echo "Le altre quattro truffe compilano in silenzio assoluto."

titolo "2. COSA FA DAVVERO LA FUNZIONE CHE ABBIAMO 'DIMOSTRATO CORRETTA'"
lake exe la-prova-che-mente 2>/dev/null

titolo "3. SU COSA POGGIANO LE DIMOSTRAZIONI (#print axioms)"
cat > /tmp/lpcm_ax.lean <<'EOF'
import LaProvaCheMente
open LPCM
#print axioms bsearchBuggy_spec_v1
#print axioms bsearchBuggy_spec_v5
#print axioms bsearchBuggy_spec_v2
#print axioms bsearchBuggy_spec_v3
#print axioms bsearchBuggy_sound
#print axioms bsearchNever_sound
#print axioms bsearch_spec
EOF
lake env lean /tmp/lpcm_ax.lean 2>&1 | sed 's/^/  /'
rm -f /tmp/lpcm_ax.lean
cat <<'EOF'

  [propext, Quot.sound] e' la logica di base di Lean: e' il rumore di fondo.
  Lo strumento becca 'sorryAx' e 'oracolo'. Non becca nient'altro.

  La spec ONESTA (bsearch_spec, 103 righe di dimostrazione) e la truffa
  VACUA (bsearchBuggy_spec_v2, 10 righe) hanno la stessa identica impronta.
  Nessun tool al mondo le distingue. Solo chi legge l'enunciato.

EOF

titolo "4. LA SPECIFICA ONESTA RIFIUTA IL CODICE ROTTO"
echo "Stessa dimostrazione di bsearch_complete_aux, applicata a bsearchBuggy:"
echo
lake env lean TentativoFallito.lean 2>&1 | sed 's/^/  /'
cat <<'EOF'

  Fallisce nel case3 -- il ramo che contiene l'off-by-one.
  E nel controesempio compare l'indice colpevole: mid - 1.

  Le quattro truffe accettavano questo codice senza fiatare.
  La specifica giusta lo rifiuta e dice anche dove guardare.

EOF

titolo "5. IL PROTOCOLLO DI CHIUSURA"
cat <<'EOF'
  Tutto quello che segue e' dimostrato in LaProvaCheMente/Chiusura.lean
  ed e' gia' stato verificato dalla build al punto 1.

  CONTROLLO 1 -- IL TESTIMONE (le ipotesi hanno un modello non degenere?)
    testimone_onesta     spec onesta: esiste #[1,3], non degenere      PASSA
    testimone_truffa2    dimostrato che NESSUN array la soddisfa       BOCCIA
    testimone_truffa3    dimostrato che le ipotesi forzano size = 0    BOCCIA

  CONTROLLO 2 -- LA MUTAZIONE (la spec rifiuta il codice rotto?)
    mutazione_onesta     la spec onesta RIFIUTA bsearchBuggy           PASSA
    mutazione_truffa4    la spec indebolita lo ACCETTA                 BOCCIA

  CONTROLLO 3 -- L'IMPLEMENTAZIONE IDIOTA (la spec accetta una funzione vuota?)
    idiota_onesta        la spec onesta RIFIUTA (fun _ _ => none)      PASSA
    bsearchNever_sound   la spec indebolita la ACCETTA                 BOCCIA

  I tre controlli sopra beccano tutte e tre le truffe che #print axioms
  si lasciava scappare. Costano tre righe di Lean a testa.

  CONTROLLO 4 -- LA DETERMINATEZZA (due implementazioni conformi coincidono?)
    base_non_determina           P e Q soddisfano tutte le garanzie
                                 e su un ordine da 60,00 EUR pagano
                                 25,01 contro 30,00                    BOCCIA
    P_non_monotono               la monotonia esclude P da sola        (progresso)
    base_e_monotonia_non_bastano Q e Meta soddisfano tutto + monotonia
                                 e pagano 30,00 contro 15,00           BOCCIA ANCORA
    politica_determina           aggiunta UNA riga di politica,
                                 due funzioni conformi coincidono
                                 ovunque                               PASSA

  Il controllo 4 e' quello che nessuno esegue, ed e' quello che avrebbe
  trovato il problema del rimborso prima del deploy invece che dopo il
  reclamo del cliente.

EOF
