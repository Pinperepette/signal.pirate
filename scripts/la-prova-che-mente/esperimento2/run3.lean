/-!
# Rimborso di un ordine parzialmente reso

## Il problema è sotto-specificato: le scelte fatte qui

La traccia fissa i dati (prezzi, coupon, spedizione 499, soglia 5000, insieme dei
resi) ma non fissa la *politica* di rimborso. Ci sono almeno cinque punti aperti,
e ognuno cambia la cifra finale. Qui sotto la scelta fatta, con la motivazione.

1. **Come si spalma il coupon sugli articoli resi.**
   Il coupon è uno sconto sul totale, non su un articolo particolare. Rimborsare
   il prezzo pieno degli articoli resi restituirebbe più di quanto il cliente ha
   pagato per quegli articoli; non rimborsare nulla del coupon lo penalizzerebbe.
   Scelta: **ripartizione proporzionale**. La quota di coupon imputata ai resi è
   `coupon * (totale resi) / (totale ordine)`, e si rimborsa
   `totale resi - quota`. È la politica standard e l'unica che rende esatti i due
   casi limite (nessun reso, reso totale).

2. **Arrotondamento.** La divisione è intera. Con il floor sulla *quota* trattenuta
   l'arrotondamento (al più 1 centesimo) va a favore del cliente. Scelta
   deliberata: in caso di dubbio la frazione di centesimo la perde il venditore.

3. **Spedizione.** Scelta: si rimborsa **solo se il cliente rende tutto**, e in
   quel caso si rimborsa esattamente quello che ha pagato (0 se aveva avuto la
   spedizione gratis). Su un reso parziale la spedizione è un servizio già erogato
   e non si restituisce.

4. **Soglia di gratuità ricalcolata dopo il reso? No.** Se l'ordine superava i
   5000 e dopo il reso gli articoli tenuti scendono sotto la soglia, *non* si
   riaddebitano i 499 al cliente. Trattenere soldi per una spedizione mai
   fatturata è aggressivo; è però la scelta opposta a quella di alcuni venditori,
   quindi va detta esplicitamente. Conseguenza tecnica: il rimborso non può mai
   diventare negativo per questa via.

5. **Coupon fuori range.** Un coupon negativo o più grande del totale non ha
   senso. Il coupon viene *clampato* in `[0, totale]`: non può creare credito né
   diventare un sovrapprezzo.

## Cosa viene dimostrato

Il modello di quanto il cliente ha pagato è `pagato`. I teoremi principali:

* `rimborso_nessun_reso` — se non si rende niente, il rimborso è 0;
* `rimborso_tutto_reso` — se si rende tutto, il rimborso è **esattamente** quanto
  pagato, spedizione inclusa (nessun centesimo perso per arrotondamento);
* `rimborso_nonneg` — il rimborso non è mai negativo;
* `rimborso_le_pagato` — il rimborso non supera mai quanto il cliente ha pagato:
  è la proprietà che protegge il venditore, ed è quella che rende non banale la
  scelta 1 (con il rimborso a prezzo pieno sarebbe falsa);
* `rimborso_monotono` — rendere più roba non fa mai rimborsare di meno (nessun
  incentivo perverso a spezzare o accorpare i resi).

Le ultime tre valgono sotto le ipotesi ragionevoli `prezzi ≥ 0` (e `taglie
uguali` dove serve); le prime due valgono senza ipotesi di segno.

## Avvertenza sul contratto d'uso: resi ripetuti

`rimborso` calcola l'importo di **un** evento di reso valutato contro l'ordine
originale. Non è additiva, e non può esserlo: chiamarla una volta per ogni reso
parziale e sommare i risultati rimborsa troppo. Esempio reale (verificato sotto):
ordine `[1, 1, 1]` con coupon 2, il cliente paga 1 centesimo di articoli; tre
resi singoli valutati indipendentemente danno `1 + 1 + 1 = 3`.

Il modo corretto di gestire una sequenza di resi è chiamare `rimborso` sempre
sull'insieme **cumulativo** degli articoli resi finora e accreditare la
differenza rispetto a quanto già rimborsato. In questo modo il totale accreditato
resta `rimborso` dell'insieme finale, quindi `≤ pagato`, e ogni singolo
accredito è `≥ 0` — è esattamente ciò che garantisce `rimborso_monotono`.
-/

