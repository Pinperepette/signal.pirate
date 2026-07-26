/-!
# Rimborso di un reso parziale

Un cliente ha comprato `N` articoli, ha usato un coupon a importo fisso e ha
pagato la spedizione se il totale al netto del coupon non arrivava alla soglia
della spedizione gratuita. Ora rende un sottoinsieme degli articoli: quanto gli
si deve?

## La regola scelta

La specifica dice come si calcola il *prezzo di un ordine*, non come si spalma
il coupon sugli articoli resi: quel pezzo è ambiguo. Qui la regola è:

> il cliente deve trovarsi esattamente nella situazione in cui si sarebbe
> trovato se avesse ordinato fin dall'inizio solo gli articoli che tiene,
> con lo stesso coupon — ma senza mai dover ridare indietro dei soldi.

Cioè `rimborso = max (pagato − costo dell'ordine dei soli articoli tenuti) 0`.

Due conseguenze, entrambe volute e dimostrate sotto:

* se il reso fa scendere l'ordine sotto la soglia della spedizione gratuita, il
  rimborso è ridotto delle spese di spedizione, che adesso sono dovute
  (`rimborso_sotto_soglia`);
* il `max … 0` serve perché senza di esso quella riduzione potrebbe rendere il
  rimborso negativo (rendere un articolo da 1 centesimo che fa perdere la
  spedizione gratis): il negozio non chiede mai soldi al cliente per un reso
  (`rimborso_nonneg`).

Il coupon resta interamente a beneficio dell'ordine residuo: chi rende una
parte della merce non si vede riscalare il coupon in proporzione. È una scelta
a favore del cliente, e va notato che rende possibile tenere un solo articolo
da pochi centesimi conservando tutto lo sconto. Una ripartizione pro-quota del
coupon richiederebbe una divisione con arrotondamento (e la regola su chi si
prende il centesimo di resto): è un'altra specifica, non questa.
-/

namespace Rimborso

/-! ## Parametri del listino -/

/-- Spese di spedizione, in centesimi. -/
def speseSpedizione : Int := 499

/-- Soglia, in centesimi e sul totale al netto del coupon, oltre la quale la
spedizione è gratuita. -/
def sogliaGratis : Int := 5000

/-! ## Costo di un ordine -/

/-- Totale degli articoli al netto del coupon. Il coupon non può spingere il
totale sotto zero: al massimo lo azzera. -/
def netto (subtotale coupon : Int) : Int :=
  max (subtotale - coupon) 0

/-- Costo complessivo di un ordine: il totale al netto del coupon, più la
spedizione se quel totale non raggiunge la soglia. Un ordine senza articoli
(`vuoto = true`) costa 0: non si spedisce il nulla. -/
def costoOrdine (subtotale coupon : Int) (vuoto : Bool) : Int :=
  if vuoto then 0
  else netto subtotale coupon +
    (if sogliaGratis ≤ netto subtotale coupon then 0 else speseSpedizione)

/-! ## Somme sugli articoli -/

/-- Somma dei prezzi degli articoli selezionati da `sel`. -/
def sommaSel : List Int → List Bool → Int
  | [], _ => 0
  | _, [] => 0
  | p :: ps, s :: ss => (if s then p else 0) + sommaSel ps ss

/-- Somma di tutti i prezzi. -/
def somma : List Int → Int
  | [] => 0
  | p :: ps => p + somma ps

/-! ## La funzione di rimborso -/

/-- Quanto il cliente ha effettivamente pagato al momento dell'acquisto. -/
def pagato (ps : List Int) (coupon : Int) : Int :=
  costoOrdine (somma ps) coupon ps.isEmpty

