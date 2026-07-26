/-
  RIMBORSO DI UN RESO PARZIALE
  ============================

  Un cliente ha comprato N articoli usando un coupon (importo fisso sottratto al totale)
  e pagando 499 centesimi di spedizione, gratuita se il totale al netto del coupon
  raggiunge i 5000 centesimi. Ora rende un sottoinsieme degli articoli.

  QUANTO GLI SI RIMBORSA?  La domanda non ha una risposta unica: il coupon e la
  spedizione sono proprieta' dell'ORDINE, non dei singoli articoli, e vanno riattribuiti.
  Questo file adotta e formalizza la politica CONTROFATTUALE:

      rimborso = (quanto ha pagato)  -  (quanto avrebbe pagato ordinando
                                          soltanto gli articoli che tiene)

  con due scelte esplicite:

  (a) L'ordine controfattuale viene riprezzato da zero, con le stesse regole: stesso
      coupon (l'enunciato non gli attribuisce alcuna soglia minima di spesa, quindi
      sarebbe stato valido anche sull'ordine ridotto) e stessa regola di spedizione,
      rivalutata sul nuovo totale.  Un ordine vuoto costa 0: chi rende tutto riprende
      tutto, spedizione inclusa.

  (b) Il rimborso non e' mai negativo.  Se il reso fa scendere l'ordine sotto la soglia
      dei 5000, il cliente perde il beneficio della spedizione gratuita e il conto
      controfattuale puo' superare quanto ha gia' pagato: in quel caso non gli si
      addebita altro, il rimborso e' semplicemente 0.  (Vedi `rende_ma_non_riceve`:
      e' una conseguenza scomoda ma reale della politica, non un bug.)

  ALTERNATIVA NON IMPLEMENTATA: allocare il coupon pro-quota sugli articoli e rimborsare
  la quota degli articoli resi.  Da preferire se il coupon avesse una soglia minima di
  spesa (qui non l'ha) o se la contabilita' richiedesse un valore per riga; costa una
  divisione con arrotondamento e l'invariante "le quote sommano al coupon".
  Sotto la politica controfattuale il cliente conserva l'intero coupon sull'ordine
  ridotto: vedi il teorema `coupon_resta_al_cliente`.
-/

/-! ## 1. Il listino -/

/-- Costo della spedizione, in centesimi. -/
def spedizione : Int := 499

/-- Totale (al netto del coupon) da cui la spedizione diventa gratuita. -/
def soglia : Int := 5000

/-! ## 2. Il prezzo di un ordine -/

def somma : List Int → Int
  | [] => 0
  | p :: t => p + somma t

/-- Totale degli articoli dopo il coupon. Il coupon non puo' rendere negativo il totale:
    l'eccedenza si perde. -/
def netto (totale coupon : Int) : Int :=
  if totale ≤ coupon then 0 else totale - coupon

/-- Aggiunge la spedizione a un totale netto, se questo non raggiunge la soglia. -/
def conSpedizione (n : Int) : Int :=
  if soglia ≤ n then n else n + spedizione

/-- Prezzo di un ordine: quanto si paga alla cassa per questi articoli con questo coupon.
    Un ordine senza articoli costa 0 (niente articoli, niente spedizione). -/
def costo : List Int → Int → Int
  | [], _ => 0
  | p :: t, coupon => conSpedizione (netto (somma (p :: t)) coupon)

/-! ## 3. Articoli tenuti e articoli resi

Un ordine con i suoi resi e' una lista di coppie (prezzo, reso?). -/

def prezziTutti (l : List (Int × Bool)) : List Int :=
  l.map Prod.fst

def prezziTenuti (l : List (Int × Bool)) : List Int :=
  (l.filter (fun x => !x.2)).map Prod.fst

def prezziResi (l : List (Int × Bool)) : List Int :=
  (l.filter (fun x => x.2)).map Prod.fst

/-! ## 4. La funzione -/

/-- Tronca a zero: non si addebita mai il cliente per un reso. -/
def nonNegativo (x : Int) : Int :=
  if x ≤ 0 then 0 else x

/-- Il rimborso, sulla lista delle coppie (prezzo, reso?). -/
def rimborsoL (l : List (Int × Bool)) (coupon : Int) : Int :=
  nonNegativo (costo (prezziTutti l) coupon - costo (prezziTenuti l) coupon)

def coppie (prezzi : Array Int) (resi : Array Bool) : List (Int × Bool) :=
  prezzi.toList.zip resi.toList

/-- Quanto il cliente ha pagato per l'ordine. -/
def pagato (prezzi : Array Int) (coupon : Int) : Int :=
  costo prezzi.toList coupon

/-- **La funzione richiesta.** `prezzi[i]` e' il prezzo dell'articolo i-esimo,
    `resi[i] = true` significa che l'articolo i viene reso. Risultato in centesimi. -/
def rimborso (prezzi : Array Int) (resi : Array Bool) (coupon : Int) : Int :=
  rimborsoL (coppie prezzi resi) coupon

/-! ## 5. Qualche conto, per fissare le idee -/

-- Due articoli, nessun coupon, sotto soglia: si paga 3000 + 499 di spedizione.
example : pagato #[1000, 2000] 0 = 3499 := by decide
-- Si rende quello da 2000: resta un ordine da 1000 + 499. Rimborso = 2000.
example : rimborso #[1000, 2000] #[false, true] 0 = 2000 := by decide
-- Si rende tutto: si riprende tutto, spedizione inclusa.
example : rimborso #[1000, 2000] #[true, true] 0 = 3499 := by decide
-- Non si rende niente: zero.
example : rimborso #[1000, 2000] #[false, false] 0 = 0 := by decide
-- Il coupon eccedente non genera credito, ma la spedizione pagata si riprende.
example : pagato #[1000] 9999 = 499 := by decide
example : rimborso #[1000] #[true] 9999 = 499 := by decide

/-! ## 6. Fatti elementari -/

theorem costo_nil (coupon : Int) : costo [] coupon = 0 := rfl

theorem costo_cons (p : Int) (t : List Int) (coupon : Int) :
    costo (p :: t) coupon = conSpedizione (netto (somma (p :: t)) coupon) := rfl

theorem netto_nonneg (totale coupon : Int) : 0 ≤ netto totale coupon := by
  unfold netto; split <;> omega

theorem conSpedizione_nonneg {n : Int} (h : 0 ≤ n) : 0 ≤ conSpedizione n := by
  unfold conSpedizione spedizione; split <;> omega

/-- Nessun ordine costa meno di zero. -/
theorem costo_nonneg (articoli : List Int) (coupon : Int) : 0 ≤ costo articoli coupon := by
  cases articoli with
  | nil => simp [costo_nil]
  | cons p t => exact conSpedizione_nonneg (netto_nonneg _ _)

theorem prezziTutti_cons (x : Int × Bool) (t : List (Int × Bool)) :
    prezziTutti (x :: t) = x.1 :: prezziTutti t := rfl

theorem prezziTenuti_cons_true {x : Int × Bool} (hx : x.2 = true) (t : List (Int × Bool)) :
    prezziTenuti (x :: t) = prezziTenuti t := by
  simp [prezziTenuti, hx]

theorem prezziTenuti_cons_false {x : Int × Bool} (hx : x.2 = false) (t : List (Int × Bool)) :
    prezziTenuti (x :: t) = x.1 :: prezziTenuti t := by
  simp [prezziTenuti, hx]

theorem prezziResi_cons_true {x : Int × Bool} (hx : x.2 = true) (t : List (Int × Bool)) :
    prezziResi (x :: t) = x.1 :: prezziResi t := by
  simp [prezziResi, hx]

theorem prezziResi_cons_false {x : Int × Bool} (hx : x.2 = false) (t : List (Int × Bool)) :
    prezziResi (x :: t) = prezziResi t := by
  simp [prezziResi, hx]

/-- Niente si perde: i prezzi tenuti piu' i prezzi resi fanno il totale dell'ordine. -/
theorem somma_tenuti_resi (l : List (Int × Bool)) :
    somma (prezziTenuti l) + somma (prezziResi l) = somma (prezziTutti l) := by
  induction l with
  | nil => rfl
  | cons x t ih =>
      cases hx : x.2 with
      | true =>
          rw [prezziTenuti_cons_true hx, prezziResi_cons_true hx, prezziTutti_cons]
          simp only [somma]
          omega
      | false =>
          rw [prezziTenuti_cons_false hx, prezziResi_cons_false hx, prezziTutti_cons]
          simp only [somma]
          omega

/-- Con prezzi non negativi, il valore di quel che si rende non e' negativo. -/
theorem somma_resi_nonneg (l : List (Int × Bool)) (h : ∀ x ∈ l, 0 ≤ x.1) :
    0 ≤ somma (prezziResi l) := by
  induction l with
  | nil => exact Int.le_refl 0
  | cons x t ih =>
      have hx1 : 0 ≤ x.1 := h x (by simp)
      have iht : 0 ≤ somma (prezziResi t) := ih (fun y hy => h y (by simp [hy]))
      cases hx : x.2 with
      | true =>
          rw [prezziResi_cons_true hx]
          simp only [somma]
          omega
      | false =>
          rw [prezziResi_cons_false hx]
          exact iht

/-! ## 7. Le proprieta' del rimborso -/

/-- **Non si addebita mai il cliente.** Il rimborso non e' mai negativo. -/
theorem rimborso_nonneg (prezzi : Array Int) (resi : Array Bool) (coupon : Int) :
    0 ≤ rimborso prezzi resi coupon := by
  unfold rimborso rimborsoL nonNegativo; split <;> omega

/-- Il rimborso non supera mai il prezzo dell'ordine intero. -/
theorem rimborsoL_le_costo (l : List (Int × Bool)) (coupon : Int) :
    rimborsoL l coupon ≤ costo (prezziTutti l) coupon := by
  have h1 := costo_nonneg (prezziTenuti l) coupon
  have h2 := costo_nonneg (prezziTutti l) coupon
  unfold rimborsoL nonNegativo; split <;> omega

/-- **Conservazione.** Quando il rimborso non e' troncato, dopo il reso il cliente ha
    speso in tutto esattamente il prezzo dell'ordine dei soli articoli che ha tenuto.
    Questa e' la politica, enunciata come equazione. -/
theorem conservazione (l : List (Int × Bool)) (coupon : Int)
    (h : costo (prezziTenuti l) coupon ≤ costo (prezziTutti l) coupon) :
    costo (prezziTenuti l) coupon + rimborsoL l coupon = costo (prezziTutti l) coupon := by
  unfold rimborsoL nonNegativo; split <;> omega

/-- E quando invece e' troncato, il rimborso e' zero: il cliente ha pagato meno di quanto
    sarebbe costato l'ordine ridotto, e non gli si chiede la differenza. -/
theorem troncato (l : List (Int × Bool)) (coupon : Int)
    (h : costo (prezziTutti l) coupon ≤ costo (prezziTenuti l) coupon) :
    rimborsoL l coupon = 0 := by
  unfold rimborsoL nonNegativo; split <;> omega

/-! ### Casi limite -/

theorem prezziTenuti_eq_tutti_of_all_false (l : List (Int × Bool)) (h : ∀ x ∈ l, x.2 = false) :
    prezziTenuti l = prezziTutti l := by
  induction l with
  | nil => rfl
  | cons x t ih =>
      rw [prezziTenuti_cons_false (h x (by simp)), prezziTutti_cons,
          ih (fun y hy => h y (by simp [hy]))]

theorem prezziTenuti_nil_of_all_true (l : List (Int × Bool)) (h : ∀ x ∈ l, x.2 = true) :
    prezziTenuti l = [] := by
  induction l with
  | nil => rfl
  | cons x t ih =>
      rw [prezziTenuti_cons_true (h x (by simp)), ih (fun y hy => h y (by simp [hy]))]

/-- **Chi non rende niente non riceve niente.** -/
theorem rimborsoL_nessun_reso (l : List (Int × Bool)) (coupon : Int)
    (h : ∀ x ∈ l, x.2 = false) : rimborsoL l coupon = 0 := by
  unfold rimborsoL nonNegativo
  rw [prezziTenuti_eq_tutti_of_all_false l h]
  split <;> omega

/-- **Chi rende tutto riprende tutto**, spedizione compresa. -/
theorem rimborsoL_tutto_reso (l : List (Int × Bool)) (coupon : Int)
    (h : ∀ x ∈ l, x.2 = true) : rimborsoL l coupon = costo (prezziTutti l) coupon := by
  have hc := costo_nonneg (prezziTutti l) coupon
  unfold rimborsoL nonNegativo
  rw [prezziTenuti_nil_of_all_true l h, costo_nil]
  split <;> omega

/-! ### Il caso regolare

Lontano dai due punti di rottura (coupon che eccede il totale, soglia della spedizione
attraversata dal reso) il rimborso e' semplicemente la somma dei prezzi resi. -/

/-- Un ordine non vuoto che resta sopra soglia costa esattamente il totale meno il coupon:
    niente spedizione e niente troncamento del coupon. -/
theorem costo_sopra_soglia (a : List Int) (coupon : Int) (hne : a ≠ [])
    (hs : soglia ≤ somma a - coupon) : costo a coupon = somma a - coupon := by
  have h5 : soglia = 5000 := rfl
  cases a with
  | nil => exact absurd rfl hne
  | cons p q =>
      rw [costo_cons]
      unfold netto
      rw [if_neg (by omega)]
      unfold conSpedizione
      rw [if_pos (by omega)]

theorem rimborsoL_regolare (x : Int × Bool) (t : List (Int × Bool)) (coupon : Int)
    (hprezzi : ∀ y ∈ x :: t, 0 ≤ y.1)
    (hresta : prezziTenuti (x :: t) ≠ [])
    (hsoglia : soglia ≤ somma (prezziTenuti (x :: t)) - coupon) :
    rimborsoL (x :: t) coupon = somma (prezziResi (x :: t)) := by
  have h5 : soglia = 5000 := rfl
  have hsplit := somma_tenuti_resi (x :: t)
  have hresi := somma_resi_nonneg (x :: t) hprezzi
  have htutti := costo_sopra_soglia (prezziTutti (x :: t)) coupon
    (by simp [prezziTutti]) (by omega)
  have htenuti := costo_sopra_soglia (prezziTenuti (x :: t)) coupon hresta hsoglia
  unfold rimborsoL nonNegativo
  rw [htutti, htenuti]
  split <;> omega

/-! ### Il prezzo della politica

Due conseguenze reali della scelta controfattuale, esibite su casi concreti perche' si
vedano prima di andare in produzione. -/

/-- Il cliente conserva l'intero coupon sull'ordine ridotto: rendendo uno dei due articoli
    da 3000 con un coupon da 1500 riprende 3000 pieni, non 3000 meno la sua quota di
    coupon. (Ha pagato 4999 = 6000 - 1500 + 499, l'ordine ridotto costa 1999.) -/
theorem coupon_resta_al_cliente :
    pagato #[3000, 3000] 1500 = 4999 ∧
    rimborso #[3000, 3000] #[false, true] 1500 = 3000 := by
  constructor <;> decide

/-- Il caso scomodo: l'ordine da 5100 aveva la spedizione gratis. Rendendo l'articolo da
    200 si scende a 4900 e la spedizione (499) torna dovuta: l'ordine ridotto costa 5399,
    piu' di quanto il cliente ha pagato. Il rimborso e' 0 e non si addebita altro.
    Rendendo invece tutto, riprende i suoi 5100 interi. -/
theorem rende_ma_non_riceve :
    pagato #[4900, 200] 0 = 5100 ∧
    rimborso #[4900, 200] #[false, true] 0 = 0 ∧
    rimborso #[4900, 200] #[true, true] 0 = 5100 := by
  refine ⟨by decide, by decide, by decide⟩

/-- Quindi il rimborso NON e' monotono nell'insieme dei resi: rendere di piu' puo' far
    rimborsare di piu' di quanto si otterrebbe rendendo un sottoinsieme. -/
theorem non_monotono :
    rimborso #[4900, 200] #[false, true] 0 < rimborso #[4900, 200] #[true, true] 0 := by
  decide

/-! ## 8. Dalla lista agli array

Le proprieta' di sopra sono enunciate sulle coppie (prezzo, reso?). Qui si trasportano
su `rimborso`, che le coppie se le costruisce da due array della stessa lunghezza. -/

theorem map_fst_zip {α β : Type} : ∀ (l₁ : List α) (l₂ : List β),
    l₁.length ≤ l₂.length → (l₁.zip l₂).map Prod.fst = l₁
  | [], _, _ => rfl
  | _ :: _, [], h => by simp at h
  | a :: t₁, b :: t₂, h => by
      rw [List.zip_cons_cons, List.map_cons, map_fst_zip t₁ t₂ (by simp at h; omega)]

theorem snd_mem_of_mem_zip {α β : Type} : ∀ {l₁ : List α} {l₂ : List β} {x : α × β},
    x ∈ l₁.zip l₂ → x.2 ∈ l₂
  | [], _, _, h => by simp [List.zip] at h
  | _ :: _, [], _, h => by simp [List.zip] at h
  | _ :: t₁, b :: t₂, _, h => by
      rw [List.zip_cons_cons, List.mem_cons] at h
      cases h with
      | inl he => subst he; simp
      | inr ht => exact List.mem_cons_of_mem b (snd_mem_of_mem_zip ht)

/-- Se gli array hanno la stessa lunghezza, l'accoppiamento non perde nessun prezzo. -/
theorem prezziTutti_coppie (prezzi : Array Int) (resi : Array Bool)
    (h : prezzi.size = resi.size) :
    prezziTutti (coppie prezzi resi) = prezzi.toList := by
  unfold prezziTutti coppie
  exact map_fst_zip _ _ (by simp [h])

/-- **Correttezza, sugli array.** Il rimborso e' quanto il cliente ha pagato meno quanto
    sarebbe costato l'ordine dei soli articoli che tiene, troncato a zero. -/
theorem rimborso_spec (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (h : prezzi.size = resi.size) :
    rimborso prezzi resi coupon =
      nonNegativo (pagato prezzi coupon
                   - costo (prezziTenuti (coppie prezzi resi)) coupon) := by
  unfold rimborso rimborsoL pagato
  rw [prezziTutti_coppie prezzi resi h]

/-- Non si rimborsa mai piu' di quanto il cliente ha pagato. -/
theorem rimborso_le_pagato (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (h : prezzi.size = resi.size) :
    rimborso prezzi resi coupon ≤ pagato prezzi coupon := by
  have hle := rimborsoL_le_costo (coppie prezzi resi) coupon
  unfold rimborso pagato
  rwa [prezziTutti_coppie prezzi resi h] at hle

/-- Nessun articolo reso: rimborso zero. -/
theorem rimborso_nessun_reso (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (hr : ∀ b ∈ resi.toList, b = false) :
    rimborso prezzi resi coupon = 0 :=
  rimborsoL_nessun_reso _ coupon (fun x hx => hr x.2 (snd_mem_of_mem_zip hx))

/-- Tutti gli articoli resi: si rimborsa l'intero importo pagato, spedizione compresa. -/
theorem rimborso_tutto_reso (prezzi : Array Int) (resi : Array Bool) (coupon : Int)
    (h : prezzi.size = resi.size) (hr : ∀ b ∈ resi.toList, b = true) :
    rimborso prezzi resi coupon = pagato prezzi coupon := by
  have ht := rimborsoL_tutto_reso (coppie prezzi resi) coupon
    (fun x hx => hr x.2 (snd_mem_of_mem_zip hx))
  unfold rimborso pagato
  rwa [prezziTutti_coppie prezzi resi h] at ht

/-! ## 9. Nessun buco

Ogni teorema di sopra si regge solo sugli assiomi standard di Lean: niente `sorryAx`,
niente `native_decide`. -/

#print axioms rimborso_spec
#print axioms rimborso_nonneg
#print axioms rimborso_le_pagato
#print axioms rimborso_nessun_reso
#print axioms rimborso_tutto_reso
#print axioms conservazione
#print axioms troncato
#print axioms rimborsoL_regolare
#print axioms non_monotono
