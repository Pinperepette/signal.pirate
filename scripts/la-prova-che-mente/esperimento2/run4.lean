/-!
# Rimborso di un ordine parzialmente reso

## Il problema, e perché non ha una risposta ovvia

Un ordine contiene `N` articoli, con prezzi in centesimi. All'acquisto è stato
applicato un coupon (importo fisso, sottratto dal totale articoli) e pagata una
spedizione di 499 centesimi, gratuita se il totale al netto del coupon raggiunge
i 5000 centesimi. Ora il cliente rende un sottoinsieme degli articoli.

"Quanto rimborsargli" non ha una risposta unica: due cose vanno decise a mano.

1. **Il coupon.** Rimborsare il prezzo pieno degli articoli resi è sbagliato: il
   cliente incasserebbe anche la parte di sconto maturata su quella merce. Con
   `S = 10000`, `coupon = 3000` (pagati 7000) e un reso da 9000, il prezzo pieno
   restituirebbe 9000 — più di quanto il cliente ha versato.
2. **La spedizione.** Se il reso porta l'ordine sotto la soglia, la spedizione
   gratuita non sarebbe più spettata. Riaddebitarla però può far pagare al
   cliente *più* di quanto vale l'articolo reso: ordine da 5000 esatti, si rende
   un articolo da 1 centesimo, e il rimborso diventa −498.

## La regola scelta

Il rimborso è la **differenza fra due stati dello stesso ordine**: quanto è
dovuto per l'ordine com'era, meno quanto è dovuto per quello che il cliente
tiene. Il "dovuto" per un sotto-ordine (`residuo`) è il suo totale al netto del
coupon, più la spedizione già pagata finché resta in mano almeno un articolo.
Detto in una riga, ed è il teorema `conto_finale`: *dopo il reso il cliente ha
pagato esattamente quello che avrebbe pagato ordinando solo ciò che si tiene.*

Ne segue che:

* il coupon si consuma sugli articoli tenuti, e non si può monetizzare con un
  reso parziale (`rimborso_no_leak`);
* la spedizione non viene mai riaddebitata: pagata una volta, resta a carico del
  cliente finché tiene qualcosa e torna indietro quando l'ordine si svuota — per
  questo il rimborso non è mai negativo (`rimborso_nonneg`);
* resi a tappe e reso in blocco danno lo stesso totale (`rimborso_a_tappe`).

## Il prezzo di questa scelta

Scaricare il coupon sugli articoli tenuti è generoso col cliente quando il
coupon è più grande di ciò che resta: chi ordina 10000 con un coupon da 3000 e
rende 9000 riottiene tutti i 7000 versati e tiene gratis merce per 1000
(`#guard` più sotto). È il comportamento giusto se il coupon è uno sconto secco
sull'ordine; se invece il coupon avesse una **soglia minima di spesa**, la
regola corretta sarebbe ripartirlo in proporzione ai prezzi — al costo di
arrotondamenti sul centesimo e della perdita di `rimborso_a_tappe`, perché due
resi successivi arrotonderebbero diversamente da un reso solo. Non essendoci
soglia minima nella specifica, ho scelto la regola esatta e path-independent.

Ipotesi di lavoro, esplicite nei teoremi che le usano: prezzi non negativi,
coupon non negativo, `prezzi.size = resi.size`.
-/

namespace Rimborso

/-! ## Parametri di listino -/

/-- Costo della spedizione, in centesimi. -/
def costoSpedizione : Int := 499

/-- Soglia, sul totale articoli al netto del coupon, oltre la quale si spedisce gratis. -/
def sogliaSpedizioneGratis : Int := 5000

/-! ## Maschere di selezione

Una maschera dice, articolo per articolo, se è selezionato. Tutte le operazioni
scorrono in parallelo prezzi e maschera e si fermano sulla più corta, così una
maschera malformata non può selezionare articoli che non esistono. -/

abbrev Maschera := List Bool

/-- Maschera che seleziona tutti gli `n` articoli. -/
def tutti (n : Nat) : Maschera := List.replicate n true

/-- Maschera che non seleziona nulla. -/
def nessuno (n : Nat) : Maschera := List.replicate n false