/-- Quanto avrebbe pagato se avesse ordinato solo gli articoli che tiene.
`rs.all id` è vero quando rende tutto (o quando l'ordine era vuoto): in quel
caso l'ordine residuo è vuoto. -/
def daPagareTenuti (ps : List Int) (rs : List Bool) (coupon : Int) : Int :=
  costoOrdine (sommaSel ps (rs.map (fun b => !b))) coupon (rs.all id)

/-- Versione su liste, dove si fanno le dimostrazioni. -/
def rimborsoL (ps : List Int) (rs : List Bool) (coupon : Int) : Int :=
  max (pagato ps coupon - daPagareTenuti ps rs coupon) 0

/-- Importo da rimborsare, in centesimi. `prezzi[i]` è il prezzo dell'articolo
`i`, `resi[i] = true` significa che l'articolo `i` viene reso; si assume
`prezzi.size = resi.size`. -/
def rimborso (prezzi : Array Int) (resi : Array Bool) (coupon : Int) : Int :=
  rimborsoL prezzi.toList resi.toList coupon

/-! ## Esempi eseguibili -/

-- Nessun reso: nessun rimborso.
#guard rimborso #[3000, 2500] #[false, false] 0 = 0

-- Reso totale: torna indietro tutto il pagato (5500, spedizione gratis).
#guard rimborso #[3000, 2500] #[true, true] 0 = 5500

-- Reso parziale che fa perdere la spedizione gratuita: l'articolo reso vale
-- 2500 ma il rimborso è 2500 - 499, perché ora la spedizione è dovuta.
#guard rimborso #[3000, 2500] #[false, true] 0 = 2001

-- Sopra soglia anche dopo il reso: si riprende esattamente il prezzo del reso.
#guard rimborso #[6000, 2500] #[false, true] 0 = 2500

-- Il coupon resta all'ordine residuo.
#guard rimborso #[6000, 2500] #[false, true] 1000 = 2500

-- Il caso in cui il `max … 0` morde: senza clamp il rimborso sarebbe -498.
#guard rimborso #[4999, 1] #[false, true] 0 = 0

/-! ## Lemmi di base -/

theorem netto_nonneg (s c : Int) : 0 ≤ netto s c := by
  simp only [netto]
  omega

theorem costoOrdine_nonneg (s c : Int) (v : Bool) : 0 ≤ costoOrdine s c v := by
  simp only [costoOrdine, speseSpedizione]
  have h := netto_nonneg s c
  split
  · omega
  · split <;> omega

theorem pagato_nonneg (ps : List Int) (c : Int) : 0 ≤ pagato ps c :=
  costoOrdine_nonneg _ _ _

theorem daPagareTenuti_nonneg (ps : List Int) (rs : List Bool) (c : Int) :
    0 ≤ daPagareTenuti ps rs c :=
  costoOrdine_nonneg _ _ _

/-- Un ordine il cui totale al netto del coupon arriva alla soglia costa
esattamente quel totale: spedizione gratis. -/
theorem costoOrdine_sopra_soglia {s c : Int} (h : sogliaGratis ≤ s - c) :
    costoOrdine s c false = s - c := by
  have hn : netto s c = s - c := by
    simp only [netto, sogliaGratis] at *
    omega
  simp only [costoOrdine, hn, if_neg (Bool.false_ne_true), if_pos h]
  omega

/-- Un ordine non vuoto il cui totale al netto del coupon resta sotto la soglia
paga la spedizione. -/
theorem costoOrdine_sotto_soglia {s c : Int} (h0 : 0 ≤ s - c)
    (h : s - c < sogliaGratis) :
    costoOrdine s c false = s - c + speseSpedizione := by
  have hn : netto s c = s - c := by
    simp only [netto]
    omega
  have hlt : ¬ (sogliaGratis ≤ s - c) := by omega
  simp only [costoOrdine, hn, if_neg (Bool.false_ne_true), if_neg hlt]

theorem costoOrdine_vuoto (s c : Int) : costoOrdine s c true = 0 := by
  simp [costoOrdine]

/-! ## Lemmi sulle somme -/

theorem sommaSel_nil (rs : List Bool) : sommaSel [] rs = 0 := by
  cases rs <;> rfl

/-- Se non è selezionato niente, la somma selezionata è zero. -/
theorem sommaSel_eq_zero {ps : List Int} {ss : List Bool}
    (h : ∀ b ∈ ss, b = false) : sommaSel ps ss = 0 := by
  induction ps generalizing ss with
  | nil => exact sommaSel_nil ss
  | cons p ps ih =>
    cases ss with
    | nil => rfl
    | cons s ss =>
      have hs : s = false := h s (List.mem_cons_self ..)
      have hss : ∀ b ∈ ss, b = false := fun b hb => h b (List.mem_cons_of_mem _ hb)
      simp [sommaSel, hs, ih hss]

/-- Se è selezionato tutto, la somma selezionata è la somma di tutti i prezzi
(purché le due liste abbiano la stessa lunghezza). -/
theorem sommaSel_eq_somma {ps : List Int} {ss : List Bool}
    (hl : ps.length = ss.length) (h : ∀ b ∈ ss, b = true) :
    sommaSel ps ss = somma ps := by
  induction ps generalizing ss with
  | nil => rfl
  | cons p ps ih =>
    cases ss with
    | nil => simp at hl
    | cons s ss =>
      have hs : s = true := h s (List.mem_cons_self ..)
      have hss : ∀ b ∈ ss, b = true := fun b hb => h b (List.mem_cons_of_mem _ hb)
      have hl' : ps.length = ss.length := by simpa using hl
      simp [sommaSel, somma, hs, ih hl' hss]

/-- **Complementarità**: quello che rendi più quello che tieni fa il totale
dell'ordine. È il lemma che tiene in piedi tutto il resto. -/
theorem sommaSel_compl {ps : List Int} {rs : List Bool}
    (hl : ps.length = rs.length) :
    sommaSel ps rs + sommaSel ps (rs.map (fun b => !b)) = somma ps := by
  induction ps generalizing rs with
  | nil => simp [sommaSel_nil, somma]
  | cons p ps ih =>
    cases rs with
    | nil => simp at hl
    | cons r rs =>
      have hl' : ps.length = rs.length := by simpa using hl
      have := ih hl'
      cases r <;> simp [sommaSel, somma] <;> omega

/-- Se il cliente rende tutto, non tiene niente. -/
theorem tenuto_eq_zero_of_tutto_reso {ps : List Int} {rs : List Bool}
    (h : rs.all id = true) : sommaSel ps (rs.map (fun b => !b)) = 0 := by
  apply sommaSel_eq_zero
  intro b hb
  simp only [List.mem_map] at hb
  obtain ⟨a, ha, rfl⟩ := hb
  have : a = true := by
    have := List.all_eq_true.mp h a ha
    simpa using this
  simp [this]

/-- Se il cliente tiene qualcosa (di valore non nullo), allora non ha reso
tutto e l'ordine non era vuoto. -/
theorem non_tutto_reso_of_tenuto_ne_zero {ps : List Int} {rs : List Bool}
    (h : sommaSel ps (rs.map (fun b => !b)) ≠ 0) :
    rs.all id = false ∧ ps.isEmpty = false := by
  constructor
  · cases hall : rs.all id with
    | false => rfl
    | true => exact absurd (tenuto_eq_zero_of_tutto_reso hall) h
  · cases ps with
    | nil => exact absurd (sommaSel_nil _) h
    | cons _ _ => rfl

/-! ## Teoremi di correttezza -/

/-- **Il rimborso non è mai negativo**: per un reso il cliente non tira mai
fuori soldi. -/
theorem rimborso_nonneg (prezzi : Array Int) (resi : Array Bool) (coupon : Int) :
    0 ≤ rimborso prezzi resi coupon := by
  simp only [rimborso, rimborsoL]
  omega

/-- **Non si rimborsa più di quanto incassato**: il rimborso non supera mai
quello che il cliente aveva pagato. -/
theorem rimborso_le_pagato (prezzi : Array Int) (resi : Array Bool) (coupon : Int) :
    rimborso prezzi resi coupon ≤ pagato prezzi.toList coupon := by
  have h1 := pagato_nonneg prezzi.toList coupon
  have h2 := daPagareTenuti_nonneg prezzi.toList resi.toList coupon
  simp only [rimborso, rimborsoL]
  omega

/-- **Nessun reso, nessun rimborso.** -/
theorem rimborso_nessun_reso {prezzi : Array Int} {resi : Array Bool} {coupon : Int}
    (hl : prezzi.size = resi.size) (h : ∀ b ∈ resi, b = false) :
    rimborso prezzi resi coupon = 0 := by
  have hl' : prezzi.toList.length = resi.toList.length := by simpa using hl
  have h' : ∀ b ∈ resi.toList, b = false := by
    intro b hb; exact h b (by simpa using hb)
  -- chi non rende niente tiene tutto…
  have htenuto : sommaSel prezzi.toList (resi.toList.map (fun b => !b))
      = somma prezzi.toList := by
    apply sommaSel_eq_somma (by simpa using hl')
    intro b hb
    simp only [List.mem_map] at hb
    obtain ⟨a, ha, rfl⟩ := hb
    simp [h' a ha]
  -- …e l'ordine residuo è vuoto esattamente quando lo era quello di partenza.
  have hvuoto : resi.toList.all id = prezzi.toList.isEmpty := by
    cases hp : prezzi.toList with
    | nil =>
      have : resi.toList = [] := by
        have := hl'; rw [hp] at this; simpa using (List.eq_nil_of_length_eq_zero this.symm)
      simp [this]
    | cons p ps =>
      have hr : resi.toList ≠ [] := by
        intro hnil
        rw [hp, hnil] at hl'
        simp at hl'
      match hrs : resi.toList with
      | [] => exact absurd hrs hr
      | r :: rs =>
        have : r = false := h' r (by rw [hrs]; exact List.mem_cons_self ..)
        simp [this]
  simp only [rimborso, rimborsoL, pagato, daPagareTenuti, htenuto, hvuoto]
  omega

/-- **Reso totale, rimborso totale**: torna indietro tutto quello che il
cliente ha pagato, spedizione inclusa. -/
theorem rimborso_tutto_reso {prezzi : Array Int} {resi : Array Bool} {coupon : Int}
    (h : ∀ b ∈ resi, b = true) :
    rimborso prezzi resi coupon = pagato prezzi.toList coupon := by
  have h' : resi.toList.all id = true := by
    apply List.all_eq_true.mpr
    intro b hb
    have : b = true := h b (by simpa using hb)
    simp [this]
  have htenuto := tenuto_eq_zero_of_tutto_reso (ps := prezzi.toList) h'
  have hp := pagato_nonneg prezzi.toList coupon
  simp only [rimborso, rimborsoL, daPagareTenuti, htenuto, h', costoOrdine_vuoto]
  omega

/-- **Il caso normale**: se i prezzi resi non sono negativi e l'ordine residuo
resta comunque sopra la soglia della spedizione gratuita, il cliente riprende
esattamente il prezzo di listino di quello che ha reso — né più né meno, e il
coupon non entra nel conto. -/
theorem rimborso_sopra_soglia {prezzi : Array Int} {resi : Array Bool} {coupon : Int}
    (hl : prezzi.size = resi.size)
    (hcoupon : 0 ≤ coupon)
    (hresi : 0 ≤ sommaSel prezzi.toList resi.toList)
    (hsoglia : sogliaGratis ≤ sommaSel prezzi.toList (resi.toList.map (fun b => !b)) - coupon) :
    rimborso prezzi resi coupon = sommaSel prezzi.toList resi.toList := by
  have hl' : prezzi.toList.length = resi.toList.length := by simpa using hl
  have hcompl := sommaSel_compl hl'
  have hsg : (5000 : Int) ≤ sommaSel prezzi.toList (resi.toList.map (fun b => !b)) - coupon := by
    simpa [sogliaGratis] using hsoglia
  -- l'ordine residuo vale almeno la soglia, quindi non è vuoto
  have hKne : sommaSel prezzi.toList (resi.toList.map (fun b => !b)) ≠ 0 := by omega
  obtain ⟨hall, hemp⟩ := non_tutto_reso_of_tenuto_ne_zero (ps := prezzi.toList) hKne
  -- anche l'ordine completo era sopra soglia, perché i resi valgono ≥ 0
  have htot : sogliaGratis ≤ somma prezzi.toList - coupon := by
    simp only [sogliaGratis]
    omega
  simp only [rimborso, rimborsoL, pagato, daPagareTenuti, hemp, hall,
    costoOrdine_sopra_soglia htot, costoOrdine_sopra_soglia hsoglia]
  omega

/-- **Il prezzo della soglia**: se invece il reso fa scendere l'ordine residuo
sotto la soglia (mentre l'ordine originale era sopra), il rimborso è il prezzo
dei resi meno le spese di spedizione, che adesso sono dovute — e comunque mai
sotto zero. -/
theorem rimborso_sotto_soglia {prezzi : Array Int} {resi : Array Bool} {coupon : Int}
    (hl : prezzi.size = resi.size)
    (hall : resi.toList.all id = false)
    (hemp : prezzi.toList.isEmpty = false)
    (htot : sogliaGratis ≤ somma prezzi.toList - coupon)
    (h0 : 0 ≤ sommaSel prezzi.toList (resi.toList.map (fun b => !b)) - coupon)
    (hsoglia : sommaSel prezzi.toList (resi.toList.map (fun b => !b)) - coupon < sogliaGratis) :
    rimborso prezzi resi coupon =
      max (sommaSel prezzi.toList resi.toList - speseSpedizione) 0 := by
  have hl' : prezzi.toList.length = resi.toList.length := by simpa using hl
  have hcompl := sommaSel_compl hl'
  simp only [rimborso, rimborsoL, pagato, daPagareTenuti, hemp, hall,
    costoOrdine_sopra_soglia htot, costoOrdine_sotto_soglia h0 hsoglia]
  omega

/-- Conseguenza diretta: il rimborso non supera mai il prezzo di listino di
quello che è stato reso (il negozio non ci rimette sul coupon più di quanto
abbia scontato). Vale quando l'ordine originale godeva della spedizione
gratuita. -/
theorem rimborso_le_resi {prezzi : Array Int} {resi : Array Bool} {coupon : Int}
    (hl : prezzi.size = resi.size)
    (hcoupon : 0 ≤ coupon)
    (hresi : 0 ≤ sommaSel prezzi.toList resi.toList)
    (hemp : prezzi.toList.isEmpty = false)
    (htot : sogliaGratis ≤ somma prezzi.toList - coupon) :
    rimborso prezzi resi coupon ≤ sommaSel prezzi.toList resi.toList := by
  have hl' : prezzi.toList.length = resi.toList.length := by simpa using hl
  have hcompl := sommaSel_compl hl'
  -- il costo dell'ordine residuo è almeno il suo totale al netto del coupon
  have hnet : sommaSel prezzi.toList (resi.toList.map (fun b => !b)) - coupon
      ≤ netto (sommaSel prezzi.toList (resi.toList.map (fun b => !b))) coupon := by
    simp only [netto]; omega
  have hsp : (0:Int) ≤ speseSpedizione := by simp only [speseSpedizione]; omega
  simp only [rimborso, rimborsoL, pagato, daPagareTenuti,
    costoOrdine_sopra_soglia htot, hemp]
  cases hallv : resi.toList.all id with
  | true =>
    have hK := tenuto_eq_zero_of_tutto_reso (ps := prezzi.toList) hallv
    simp only [costoOrdine_vuoto]
    omega
  | false =>
    simp only [costoOrdine, if_neg (Bool.false_ne_true)]
    split <;> omega

/-! ## Le ipotesi non sono vuote

I due teoremi condizionali sopra sarebbero inutili se nessun ordine reale
soddisfacesse le loro ipotesi. Qui si istanziano su casi concreti: le ipotesi
si chiudono per calcolo e la conclusione dà il numero atteso. -/

-- Ordine da 8500 con coupon 1000: resta sopra soglia anche dopo il reso,
-- e infatti si riprende esattamente il prezzo dell'articolo reso.
example : rimborso #[6000, 2500] #[false, true] 1000 = 2500 :=
  rimborso_sopra_soglia (prezzi := #[6000, 2500]) (resi := #[false, true])
    (coupon := 1000) (by decide) (by decide) (by decide) (by decide)

-- Ordine da 5500 senza coupon: il reso lo fa scendere sotto soglia, quindi
-- dal prezzo del reso (2500) si trattengono le spese di spedizione.
example : rimborso #[3000, 2500] #[false, true] 0 = 2001 :=
  rimborso_sotto_soglia (prezzi := #[3000, 2500]) (resi := #[false, true])
    (coupon := 0) (by decide) (by decide) (by decide) (by decide) (by decide)
    (by decide)

end Rimborso