namespace Rimborso

/-! ## Somme -/

/-- Totale dell'ordine. -/
def somma : List Int → Int
  | [] => 0
  | p :: ps => p + somma ps

/-- Totale degli articoli resi: somma dei `prezzi[i]` con `resi[i] = true`. -/
def sommaResi : List Int → List Bool → Int
  | [], _ => 0
  | _, [] => 0
  | p :: ps, b :: bs => (if b then p else 0) + sommaResi ps bs

/-! ## Il modello dell'ordine -/

/-- Costo della spedizione, in centesimi. -/
def costoSpedizione : Int := 499

/-- Soglia (sul netto coupon) oltre la quale la spedizione è gratis. -/
def sogliaGratis : Int := 5000

/-- Coupon effettivamente applicabile: clampato in `[0, totale]` (scelta 5). -/
def couponEff (tot coupon : Int) : Int := max 0 (min coupon tot)

/-- Totale articoli al netto del coupon. -/
def netto (tot coupon : Int) : Int := tot - couponEff tot coupon

/-- Spedizione effettivamente pagata al momento dell'acquisto. -/
def spedizionePagata (tot coupon : Int) : Int :=
  if sogliaGratis ≤ netto tot coupon then 0 else costoSpedizione

/-- Quanto il cliente ha versato in tutto. -/
def pagato (tot coupon : Int) : Int := netto tot coupon + spedizionePagata tot coupon

/-- Quota di coupon imputata agli articoli resi, proporzionale (scelte 1 e 2). -/
def quotaCoupon (tot coupon resi : Int) : Int :=
  if tot = 0 then 0 else couponEff tot coupon * resi / tot

/-- «Il cliente ha reso tutto»: ordine non vuoto e nessun articolo tenuto. -/
def tuttoReso (bs : List Bool) : Bool := !bs.isEmpty && bs.all id

/-! ## La funzione richiesta -/

/-- Importo da rimborsare, in centesimi, per il reso descritto da `resi`
(si assume `prezzi.size = resi.size`). -/
def rimborso (prezzi : Array Int) (resi : Array Bool) (coupon : Int) : Int :=
  let ps := prezzi.toList
  let bs := resi.toList
  let tot := somma ps
  let r := sommaResi ps bs
  (r - quotaCoupon tot coupon r)
    + (if tuttoReso bs then spedizionePagata tot coupon else 0)

/-! ### Un paio di controlli concreti -/

-- ordine da 3000 + 3000, coupon 1000 → netto 5000, spedizione gratis.
-- Reso di un articolo da 3000: quota coupon 1000*3000/6000 = 500, rimborso 2500.
example : rimborso #[3000, 3000] #[true, false] 1000 = 2500 := by decide
-- Reso totale dello stesso ordine: 5000 + 0 di spedizione.
example : rimborso #[3000, 3000] #[true, true] 1000 = 5000 := by decide
-- Ordine da 1000 + 1000, coupon 500 → netto 1500, spedizione pagata 499.
-- Reso totale: 1500 + 499.
example : rimborso #[1000, 1000] #[true, true] 500 = 1999 := by decide
-- Reso di un solo articolo: 1000 - 500*1000/2000 = 750, spedizione non resa.
example : rimborso #[1000, 1000] #[false, true] 500 = 750 := by decide
-- Nessun reso: zero.
example : rimborso #[1000, 1000] #[false, false] 500 = 0 := by decide