/-- Toglie da `m` gli articoli selezionati da `r`. -/
def togli (m r : Maschera) : Maschera := List.zipWith (fun a b => a && !b) m r

/-- Unione di due selezioni. -/
def unisci (r s : Maschera) : Maschera := List.zipWith (fun a b => a || b) r s

/-- Somma dei prezzi degli articoli selezionati. -/
def somma : List Int → Maschera → Int
  | [], _ => 0
  | _, [] => 0
  | p :: ps, b :: bs => (if b then p else 0) + somma ps bs

/-- `true` se la selezione contiene almeno un articolo. -/
def qualcheAttivo : List Int → Maschera → Bool
  | [], _ => false
  | _, [] => false
  | _ :: ps, b :: bs => b || qualcheAttivo ps bs

/-! ## Il modello economico -/

/-- Totale al netto del coupon: il coupon non può spingere il conto sotto zero. -/
def netto (totale coupon : Int) : Int :=
  if totale ≤ coupon then 0 else totale - coupon

/-- Totale articoli dell'ordine originale, al netto del coupon. -/
def nettoOrdine (prezzi : List Int) (coupon : Int) : Int :=
  netto (somma prezzi (tutti prezzi.length)) coupon

/-- La spedizione effettivamente pagata all'acquisto. Dipende solo dall'ordine
originale: una volta pagata, i resi non la rimettono in discussione. -/
def spedizionePagata (prezzi : List Int) (coupon : Int) : Int :=
  if qualcheAttivo prezzi (tutti prezzi.length) then
    (if sogliaSpedizioneGratis ≤ nettoOrdine prezzi coupon then 0 else costoSpedizione)
  else 0

/-- Quanto il cliente ha pagato in tutto. -/
def pagato (prezzi : List Int) (coupon : Int) : Int :=
  nettoOrdine prezzi coupon + spedizionePagata prezzi coupon

/-- Quanto resta dovuto per il sotto-ordine ancora in mano al cliente. -/
def residuo (prezzi : List Int) (attivi : Maschera) (coupon : Int) : Int :=
  netto (somma prezzi attivi) coupon
    + (if qualcheAttivo prezzi attivi then spedizionePagata prezzi coupon else 0)

/-- Rimborso per un reso a partire da un ordine qualsiasi, non necessariamente
quello originale: serve a parlare di resi successivi. -/
def rimborsoGen (prezzi : List Int) (inOrdine resi : Maschera) (coupon : Int) : Int :=
  residuo prezzi inOrdine coupon - residuo prezzi (togli inOrdine resi) coupon

/-- **Il rimborso dovuto al cliente, in centesimi.** -/
def rimborso (prezzi : Array Int) (resi : Array Bool) (coupon : Int) : Int :=
  rimborsoGen prezzi.toList (tutti prezzi.size) resi.toList coupon

/-! ## Qualche caso concreto -/

-- Nessun coupon, nessun reso: non si rimborsa niente.
#guard rimborso #[1000, 2000] #[false, false] 0 = 0

-- Nessun coupon, si rende l'articolo da 2000: si rimborsa esattamente 2000.
#guard rimborso #[1000, 2000] #[false, true] 0 = 2000

-- Ordine da 10000 con coupon 3000: pagati 7000, spedizione gratis. Si rende
-- l'articolo da 6000; sui 4000 tenuti il coupon vale ancora tutto, quindi il
-- cliente resta debitore di 1000 e si rimborsano 6000.
#guard rimborso #[6000, 4000] #[true, false] 3000 = 6000

-- Stesso ordine, reso totale: torna tutto il pagato.
#guard rimborso #[6000, 4000] #[true, true] 3000 = 7000

-- Il caso limite discusso sopra: il coupon (3000) supera i 1000 tenuti, quindi
-- il cliente riprende tutti i 7000 versati e tiene la merce da 1000 gratis.
#guard rimborso #[9000, 1000] #[true, false] 3000 = 7000

-- Ordine da 5000 esatti: spedizione gratis. Si rende un articolo da 1 centesimo.
-- La spedizione non si riaddebita: il rimborso è 1, non -498.
#guard rimborso #[4999, 1] #[false, true] 0 = 1

-- Ordine sotto soglia: 499 di spedizione pagati, restituiti solo a ordine svuotato.
#guard rimborso #[1000] #[false] 0 = 0
#guard rimborso #[1000] #[true] 0 = 1499

-- Un coupon più grande del totale non genera un credito.
#guard rimborso #[1000] #[true] 5000 = 499

-- Ordine vuoto: niente spedizione, niente rimborso.
#guard rimborso #[] #[] 0 = 0

/-! ## Lemmi di calcolo su maschere e somme -/

@[simp] theorem tutti_zero : tutti 0 = [] := rfl
@[simp] theorem tutti_succ (n : Nat) : tutti (n + 1) = true :: tutti n := rfl
@[simp] theorem nessuno_zero : nessuno 0 = [] := rfl
@[simp] theorem nessuno_succ (n : Nat) : nessuno (n + 1) = false :: nessuno n := rfl

@[simp] theorem togli_nil_left (r : Maschera) : togli [] r = [] := rfl
@[simp] theorem togli_nil_right (m : Maschera) : togli m [] = [] := by
  cases m <;> rfl
@[simp] theorem togli_cons (a : Bool) (as : Maschera) (b : Bool) (bs : Maschera) :
    togli (a :: as) (b :: bs) = (a && !b) :: togli as bs := rfl

@[simp] theorem unisci_nil_left (s : Maschera) : unisci [] s = [] := rfl
@[simp] theorem unisci_nil_right (r : Maschera) : unisci r [] = [] := by
  cases r <;> rfl
@[simp] theorem unisci_cons (a : Bool) (as : Maschera) (b : Bool) (bs : Maschera) :
    unisci (a :: as) (b :: bs) = (a || b) :: unisci as bs := rfl

@[simp] theorem somma_nil_left (m : Maschera) : somma [] m = 0 := rfl
@[simp] theorem somma_nil_right (ps : List Int) : somma ps [] = 0 := by
  cases ps <;> rfl
@[simp] theorem somma_cons (p : Int) (ps : List Int) (b : Bool) (bs : Maschera) :
    somma (p :: ps) (b :: bs) = (if b then p else 0) + somma ps bs := rfl

@[simp] theorem qualcheAttivo_nil_left (m : Maschera) : qualcheAttivo [] m = false := rfl
@[simp] theorem qualcheAttivo_nil_right (ps : List Int) : qualcheAttivo ps [] = false := by
  cases ps <;> rfl
@[simp] theorem qualcheAttivo_cons (p : Int) (ps : List Int) (b : Bool) (bs : Maschera) :
    qualcheAttivo (p :: ps) (b :: bs) = (b || qualcheAttivo ps bs) := rfl

/-- Togliere `r` e poi `s` è come togliere `r ∪ s` in un colpo solo.
È l'identità che rende i resi indipendenti dall'ordine in cui avvengono. -/
theorem togli_togli (m r s : Maschera) :
    togli (togli m r) s = togli m (unisci r s) := by
  induction m generalizing r s with
  | nil => simp
  | cons x xs ih =>
    cases r with
    | nil => simp
    | cons y ys =>
      cases s with
      | nil => simp
      | cons z zs =>
        simp only [togli_cons, unisci_cons, ih ys zs, List.cons.injEq, and_true]
        cases x <;> cases y <;> cases z <;> rfl

/-- Togliere una selezione vuota lascia la maschera com'è. -/
theorem togli_nessuno (m : Maschera) (n : Nat) (h : m.length ≤ n) :
    togli m (nessuno n) = m := by
  induction m generalizing n with
  | nil => simp
  | cons x xs ih =>
    cases n with
    | zero => simp at h
    | succ k =>
      have hk : xs.length ≤ k := by simpa using h
      simp [ih k hk]

/-- Rendere tutto svuota l'ordine. -/
theorem togli_tutti_tutti (n : Nat) : togli (tutti n) (tutti n) = nessuno n := by
  induction n with
  | zero => simp
  | succ k ih => simp [ih]

@[simp] theorem somma_nessuno (ps : List Int) (n : Nat) : somma ps (nessuno n) = 0 := by
  induction ps generalizing n with
  | nil => simp
  | cons p ps ih => cases n with
    | zero => simp
    | succ k => simp [ih k]