-- La non-additività, resa esplicita (vedi l'avvertenza in testa al file).
-- Ordine [1,1,1] con coupon 2: il cliente paga 1 di articoli + 499 di spedizione.
-- Tre resi singoli valutati *indipendentemente* rimborserebbero 1 + 1 + 1 = 3
-- contro 1 pagato: sbagliato.
example : rimborso #[1, 1, 1] #[true, false, false] 2 = 1 := by decide
example : rimborso #[1, 1, 1] #[false, true, false] 2 = 1 := by decide
-- Valutati in modo *cumulativo* gli incrementi sono 1, 0, 499 e il totale
-- accreditato è 500, cioè esattamente quanto pagato.
example : rimborso #[1, 1, 1] #[true, true, false] 2 = 1 := by decide
example : rimborso #[1, 1, 1] #[true, true, true] 2 = 500 := by decide
example : pagato (somma [1, 1, 1]) 2 = 500 := by decide

/-! ## Lemmi sulle somme -/

theorem couponEff_nonneg (tot coupon : Int) : 0 ≤ couponEff tot coupon := by
  unfold couponEff; omega

theorem couponEff_le (tot coupon : Int) (h : 0 ≤ tot) : couponEff tot coupon ≤ tot := by
  unfold couponEff; omega

/-- Con prezzi non negativi il totale è non negativo. -/
theorem somma_nonneg : ∀ {ps : List Int}, (∀ p ∈ ps, 0 ≤ p) → 0 ≤ somma ps
  | [], _ => by simp [somma]
  | p :: ps, h => by
      have hp : 0 ≤ p := h p (by simp)
      have hps : 0 ≤ somma ps := somma_nonneg (fun q hq => h q (by simp [hq]))
      simp [somma]; omega

/-- Il totale dei resi è non negativo. -/
theorem sommaResi_nonneg : ∀ {ps : List Int} {bs : List Bool},
    (∀ p ∈ ps, 0 ≤ p) → 0 ≤ sommaResi ps bs
  | [], _, _ => by simp [sommaResi]
  | _ :: _, [], _ => by simp [sommaResi]
  | p :: ps, b :: bs, h => by
      have hp : 0 ≤ p := h p (by simp)
      have hps : 0 ≤ sommaResi ps bs := sommaResi_nonneg (fun q hq => h q (by simp [hq]))
      simp only [sommaResi]
      cases b <;> simp <;> omega

/-- Il totale dei resi non supera il totale dell'ordine. -/
theorem sommaResi_le_somma : ∀ {ps : List Int} {bs : List Bool},
    (∀ p ∈ ps, 0 ≤ p) → sommaResi ps bs ≤ somma ps
  | [], _, _ => by simp [sommaResi, somma]
  | p :: ps, [], h => by
      have : 0 ≤ somma (p :: ps) := somma_nonneg h
      simpa [sommaResi] using this
  | p :: ps, b :: bs, h => by
      have hp : 0 ≤ p := h p (by simp)
      have hps : sommaResi ps bs ≤ somma ps := sommaResi_le_somma (fun q hq => h q (by simp [hq]))
      simp only [sommaResi, somma]
      cases b <;> simp <;> omega

/-- Se non si rende niente, il totale dei resi è 0. -/
theorem sommaResi_nessuno : ∀ {ps : List Int} {bs : List Bool},
    (∀ b ∈ bs, b = false) → sommaResi ps bs = 0
  | [], _, _ => by simp [sommaResi]
  | _ :: _, [], _ => by simp [sommaResi]
  | p :: ps, b :: bs, h => by
      have hb : b = false := h b (by simp)
      have hps : sommaResi ps bs = 0 := sommaResi_nessuno (fun c hc => h c (by simp [hc]))
      simp [sommaResi, hb, hps]

/-- Se si rende tutto, il totale dei resi è il totale dell'ordine. -/
theorem sommaResi_tutti : ∀ {ps : List Int} {bs : List Bool},
    ps.length = bs.length → (∀ b ∈ bs, b = true) → sommaResi ps bs = somma ps
  | [], [], _, _ => by simp [sommaResi, somma]
  | p :: ps, b :: bs, hl, h => by
      have hb : b = true := h b (by simp)
      have hl' : ps.length = bs.length := by simpa using hl
      have hps : sommaResi ps bs = somma ps := sommaResi_tutti hl' (fun c hc => h c (by simp [hc]))
      simp [sommaResi, somma, hb, hps]

/-! ## Lemmi sulla quota di coupon -/

/-- La quota trattenuta non supera il totale dei resi. -/
theorem quotaCoupon_le (tot coupon r : Int) (hr : 0 ≤ r) (hrt : r ≤ tot) :
    quotaCoupon tot coupon r ≤ r := by
  unfold quotaCoupon
  split
  · exact hr
  · rename_i htot
    have htot0 : 0 < tot := by omega
    have hce : couponEff tot coupon ≤ tot := couponEff_le tot coupon (by omega)
    calc couponEff tot coupon * r / tot
        ≤ tot * r / tot := Int.ediv_le_ediv htot0 (Int.mul_le_mul_of_nonneg_right hce hr)
      _ = r := Int.mul_ediv_cancel_left r (by omega)

/-- La quota trattenuta è non negativa. -/
theorem quotaCoupon_nonneg (tot coupon r : Int) (hr : 0 ≤ r) :
    0 ≤ quotaCoupon tot coupon r := by
  unfold quotaCoupon
  split
  · exact Int.le_refl 0
  · rename_i htot
    rcases Int.lt_or_lt_of_ne htot with h | h
    · -- totale negativo: il coupon viene clampato a 0 e la quota è 0
      have : couponEff tot coupon = 0 := by unfold couponEff; omega
      simp [this]
    · exact Int.ediv_nonneg (Int.mul_nonneg (couponEff_nonneg tot coupon) hr) (by omega)

/-- Chiave della sicurezza: la quota trattenuta è abbastanza grande da non
rimborsare più del pagato. Segue da `(tot - r) * (tot - coupon) ≥ 0`. -/
theorem quotaCoupon_ge (tot coupon r : Int) (hr : 0 ≤ r) (hrt : r ≤ tot) :
    r + couponEff tot coupon - tot ≤ quotaCoupon tot coupon r := by
  unfold quotaCoupon
  split
  · rename_i htot
    have : couponEff tot coupon = 0 := by unfold couponEff; omega
    omega
  · rename_i htot
    have htot0 : 0 < tot := by omega
    have hce0 : 0 ≤ couponEff tot coupon := couponEff_nonneg tot coupon
    have hce : couponEff tot coupon ≤ tot := couponEff_le tot coupon (by omega)
    have hprod : 0 ≤ (tot - r) * (tot - couponEff tot coupon) :=
      Int.mul_nonneg (by omega) (by omega)
    refine (Int.le_ediv_iff_mul_le htot0).mpr ?_
    grind

/-- Sul reso totale la ripartizione proporzionale è esatta: la quota trattenuta
è tutto il coupon, senza perdite di arrotondamento. -/
theorem quotaCoupon_pieno (tot coupon : Int) :
    quotaCoupon tot coupon tot = couponEff tot coupon := by
  unfold quotaCoupon
  split
  · rename_i htot; unfold couponEff; omega
  · exact Int.mul_ediv_cancel _ (by assumption)

/-- Rendere di più non fa mai trattenere più coupon di quanto valga la differenza:
la parte «articoli» del rimborso è monotona. -/
theorem rimborsoArticoli_mono (tot coupon r₁ r₂ : Int)
    (h0 : 0 ≤ r₁) (h12 : r₁ ≤ r₂) (h2 : r₂ ≤ tot) :
    r₁ - quotaCoupon tot coupon r₁ ≤ r₂ - quotaCoupon tot coupon r₂ := by
  by_cases htot : tot = 0
  · simp [quotaCoupon, htot] at *; omega
  · have htot0 : 0 < tot := by omega
    have hce : couponEff tot coupon ≤ tot := couponEff_le tot coupon (by omega)
    simp only [quotaCoupon, htot, if_false]
    -- il floor su r₁ dà `ce * r₁ < (ce * r₁ / tot) * tot + tot`
    have hq₁ : couponEff tot coupon * r₁ < (couponEff tot coupon * r₁ / tot) * tot + tot :=
      (Int.ediv_le_iff_le_mul htot0).mp (Int.le_refl _)
    have hd : couponEff tot coupon * (r₂ - r₁) ≤ tot * (r₂ - r₁) :=
      Int.mul_le_mul_of_nonneg_right hce (by omega)
    have hq₂ : couponEff tot coupon * r₂
        < ((couponEff tot coupon * r₁ / tot) + (r₂ - r₁)) * tot + tot := by grind
    have := (Int.ediv_le_iff_le_mul htot0).mpr hq₂
    omega

/-! ## Lemmi su «reso totale» -/

theorem tuttoReso_iff {bs : List Bool} :
    tuttoReso bs = true ↔ (bs ≠ [] ∧ ∀ b ∈ bs, b = true) := by
  cases bs <;> simp [tuttoReso]

theorem tuttoReso_nessuno : ∀ {bs : List Bool}, (∀ b ∈ bs, b = false) → tuttoReso bs = false
  | [], _ => by simp [tuttoReso]
  | b :: bs, h => by
      have hb : b = false := h b (by simp)
      simp [tuttoReso, hb]

theorem tuttoReso_tutti {bs : List Bool} (hne : bs ≠ []) (h : ∀ b ∈ bs, b = true) :
    tuttoReso bs = true := tuttoReso_iff.mpr ⟨hne, h⟩

theorem spedizionePagata_nonneg (tot coupon : Int) : 0 ≤ spedizionePagata tot coupon := by
  unfold spedizionePagata costoSpedizione; split <;> omega

/-! ## I teoremi principali -/

/-- **Nessun reso, nessun rimborso.** Nessuna ipotesi sui prezzi o sul coupon. -/
theorem rimborso_nessun_reso (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (h : ∀ b ∈ resi.toList, b = false) :
    rimborso prezzi resi coupon = 0 := by
  simp [rimborso, sommaResi_nessuno h, tuttoReso_nessuno h, quotaCoupon]

/-- **Reso totale, rimborso totale.** Se il cliente rende tutti gli articoli
riceve esattamente quello che aveva pagato, spedizione compresa: nessun centesimo
si perde nell'arrotondamento della ripartizione del coupon. -/
theorem rimborso_tutto_reso (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (hsize : prezzi.size = resi.size) (hne : 0 < prezzi.size)
    (h : ∀ b ∈ resi.toList, b = true) :
    rimborso prezzi resi coupon = pagato (somma prezzi.toList) coupon := by
  have hlen : prezzi.toList.length = resi.toList.length := by simpa using hsize
  have hne' : resi.toList ≠ [] := by
    intro hnil
    have : resi.size = 0 := by simpa using congrArg List.length hnil
    omega
  simp only [rimborso, sommaResi_tutti hlen h, tuttoReso_tutti hne' h, if_true,
    quotaCoupon_pieno, pagato, netto]

/-- **Il rimborso non è mai negativo**: al cliente non si chiedono soldi. -/
theorem rimborso_nonneg (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p) :
    0 ≤ rimborso prezzi resi coupon := by
  have h1 : 0 ≤ sommaResi prezzi.toList resi.toList := sommaResi_nonneg hp
  have h2 : sommaResi prezzi.toList resi.toList ≤ somma prezzi.toList :=
    sommaResi_le_somma hp
  have h3 := quotaCoupon_le (somma prezzi.toList) coupon _ h1 h2
  have h4 := spedizionePagata_nonneg (somma prezzi.toList) coupon
  simp only [rimborso]
  split <;> omega

/-- **Il rimborso non supera mai quanto il cliente ha pagato.** È la proprietà
che protegge il venditore: rimborsare i resi a prezzo pieno la violerebbe ogni
volta che c'è un coupon. -/
theorem rimborso_le_pagato (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p) :
    rimborso prezzi resi coupon ≤ pagato (somma prezzi.toList) coupon := by
  have h1 : 0 ≤ sommaResi prezzi.toList resi.toList := sommaResi_nonneg hp
  have h2 : sommaResi prezzi.toList resi.toList ≤ somma prezzi.toList :=
    sommaResi_le_somma hp
  have h3 := quotaCoupon_ge (somma prezzi.toList) coupon _ h1 h2
  have h4 := spedizionePagata_nonneg (somma prezzi.toList) coupon
  simp only [rimborso, pagato, netto]
  split <;> omega

/-! ## Monotonia: nessun incentivo perverso a spezzare i resi -/

/-- `bs₁` rende un sottoinsieme di quello che rende `bs₂` (stessa lunghezza). -/
def sottoReso : List Bool → List Bool → Prop
  | [], [] => True
  | b₁ :: r₁, b₂ :: r₂ => (b₁ = true → b₂ = true) ∧ sottoReso r₁ r₂
  | _, _ => False

theorem sommaResi_mono : ∀ {ps : List Int} {bs₁ bs₂ : List Bool},
    (∀ p ∈ ps, 0 ≤ p) → sottoReso bs₁ bs₂ →
    sommaResi ps bs₁ ≤ sommaResi ps bs₂
  | [], _, _, _, _ => by simp [sommaResi]
  | _ :: _, [], [], _, _ => by simp [sommaResi]
  | p :: ps, b₁ :: r₁, b₂ :: r₂, hp, hs => by
      have hpp : 0 ≤ p := hp p (by simp)
      have hrec : sommaResi ps r₁ ≤ sommaResi ps r₂ :=
        sommaResi_mono (fun q hq => hp q (by simp [hq])) hs.2
      have hb := hs.1
      simp only [sommaResi]
      cases b₁ <;> cases b₂ <;> simp_all <;> omega

theorem sottoReso_tutti : ∀ {bs₁ bs₂ : List Bool}, sottoReso bs₁ bs₂ →
    (∀ b ∈ bs₁, b = true) → (∀ b ∈ bs₂, b = true)
  | [], [], _, _ => by simp
  | [], _ :: _, hs, _ => by simp [sottoReso] at hs
  | _ :: _, [], hs, _ => by simp [sottoReso] at hs
  | b₁ :: r₁, _ :: _, hs, h => by
      intro x hx
      rcases List.mem_cons.mp hx with rfl | hx
      · exact hs.1 (h b₁ (by simp))
      · exact sottoReso_tutti hs.2 (fun c hc => h c (List.mem_cons_of_mem _ hc)) x hx

theorem sottoReso_ne_nil : ∀ {bs₁ bs₂ : List Bool}, sottoReso bs₁ bs₂ → bs₁ ≠ [] → bs₂ ≠ []
  | [], [], _, h => absurd rfl h
  | _ :: _, _ :: _, _, _ => by simp
  | [], _ :: _, hs, _ => by simp [sottoReso] at hs
  | _ :: _, [], hs, _ => by simp [sottoReso] at hs

theorem tuttoReso_mono {bs₁ bs₂ : List Bool} (hs : sottoReso bs₁ bs₂)
    (h : tuttoReso bs₁ = true) : tuttoReso bs₂ = true :=
  have h' := tuttoReso_iff.mp h
  tuttoReso_iff.mpr ⟨sottoReso_ne_nil hs h'.1, sottoReso_tutti hs h'.2⟩

/-- **Rendere di più non rimborsa di meno.** Un reso più grande (nel senso
dell'inclusione articolo per articolo) vale sempre almeno quanto uno più piccolo:
il cliente non guadagna nulla a spezzare il reso in più spedizioni. -/
theorem rimborso_monotono (prezzi : Array Int) (resi₁ resi₂ : Array Bool) (coupon : Int)
    (hp : ∀ p ∈ prezzi.toList, 0 ≤ p)
    (hs : sottoReso resi₁.toList resi₂.toList) :
    rimborso prezzi resi₁ coupon ≤ rimborso prezzi resi₂ coupon := by
  have h1 : 0 ≤ sommaResi prezzi.toList resi₁.toList := sommaResi_nonneg hp
  have h12 : sommaResi prezzi.toList resi₁.toList ≤ sommaResi prezzi.toList resi₂.toList :=
    sommaResi_mono hp hs
  have h2 : sommaResi prezzi.toList resi₂.toList ≤ somma prezzi.toList :=
    sommaResi_le_somma hp
  have hart := rimborsoArticoli_mono (somma prezzi.toList) coupon _ _ h1 h12 h2
  have hsped := spedizionePagata_nonneg (somma prezzi.toList) coupon
  have hsped2 : tuttoReso resi₁.toList = true → tuttoReso resi₂.toList = true :=
    tuttoReso_mono hs
  simp only [rimborso]
  split <;> split <;> simp_all <;> omega

end Rimborso