@[simp] theorem qualcheAttivo_nessuno (ps : List Int) (n : Nat) :
    qualcheAttivo ps (nessuno n) = false := by
  induction ps generalizing n with
  | nil => simp
  | cons p ps ih => cases n with
    | zero => simp
    | succ k => simp [ih k]

/-- Con prezzi non negativi, nessuna selezione ha totale negativo. -/
theorem somma_nonneg (ps : List Int) (hp : ∀ p ∈ ps, 0 ≤ p) (m : Maschera) :
    0 ≤ somma ps m := by
  induction ps generalizing m with
  | nil => simp
  | cons p ps ih =>
    cases m with
    | nil => simp
    | cons b bs =>
      have h0 : 0 ≤ p := hp p (by simp)
      have hrest := ih (fun q hq => hp q (by simp [hq])) bs
      simp only [somma_cons]
      split <;> omega

/-- Ciò che si tiene più ciò che si rende fa l'ordine intero. -/
theorem somma_tenuti_add_resi (ps : List Int) (r : Maschera) (h : ps.length = r.length) :
    somma ps (togli (tutti ps.length) r) + somma ps r = somma ps (tutti ps.length) := by
  induction ps generalizing r with
  | nil => simp
  | cons p ps ih =>
    cases r with
    | nil => simp at h
    | cons b bs =>
      have hlen : ps.length = bs.length := by simpa using h
      have hih := ih bs hlen
      simp only [List.length_cons, tutti_succ, togli_cons, somma_cons, Bool.true_and]
      cases b <;> simp <;> omega

/-- Togliere articoli non fa crescere il totale, se i prezzi non sono negativi. -/
theorem somma_togli_le (ps : List Int) (hp : ∀ p ∈ ps, 0 ≤ p) (m r : Maschera) :
    somma ps (togli m r) ≤ somma ps m := by
  induction ps generalizing m r with
  | nil => simp
  | cons p ps ih =>
    have h0 : 0 ≤ p := hp p (by simp)
    have hp' : ∀ q ∈ ps, 0 ≤ q := fun q hq => hp q (by simp [hq])
    cases m with
    | nil => simp
    | cons a as =>
      cases r with
      | nil =>
        have hrest : (0 : Int) ≤ somma ps as := somma_nonneg ps hp' as
        simp only [togli_nil_right, somma_nil_right, somma_cons]
        split <;> omega
      | cons b bs =>
        have hrest := ih hp' as bs
        simp only [togli_cons, somma_cons]
        cases a <;> cases b <;> simp <;> omega

/-- Se dopo il reso resta qualcosa, qualcosa c'era anche prima. -/
theorem qualcheAttivo_togli (ps : List Int) (m r : Maschera) :
    qualcheAttivo ps (togli m r) = true → qualcheAttivo ps m = true := by
  induction ps generalizing m r with
  | nil => simp
  | cons p ps ih =>
    cases m with
    | nil => simp
    | cons a as =>
      cases r with
      | nil => simp
      | cons b bs =>
        simp only [togli_cons, qualcheAttivo_cons, Bool.or_eq_true]
        intro h
        rcases h with h | h
        · cases a <;> simp_all
        · exact Or.inr (ih as bs h)

/-! ## Proprietà elementari del modello -/

theorem spedizionePagata_nonneg (ps : List Int) (c : Int) : 0 ≤ spedizionePagata ps c := by
  simp only [spedizionePagata, costoSpedizione]
  split
  · split <;> decide
  · decide

theorem netto_nonneg (t c : Int) : 0 ≤ netto t c := by
  simp only [netto]; split <;> omega

theorem netto_mono (a b c : Int) (h : a ≤ b) : netto a c ≤ netto b c := by
  simp only [netto]; split <;> split <;> omega

/-- La quota di spedizione a carico di un sotto-ordine: c'è finché l'ordine non si svuota. -/
theorem quotaSped_nonneg (ps : List Int) (m : Maschera) (c : Int) :
    0 ≤ (if qualcheAttivo ps m then spedizionePagata ps c else 0) := by
  have := spedizionePagata_nonneg ps c
  split <;> omega

theorem quotaSped_togli_le (ps : List Int) (m r : Maschera) (c : Int) :
    (if qualcheAttivo ps (togli m r) then spedizionePagata ps c else 0)
      ≤ (if qualcheAttivo ps m then spedizionePagata ps c else 0) := by
  have hs := spedizionePagata_nonneg ps c
  by_cases h : qualcheAttivo ps (togli m r) = true
  · rw [if_pos h, if_pos (qualcheAttivo_togli ps m r h)]
    omega
  · rw [if_neg h]
    split <;> omega

theorem residuo_nonneg (ps : List Int) (m : Maschera) (c : Int) : 0 ≤ residuo ps m c := by
  have h1 := netto_nonneg (somma ps m) c
  have h2 := quotaSped_nonneg ps m c
  simp only [residuo]
  omega

/-- **Togliere articoli non fa mai crescere il dovuto.** È il cuore di tutte le
disuguaglianze che seguono, ed è il punto in cui serve che i prezzi siano ≥ 0. -/
theorem residuo_togli_le (ps : List Int) (hp : ∀ p ∈ ps, 0 ≤ p) (m r : Maschera) (c : Int) :
    residuo ps (togli m r) c ≤ residuo ps m c := by
  have h1 := netto_mono _ _ c (somma_togli_le ps hp m r)
  have h2 := quotaSped_togli_le ps m r c
  simp only [residuo]
  omega

/-- Sull'ordine intero, il residuo è esattamente quanto il cliente ha pagato. -/
theorem residuo_tutti (ps : List Int) (c : Int) :
    residuo ps (tutti ps.length) c = pagato ps c := by
  simp only [residuo, pagato, nettoOrdine, spedizionePagata]
  split <;> rfl

/-- A ordine svuotato non resta nulla da pagare, se il coupon non è negativo. -/
theorem residuo_nessuno (ps : List Int) (n : Nat) (c : Int) (hc : 0 ≤ c) :
    residuo ps (nessuno n) c = 0 := by
  have h : netto 0 c = 0 := by simp only [netto]; split <;> omega
  simp [residuo, h]

/-- Forma esplicita del residuo quando il cliente tiene ancora qualcosa. -/
theorem residuo_di_attivo (ps : List Int) (m : Maschera) (c : Int)
    (h : qualcheAttivo ps m = true) :
    residuo ps m c = netto (somma ps m) c + spedizionePagata ps c := by
  simp only [residuo]
  rw [if_pos h]

/-! ## I teoremi di correttezza -/

/-- **La specifica, in una riga.** Quello che il cliente ha pagato al netto del
rimborso è esattamente quanto costerebbe l'ordine dei soli articoli che tiene,
valutato con le stesse regole (coupon e spedizione già pagata). -/
theorem conto_finale (prezzi : Array Int) (resi : Array Bool) (c : Int) :
    pagato prezzi.toList c - rimborso prezzi resi c
      = residuo prezzi.toList (togli (tutti prezzi.size) resi.toList) c := by
  have hs : prezzi.toList.length = prezzi.size := by simp
  have ht := residuo_tutti prezzi.toList c
  rw [hs] at ht
  simp only [rimborso, rimborsoGen, ht]
  omega

/-- **Se non si rende nulla, non si rimborsa nulla.** -/
theorem rimborso_nessun_reso (prezzi : Array Int) (c : Int) :
    rimborso prezzi (Array.replicate prezzi.size false) c = 0 := by
  simp only [rimborso, rimborsoGen, Array.toList_replicate,
    show List.replicate prezzi.size false = nessuno prezzi.size from rfl]
  rw [togli_nessuno _ _ (by simp [tutti])]
  omega

/-- **Se si rende tutto, si rimborsa esattamente quanto pagato**, spedizione compresa. -/
theorem rimborso_reso_totale (prezzi : Array Int) (c : Int) (hc : 0 ≤ c) :
    rimborso prezzi (Array.replicate prezzi.size true) c = pagato prezzi.toList c := by
  have hs : prezzi.toList.length = prezzi.size := by simp
  simp only [rimborso, rimborsoGen, Array.toList_replicate,
    show List.replicate prezzi.size true = tutti prezzi.size from rfl]
  rw [togli_tutti_tutti, residuo_nessuno _ _ _ hc, ← hs, residuo_tutti]
  omega

/-- **Il rimborso non è mai negativo**: rendere merce non può trasformarsi in un
addebito, nemmeno quando il reso porta l'ordine sotto la soglia di spedizione
gratuita. È il punto 2 della discussione in testa al file. -/
theorem rimborso_nonneg (prezzi : Array Int) (resi : Array Bool) (c : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p) :
    0 ≤ rimborso prezzi resi c := by
  have h := residuo_togli_le prezzi.toList hp (tutti prezzi.size) resi.toList c
  simp only [rimborso, rimborsoGen]
  omega

/-- **Non si rimborsa mai più di quanto il cliente ha pagato.** -/
theorem rimborso_le_pagato (prezzi : Array Int) (resi : Array Bool) (c : Int) :
    rimborso prezzi resi c ≤ pagato prezzi.toList c := by
  have hs : prezzi.toList.length = prezzi.size := by simp
  have h0 := residuo_nonneg prezzi.toList (togli (tutti prezzi.size) resi.toList) c
  have ht := residuo_tutti prezzi.toList c
  rw [hs] at ht
  simp only [rimborso, rimborsoGen, ht]
  omega

/-- **Il coupon non si può incassare.** Finché il cliente tiene almeno un articolo,
il rimborso non supera il prezzo di listino della merce resa: lo sconto resta
attaccato all'ordine invece di essere monetizzato con un reso parziale.
È il punto 1 della discussione in testa al file. -/
theorem rimborso_no_leak (prezzi : Array Int) (resi : Array Bool) (c : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p)
    (hlen : prezzi.toList.length = resi.toList.length)
    (hq : qualcheAttivo prezzi.toList (togli (tutti prezzi.size) resi.toList) = true) :
    rimborso prezzi resi c ≤ somma prezzi.toList resi.toList := by
  have hs : prezzi.toList.length = prezzi.size := by simp
  have hsplit := somma_tenuti_add_resi prezzi.toList resi.toList hlen
  rw [hs] at hsplit
  have hR := somma_nonneg prezzi.toList hp resi.toList
  have hatt := qualcheAttivo_togli _ _ _ hq
  simp only [rimborso, rimborsoGen, residuo_di_attivo _ _ c hq,
    residuo_di_attivo _ _ c hatt, netto]
  split <;> split <;> omega

/-- **Rendere di più non rimborsa di meno.** -/
theorem rimborso_monotono (prezzi : Array Int) (r s : Array Bool) (c : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p) :
    rimborso prezzi r c
      ≤ rimborsoGen prezzi.toList (tutti prezzi.size) (unisci r.toList s.toList) c := by
  have h := residuo_togli_le prezzi.toList hp
    (togli (tutti prezzi.size) r.toList) s.toList c
  rw [togli_togli] at h
  simp only [rimborso, rimborsoGen]
  omega

/-- **I resi a tappe non cambiano il conto.** Rendere `r` e poi `s` rimborsa in
totale esattamente quanto rendere `r ∪ s` in una volta sola: il cliente non
guadagna né perde niente scegliendo come spezzare il reso, e in particolare non
può spremere due volte la soglia di spedizione gratuita. -/
theorem rimborso_a_tappe (prezzi : List Int) (m r s : Maschera) (c : Int) :
    rimborsoGen prezzi m r c + rimborsoGen prezzi (togli m r) s c
      = rimborsoGen prezzi m (unisci r s) c := by
  simp only [rimborsoGen, togli_togli]
  omega

/-- Lo stesso, a partire dalla funzione pubblica: il primo reso è un `rimborso`. -/
theorem rimborso_a_tappe' (prezzi : Array Int) (r s : Array Bool) (c : Int) :
    rimborso prezzi r c
        + rimborsoGen prezzi.toList (togli (tutti prezzi.size) r.toList) s.toList c
      = rimborsoGen prezzi.toList (tutti prezzi.size) (unisci r.toList s.toList) c :=
  rimborso_a_tappe prezzi.toList (tutti prezzi.size) r.toList s.toList c

end Rimborso
