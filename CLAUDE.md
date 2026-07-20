# CLAUDE.md — Istruzioni del progetto

> Questo file è la fonte di verità sul progetto. È stato riscritto dopo una
> ricognizione che ha allineato la documentazione allo stato reale del codice.
> La versione precedente descriveva un'architettura "Fase 2" (Cobb-Douglas +
> utili trattenuti) mai implementata e riportava numeri di calibrazione mai
> misurati: entrambi sono stati corretti qui sotto. Vedi §4 e §5.

---

## 1. Contesto e obiettivo (research question — invariata)

Estensione del modello ad agenti (ABM) di **Teglio (2025)** — una "croce
keynesiana disaggregata" con agenti eterogenei — per aggiungere **investimento
endogeno e accumulazione di capitale**, endogenizzando così sia la domanda sia
l'offerta. (Citare **2025**: volume a stampa *Journal of Economic Interaction and
Coordination* 20(1), 107–139; online-first maggio 2024.)

**Stella polare:** l'investimento deve guidare l'output **via capitale** —
l'accumulazione di capitale endogenizza il lato dell'offerta. Il canale di
offerta deve essere vivo e marginalmente attivo. Questo è ciò che il core
Cobb-Douglas ha stabilito (§7).

**Precisazione importante (dal punto 11 in poi).** "Via capitale" **non**
significa "il capitale deve sempre vincolare l'output". Con il mercato del lavoro
(punto 11) il modello riattiva il canale di domanda, e in regime
demand-constrained la capacità non vincola al margine. I due canali coesistono e
il regime diventa un **esito**, non un requisito. In particolare:

> **Un esito wage-led è un RISULTATO, non un fallimento.** In regime
> demand-constrained, più capitale ⇒ meno lavoratori necessari per la stessa
> domanda (`L_domanda` è decrescente in K) ⇒ disoccupazione tecnologica ⇒ monte
> salari e quota salari giù ⇒ domanda giù (l'MPC dei capitalisti è più bassa di
> quella dei lavoratori). Il contro-effetto è la domanda di investimento
> (`I = ρπ`, π cresce con K). Il segno netto è la questione **wage-led vs
> profit-led** kaleckiana, ed è un **oggetto di ricerca**, non un bug. Se il
> modello risultasse wage-led — l'investimento che deprime l'output — quello è il
> ricongiungimento più forte possibile con il meccanismo di leakage di Teglio, ed
> è da riportare, **non da ricalibrare via**.

Il modello deve essere insieme **teoricamente coerente** ed **empiricamente
fondato** (coerente con benchmark macroeconomici reali). Framework: **Mesa**
(Python), test con `pytest`.

Il modello deve essere insieme **teoricamente coerente** (l'investimento guida
davvero l'output) ed **empiricamente fondato** (coerente con benchmark
macroeconomici reali). Framework: **Mesa** (Python), test con `pytest`.

---

## 2. Stato reale del repository (topologia dei branch)

Dopo il merge del brief 06, **`main` è la linea principale corrente** (CES +
mercato del lavoro) e **contiene tutto il lavoro**; la baseline Fase 1 è
preservata dal **tag** `phase-1-baseline`. Gli altri branch restano come
checkpoint storici citabili, con il codice ormai contenuto in `main`. Relazione
lineare: `phase-1-baseline` (tag) → `cobb-douglas-core` → `labour-market` →
`ces-production` → **merge in `main`**. *Nota:* alcuni tip **remoti** su GitHub
(`cobb-douglas-core`, `labour-market-leontief`) hanno commit **solo di
documentazione** più avanti dei tip locali; il codice `src/`/`tests/` coincide
(verificato con `git diff --stat`).

- **`main`** — **linea principale corrente.** Core a **CES normalizzata**
  `Y* = Y0·[π0·(K/K0)^r + (1−π0)·(L/L0)^r]^(1/r)` con **mercato del lavoro
  endogeno** (salario fisso `w̄`, `L = min(L_domanda, L_profitmax, N)`) e
  finanziamento interno via utili trattenuti. Risultato del merge di
  `ces-production` (brief 06). README, notebook, figure e codice **coincidono**;
  CSV misurati in `results/`; driver riproducibile `scripts/run_brief05.py`.
  **345 test verdi.** Numeri e cornice di regime nel README e in §4/§7.

- **`phase-1-baseline`** (tag, non branch) — **Baseline Fase 1 citabile**
  (additiva-nesting): capacità `Y* = A·L·(1 + γ·(K/L)^α)`, investimento
  `I = θ·hoard·util_effect`, nessun mercato del lavoro. README e codice
  coincidono; **12 test verdi**. È lo stato che `main` aveva *prima* del merge
  brief 06 (commit `a02bf65`). Baseline citabile in tesi.

- **`cobb-douglas-core`** (branch, checkpoint storico) — Core di offerta
  (Cobb-Douglas + finanziamento interno via utili trattenuti; conto d'impresa
  infra-periodo, nessun sequestro di moneta). 19 test. **Il suo codice è contenuto
  in `main`.** Numeri e cornice di regime in §4 e §7.

- **`labour-market`** (branch, checkpoint storico) — Punto 11: mercato del lavoro
  endogeno sul core Cobb-Douglas (salario fisso `w̄`, `markup` rimosso, profitto
  residuo). 17 test. **Contenuto in `main`.** Design in §6bis.

- **`ces-production`** (branch, checkpoint storico) — Dove sono stati svolti brief
  04 (CES + sign frontier), brief 05 (stack di robustezza) e brief 06
  (consolidamento). **Mergiato in `main`** (contenuto in `main`); il suo tip è il
  secondo parent del commit di merge.

- **`labour-market-leontief`** (branch) — Checkpoint del punto 11 costruito fuori
  sequenza: produzione **Leontief** `output = A·L` con vincolo di capitale sui
  posti (`max_jobs = K/κ`) e settore pubblico a bilancio in pareggio. 15 test.
  **Fuori rotta e NON mergiato**: il suo **governo** (`government()`, sussidio a
  bilancio in pareggio) è stato **reinnestato su `main` col brief 09** (adattato al
  core CES + wage curve, base imponibile su `max(0,·)`, `rr=0` di default). Il resto
  del branch resta un checkpoint storico non mergiato.

**Nota sui tag.** `phase-1-baseline` è il tag **citabile** della baseline Fase 1
(sul commit `a02bf65`, ex tip di `main`). Esiste anche un tag preesistente
`phase1-baseline` (senza il secondo trattino), su un commit diverso e **non
correlato**: non usarlo come referente — è tenuto solo per non riscrivere la
storia dei tag. Altri tag storici: `cobb-douglas-core-v1`, `labour-market-v1`,
`leontief-exploration`.

---

## 3. Traiettoria del progetto (narrazione corretta)

### Fase 1 — Baseline (`main`, completata)
Additiva-nesting. Investimento finanziato dal risparmio personale via `θ`.
Risultato: θ 0→0.15 alza l'output di steady-state e riduce l'output gap, con
rendimenti decrescenti. **Limite strutturale:** economia demand-constrained con
capacità di lavoro già eccedente la domanda di steady state → **il capitale era
opzionale per costruzione**, e l'investimento endogeno non produceva un vero
uplift dell'output via offerta. Il termine di deepening non vincolava mai.

### Deviazione Leontief (`labour-market-leontief`, completata, fuori sequenza)
Nata da una diagnosi corretta e acuta: **l'ABM di Fase 1 si comportava come il
suo aggregato mean-field** (un aggregato rappresentativo di ~6 righe lo
riproduceva a 3 decimali; bande di confidenza inter-seed ≈ 0). L'eterogeneità e
la rete non "mordevano". Il mercato del lavoro con hiring/firing discreto e
matching casuale ha risolto questo: bande inter-seed finalmente non nulle, Okun
che emerge senza essere fittato (corr ≈ −0.80). **Questa lezione si tiene.**

**Perché è fuori rotta rispetto alla research question:** in Leontief
`output = A·L`, il capitale **non ha margine intensivo** — entra solo come
tetto ai posti equipaggiabili (`K/κ`). Nella calibrazione, a θ=0.15 il modello
accumula K=245 quando ~45 basterebbe a equipaggiare l'intera forza lavoro:
**utilizzo del capitale 0.20, ~80% di capitale strutturalmente ozioso.** A
piena occupazione il capitale non fa nulla al margine; la salita dell'output
50→98 è **100% canale di domanda** (hoard riciclato in salari via assunzioni).
Leontief ha involontariamente **disattivato il lato offerta** — cioè proprio
l'oggetto del progetto. Da qui la decisione di §6.

### Core di offerta — l'ex "Fase 2", ora costruito (`cobb-douglas-core`)
Fino a poco fa esisteva **solo come specifica di design** (mai implementata) nel
vecchio `CLAUDE.md`. Ora è **costruita, calibrata e committata**: Cobb-Douglas
vera con capitale essenziale, finanziamento interno via utili trattenuti. Il
capitale è tornato a mordere — a regime esteso l'output è `A·K^α·L^(1−α)` con
utilizzo ≈0.99, quindi la salita 44→157 è **capacità che cresce con K**, non
moltiplicatore di domanda. Numeri in §4, architettura in §7.

**Cornice di regime — da tenere onesta fino alla scrittura.** Questo core è
**capacity-constrained ovunque, baseline incluso** (u≈1 su tutto lo sweep). Il
baseline `ρ=0` non è stagnazione da domanda debole: è un'economia a **basso
capitale** (K si ferma dove `δK = investment_floor`). Il progetto è oscillato da
"solo la domanda vincola" (Fase 1) a **"solo l'offerta vincola"** (qui). Il
risultato headline "l'investimento guida l'output" è quindi un **risultato di
offerta**, e va presentato come tale — non come dinamica keynesiana da domanda,
che qui è **dormiente**. L'"endogenizzare *sia* domanda *sia* offerta" del titolo
si completa al **punto 11** (mercato del lavoro), dove lo slack diventa
disoccupazione. Dire che questo core mostra stagnazione da domanda sarebbe falso
quanto il "0.671" di prima.

---

## 4. Correzione dei "numeri fantasma"

> **⚠️ Superseded by the CES + labour-market core — see README/§2.** Questa sezione
> è un **record storico** dello stadio `cobb-douglas-core` (σ=1, senza mercato del
> lavoro). I numeri "effettivamente misurati" qui sotto sono di **quello** stadio; il
> modello corrente su `main` (CES + mercato del lavoro) ha numeri diversi — vedi il
> README e §2. Tenuta per la lezione anti-drift, non come descrizione del core attuale.

La versione precedente di questo file (e la memoria di progetto) riportava come
**risultati raggiunti** i seguenti valori:

> K/Y ≈ 2.51–2.65 · quota salari = 0.671 ("match esatto di 1−α") · utilizzo
> capacità ≈ 0.89–0.94

**Questi numeri non sono mai stati misurati.** Sono **target di design**
proiettati in una conversazione di progettazione per un modello Cobb-Douglas che
non è mai stato costruito. In particolare "match esatto di 1−α" è privo di
referente: **nel codice realmente implementato non esiste alcun α** (né in Fase
1 esso vincola, né in Leontief esiste). Da trattare come **obiettivi di
calibrazione del core Cobb-Douglas**, mai come validazione empirica. Se
finissero in una tesi come "risultati", sarebbero fabbricati.

**Numeri effettivamente misurati** (ricognizione, seed espliciti, 500 step,
media ultime 50 osservazioni):

| Configurazione | K/Y | quota salari | util. capitale | disoccup. | I/Y |
|---|---|---|---|---|---|
| Fase 1 additiva, θ=0 (baseline) | 0.69–0.76 | 0.85–0.87 | 0.67–0.76 | — | 0 |
| Leontief, θ=0 (baseline) | ~0.7 | ~0.85 | 0.73 | ~49% | 0 |
| Leontief, θ=0.15 (investimento) | 2.47–2.52 | 0.84 | 0.20 | ~1.5% | 0.12–0.13 |

Nota: la quota salari misurata ≈ 0.84 ≈ `1/(1+markup)` con markup=0.2 — fissata
dal **pricing**, non dalla tecnologia (nessun α nel modello reale).

**Core di offerta Cobb-Douglas — numeri ora MISURATI** (3 seed, 2000 step, media
ultime 50). Questi **sostituiscono** i numeri fantasma qui sopra: il core esiste,
è stato eseguito, e i valori vengono dalla simulazione.

| ρ (retention) | Y | u | K/Y | I/Y | quota salari | quota profitti | buffer |
|---|---|---|---|---|---|---|---|
| 0.00 | 44.1 | 1.00 | 0.19 | 0.010 | 0.667 | 0.333 | 0.0 |
| 0.20 | 106.1 | 1.00 | 1.13 | 0.057 | 0.667 | 0.333 | 0.0 |
| 0.35 | 146.6 | 0.99 | 2.23 | 0.111 | 0.667 | 0.333 | 0.0 |
| **0.40** | **157.3** | **0.99** | **2.58** | **0.129** | **0.667** | **0.333** | **0.0** |

- Quota salari 0.667 = `1−α` e quota profitti 0.333 = `α`, **esatte per
  costruzione** (`markup = α/(1−α)`, α=1/3) — non più un "match" senza referente.
- K/Y e I/Y coincidono con le relazioni analitiche `K/Y = ρα/δ`, `I/Y = ρα` (§7).
- `buffer ≡ 0` a fine periodo: il conto d'impresa è infra-periodo, nessun
  sequestro di moneta.
- Confronto coi fantasma: K/Y 2.58 (era 2.51–2.65, ok); quota salari 0.667 (era
  0.671, ora con referente reale); **utilizzo 0.99, non 0.89–0.94** — l'economia
  è più capacity-constrained di quanto il target fantasma suggerisse (vedi §3).
- Parametri di calibrazione (`c0=1.0`, `wealth_effect=0.08`, `target_utilization=
  0.90`, `investment_floor=0.1`, `beta=0.5`): **scelti per raggiungere il regime,
  non da dati.** `wealth_effect=0.08` è alto vs MPC-ricchezza empirico ~0.03–0.05.
  Debito di ancoraggio bibliografico (roadmap punto 4), da saldare prima di
  chiamarli "calibrazione empirica".

---

## 5. Regola sui numeri, d'ora in poi

Ogni valore che entra in una tabella di risultati, in una figura o in un testo
deve essere **o misurato** (con seed, step e configurazione riproducibili) **o
dichiarato esplicitamente come target di design**. Non si registrano target come
risultati. Vale anche per la memoria di progetto.

---

## 6. Decisione architetturale: sequenziare il mercato del lavoro (ESEGUITA)

Il capitale deve tornare a mordere. Serve **sia** una struttura produttiva con
margine intensivo vivo **sia** un regime operativo in cui il capitale vincola
(vedi §7). Il mercato del lavoro Leontief non va integrato ora nella
Cobb-Douglas: raddoppierebbe le variabili in movimento nella fase di
calibrazione più delicata, e la roadmap lo colloca comunque al **punto 11**.

**Sequenza decisa:**
1. Ricostruire il **core di offerta** (Cobb-Douglas + finanziamento interno) su
   `cobb-douglas-core`, partendo da **`main`**, con **lavoro semplice** (L fisso
   / piena occupazione). Obiettivo: far tornare a mordere il capitale e
   calibrare pulito K/Y e quote fattoriali.
2. **Reintrodurre il mercato del lavoro dopo** (punto 11), reinnestando il
   lavoro del branch `labour-market-leontief` sulla fondazione Cobb-Douglas
   corretta.

Ripartire da `main` (non dal branch Leontief) perché la baseline Fase 1 ha già
lavoro semplice e imprese possedute dai capitalisti: ricostruire da lì cambia
due cose (produzione, finanziamento) e tiene il resto, invece di smontare prima
mercato del lavoro e governo.

---

## 6bis. Punto 11 — decisioni di design (task attivo)

**Fuori sequenza, DELIBERATAMENTE.** La roadmap (§8) colloca il punto 11 dopo 8,
9 e 10. Ci si va direttamente, saltando eterogeneità, markup endogeno e
aspettative adattive. È una **decisione presa consapevolmente** dal PI (a
differenza del salto fuori sequenza del branch Leontief, che fu scoperto a
posteriori): il punto 11 è ciò che completa la narrazione del modello, e gli 8–10
non ne sono prerequisiti. **Registrato qui perché non torni a sembrare una
discrepanza silenziosa.**

**Salario fisso `w̄`, non residuale.** In Leontief `output = A·L` (prodotto per
lavoratore costante) faceva sì che salario fisso ⟺ quota salari costante. In
Cobb-Douglas il prodotto per lavoratore è `A·(K/L)^α` e **quella coincidenza si
rompe**: o salario fisso (la disoccupazione taglia il monte salari ⇒ canale di
domanda vivo) o quota salari pinnata (ma monte salari invariante all'occupazione
⇒ mercato del lavoro cosmetico). Scelto **salario fisso**.

**Conseguenza: `markup` RIMOSSO.** Con prezzo fisso a 1 e salario parametrico, la
distribuzione la determina `w̄`; il profitto diventa residuo (`sales − w̄·L`).
`w̄` è il nuovo parametro distributivo.

> **La quota salari 0.667 cessa di essere un'identità e diventa un esito
> misurato.** Non è una perdita: un'identità vera per costruzione non valida
> nulla. Limite strutturale nuovo: l'impresa non assume mai dove `MPL < w̄`,
> quindi **quota salari ≤ 1−α sempre**, con uguaglianza solo al profit-max
> (knife-edge). Il target giusto è il **range empirico 0.60–0.68**, non 0.667.

**Occupazione a tre regimi:** `L = min(L_domanda, L_profitmax, N)` — demand-
constrained (disoccupazione keynesiana involontaria), profit-constrained
(disoccupazione classica; qui e solo qui quota salari = 1−α), labour-constrained
(piena occupazione).

**Trappola AK — invariante strutturale.** Con `w̄` fisso e lavoro illimitato,
`L_profitmax ∝ K` ⇒ `Y* ∝ K`: rendimenti costanti al capitale, crescita
illimitata, nessuno steady state. **Il tetto `L ≤ N` è ciò che restituisce i
rendimenti decrescenti**, non un dettaglio realistico. Da assertare in test.

**Ridefinizione dell'utilizzo (necessaria).** Con `L` scelto per soddisfare la
domanda attesa, `Y*` insegue `Y` e `u ≈ 1` per costruzione: l'acceleratore
riceverebbe un segnale morto. Capacità ridefinita al profit-max:
`Y*_firm = A·K^α·L_profitmax^(1−α)`.

**Il regime è un esito, non un requisito** — vedi la precisazione in §1
(wage-led vs profit-led). I criteri di accettazione devono chiedere di
**riportare quale vincolo morde**, non di garantirne uno.

**Debito di calibrazione che si ripaga qui:** `c0=1.0` e `wealth_effect=0.08`
erano cranked up per forzare il capacity-constraint in assenza di mercato del
lavoro. Ora possono scendere verso l'empirico (λ → 0.05, Slacalek 2009).

---

## 7. Architettura del core di offerta (IMPLEMENTATA — riferimento al codice su `cobb-douglas-core`)

> **⚠️ Superseded by the CES + labour-market core — see README/§2.** Descrive lo
> stadio `cobb-douglas-core` (σ=1, `markup`, nessun mercato del lavoro). Il core
> corrente su `main` generalizza la produzione a una **CES normalizzata** con
> elasticità σ e aggiunge il **mercato del lavoro endogeno** (salario fisso `w̄`,
> `markup` rimosso): equazioni e cornice nel README. Sezione tenuta come record
> dell'architettura di quello stadio.

- **Produzione:** Cobb-Douglas vera `Y* = A·K^α·L^(1−α)`, `Y = min(domanda, Y*)`.
  Capitale essenziale. α ≈ 1/3 come quota del capitale — **da ancorare a fonte
  primaria** (PWT / AMECO / FRED) nello step bibliografico; per ora valore
  standard di manuale, non citabile come misurato.
- **Coerenza distributiva (resa concreta):** con Cobb-Douglas la quota salari è
  determinata due volte (tecnologia `1−α` vs pricing `1/(1+markup)`), che in
  generale confliggono. Vincolo di allineamento: **`markup = α/(1−α)`**, così
  `1/(1+markup) = 1−α`. Con α=1/3 → markup ≈ 0.5 → quota salari ≈ 0.67. (È da
  qui che veniva il "0.671" — un target, non una misura.)
- **Finanziamento:** **utili trattenuti a livello d'impresa** (`retention_ratio
  = 0.40`; da ancorare a corporate finance). Regola implementata:
  `I = clip(ρ·profit·util_effect, floor, profit)` — investimento come **flusso**
  legato al profitto, cap = profitto corrente (nessun credito). L'impresa
  **trattiene esattamente ciò che investe** e distribuisce il resto come
  dividendi. Motivo: con capitale essenziale, il finanziamento da risparmio
  personale crea una spirale di collasso (I < δK → K crolla → output crolla); il
  finanziamento interno spezza il feedback. **`investment_floor`** come guardrail
  contro il capex nullo. (Nota: 0.40 supera il 0.35 delle note precedenti perché
  `K/Y = ρα/δ` mostra che 0.35 atterra a 2.33, sotto la banda 2.5–3.)
- **Vincolo SFC critico — come è stato risolto:** un primo tentativo con il
  conto d'impresa come **stock accumulato tra periodi** ha creato un **sequestro
  di moneta** (la ritenzione non investita si accumulava senza sbocco →
  spirale di domanda). Soluzione implementata: il conto d'impresa è un
  **passaggio infra-periodo** che torna a **zero ogni periodo** — l'impresa
  trattiene ciò che investe, paga i beni capitale, e distribuisce il resto come
  dividendi. Invariante testato: `money_buffer ≡ 0` a fine periodo. La moneta è
  conservata (incl. moneta in transito infra-periodo), deviazione ~1e-13.
- **Regime effettivo (nota, non più previsione):** il core è risultato
  **capacity-constrained ovunque** (u≈0.99 su tutto lo sweep, baseline incluso),
  non demand-constrained con slack come ipotizzato in fase di design. Il capitale
  morde (è ciò che vincola l'output), che è l'obiettivo; ma il regime keynesiano
  da domanda è **dormiente** — vedi la cornice di §3. Per portare l'economia
  capacity-constrained è servita più domanda del previsto (`c0=1.0`,
  `wealth_effect=0.08`): scelte di regime, non da dati.

---

## 8. Roadmap

**Fatto:**
- Core Cobb-Douglas + finanziamento interno (§7): costruito, calibrato,
  committato su `cobb-douglas-core` (19 test verdi).
- **Punto 11 — mercato del lavoro endogeno** (salario fisso `w̄`, occupazione
  `L = min(L_domanda, L_profitmax, N)`, `markup` rimosso, profitto residuo):
  costruito su `labour-market`, poi portato su `ces-production`. Design §6bis;
  esito **wage-led a σ=1** misurato.
- **Brief 04 — CES normalizzata** (elasticità σ, sweep e *sign frontier*): la
  produzione è ora `Y* = Y0·[π0·(K/K0)^r + (1−π0)·(L/L0)^r]^(1/r)` con
  `r = (σ−1)/σ`, che nidifica la Cobb-Douglas (σ=1) e la Leontief (σ→0). Il
  **segno di `dY/dρ` dipende da σ** (σ* ≈ 0.65 a c0=1.0).
- **Brief 05 — stack di robustezza**: pannello per-seed (20 seed), slope OLS su
  supporto viable comune, **bootstrap CI su σ***, sensibilità a supporto e ancora
  (Temple 2012), curvatura. Driver **riproducibile** `scripts/run_brief05.py`
  (thread BLAS pinnati); output in `results/ces_b05_*.csv`.
- **Consolidamento (brief 06)**: README, notebook, figure allineati al codice
  CES + mercato del lavoro; cornice onesta nel README; CSV spostati in `results/`;
  `engine.cpp` resta STALE. **README, notebook, figure e codice coincidono.**
- **Blocco bibliografico (punto 4)**: `parameter_notes.md` nel repo — fonte,
  stima, range e verdetto di ancoraggio per ogni parametro, **allineato ai default
  del codice**. Vedi §4 e §11.
- **Brief 07 — blocco salariale (punto 9, parte salario)**: salario endogeno via
  **wage curve** di Blanchflower–Oswald
  `w_t = max(w_min, w_bar·(max(U_{t-1},U_min)/U_REF)^(-η))`, fissato su `U_{t-1}`
  prima del mercato del lavoro (**step 0** della sequenza). `η=0` annida il modello
  a salario fisso **bit-for-bit** (check di annidamento **byte-identico** η=0 vs
  `ces_b05_stage_a_panel`: PASS su entrambi i c0, dev 0). `U_REF=0.2604666667`
  misurato allo scenario `ANCHOR_*` e congelato. **Esito headline (c0=1.0): σ*(η)
  SALE** 0.654→0.740 al crescere di η (l'empirico σ 0.40–0.60 resta **sotto** σ*):
  la flessibilità salariale **non ribalta** il wage-led, lo **rafforza** (il canale
  di domanda kaleckiano — paradosso dei costi — domina la sostituzione); la
  disoccupazione media sale con η (0.53→0.58). **c0=2.0 (secondario):
  destabilizzato** — l'angolo alto-σ/basso-ρ collassa con η (σ=1.25: 43% dei seed a
  η=0.15), σ* erratico/indefinito; il floor `w_min` **non morde mai** (collasso di
  viability, non artefatto del floor).
  - **Meccanismo del collasso c0=2.0 (VERIFICATO** su una traiettoria tracciata
    σ=1.5/ρ=0.40/η=0.10 — 6/6 seed collassano — e su uno sweep in σ a c0=2.0**):**
    la wage curve destabilizza **solo l'angolo ad alto σ** (σ≳0.8; collasso a
    σ≥1.25). Il salario **oscilla**: sale sopra `w̄` quando `U→0` (guard `U_min`:
    `w→~1.25`) e scende sotto quando `U` è alta; poiché a σ crescente `L_profitmax`
    è sempre più sensibile al salario, questo alimenta un'**oscillazione
    dell'occupazione** che **erode il capitale a ogni ciclo** (l'investimento non
    copre il deprezzamento) finché, a ρ bassa, l'economia collassa a `U=1`. Nella
    regione empirica σ≈0.5 lo stesso meccanismo lascia `w≈w̄`, **nessuna
    oscillazione, e il capitale cresce** (K 354→460). **L'ipotesi "a `U<U_REF` il
    salario sale sopra `w̄`" è confermata come *gamba* dell'oscillazione, ma il
    driver del collasso è l'erosione di capitale, non una spirale monotona al
    rialzo.** (Nota: l'ampiezza dell'oscillazione dipende dal guard `U_min`, una
    convenzione — candidato per un'analisi di sensibilità futura.)
  - **359 test verdi.** Driver
  `scripts/run_brief07.py` (due fasi, soglie di halt esplicite); CSV
  `results/ces_b07_*.csv`; figura `results/ces_b07_sigma_star_eta.png`. Design §6bis
  del brief; note parametri (η, U_REF, U_min, w_min, declassamento w̄) in
  `parameter_notes.md`.
- **Brief 08 — aspettative adattive sulla domanda (punto 10, parte DOMANDA)**:
  l'aspettativa d'impresa passa da statica (`Ye_t = D_{t-1}`) ad adattiva
  `Ye_t = Ye_{t-1} + λ_e·(D_{t-1} − Ye_{t-1})`, gain `λ_e` (codice:
  `expectation_gain`, default 1.0). `λ_e=1` annida il modello statico **bit-for-bit**
  (4 byte-check λ_e=1 vs `ces_b05`/`ces_b07`, **dev = 0.0**, PASS su tutti — sentinella
  anti-drift). Update interno a `step_production` (nessuno step nuovo); helper
  `adaptive_expectation` col branch esplicito λ_e=1; infrastruttura di pooling
  **single-pool** (`run_grid_panels`, 2 spawn di pool anziché 24). **Esito headline
  (E1, c0=1.0): σ\*(η; λ_e) λ_e-INVARIANTE entro CI** — a η=0 σ\*=0.654/0.686/0.674 a
  λ_e=1/0.5/0.25 (CI sovrapposte), a η=0.10 0.725/0.713/0.721; l'empirico σ 0.40–0.60
  resta **sotto** σ\* per ogni λ_e: **il wage-led è robusto al gain**, nessun finding
  di selezione del bacino. **E2 (c0=2.0): ipotesi di stabilizzazione NON CONFERMATA** —
  la regione di collasso è λ_e-invariante entro il rumore (celle a collasso pieno
  piatte; η=0.15 non monotono) e la cella di riferimento (σ=1.5, ρ=0.40, η=0.10)
  **collassa a K=0/U=1 a ogni λ_e**. Il collasso c0=2.0 è guidato dal canale
  salario→U→erosione di capitale (wage curve), che `λ_e` non tocca: smorzare
  l'aspettativa di **domanda** non stabilizza un'instabilità che non nasce dalla
  domanda. **378 test verdi.** Driver `scripts/run_brief08.py` (due fasi, gate E1 su
  perdita di supporto vs λ_e=1); CSV `results/ces_b08_*.csv`; figure
  `results/ces_b08_sigma_star_lambda.png`, `ces_b08_collapse_map.png`,
  `ces_b08_trace.png`. Note parametro (`λ_e`, Nerlove 1958, Evans & Honkapohja 2001)
  in `parameter_notes.md`. **Fuori scope:** aspettative su salari/prezzi/investimento
  (l'acceleratore usa `utilization_last_period`, un segnale realizzato).
- **Brief 09 — governo: sussidio a bilancio in pareggio (punto 15, forma minima)**:
  reinnestato il sussidio di disoccupazione a bilancio in pareggio dal ramo
  `labour-market-leontief`. Flat tax sul reddito maturato (`next_income`) finanzia un
  trasferimento uguale ai disoccupati, indicizzato al salario **corrente** `w_t`; step
  8 tra settlement investimenti e settlement famiglie. Un solo parametro economico:
  `benefit_replacement_rate` (rr, default 0.0). **Base imponibile su `max(0,·)`** (un
  dividendo residuo può essere negativo, misurato −0.007 a σ=1.5/c0=2.0/η=0.10) → 
  `Σ prelievi = Σ sussidi` esatto, SFC intatta. `rr=0` annida bit-for-bit (**byte-check
  rr=0 vs `ces_b05`/`ces_b07`: 4/4 PASS, dev=0.0**). Reporter `Tax_Rate`,
  `Benefit_Per_Head`, `Gov_Transfers`, `Tax_At_Cap` (diagnostica di saturazione). **Esiti
  (20 seed, `results/ces_b09_*`): E1** — dose-risposta rr∈{0,0.25,0.5,0.75}: nello
  scenario headline (c0=1.0, σ=0.5, η=0.10) U 0.566→0.373 e — punto teorico — **K
  299→436** (crowding-in in regime demand-constrained); cash-constrained 0.90 = tutti i
  90 lavoratori, invariante a rr (moltiplicatore intatto). **E2** — σ\*(η;rr) c0=1.0: a
  rr=0.5 σ\* **INDEFINITO** (`frac_undef`≈1.0), tutte le pendenze `dY/dρ` positive → il
  sussidio **elimina la regione wage-led** (σ\* spinto sopra 1.5); frontiera su U quasi
  ferma. **E3** — ipotesi di stabilizzazione c0=2.0 **FALSIFICATA: il collasso si
  ALLARGA** (celle con qualche collasso η=0.10 16→26, η=0.15 16→29; frac seed a U=1
  raddoppia); cella di riferimento collassa a K=0/U=1 sia a rr=0 sia a rr=0.5, ma a
  rr=0.5 la tassa è **fissata al cap** (τ=0.6, frac_at_cap=1.0) — strumento saturo.
  Meccanismo: base ~tutta salariale ⇒ trasferimento MPC-neutrale; sussidio prociclico
  (w_t giù a U alta); domanda extra amplifica l'oscillazione salario→U→erosione di
  capitale. **397 test verdi** (378 invariati + 19 nuovi). Driver `scripts/run_brief09.py`
  (due fasi, gate E2 su perdita di supporto vs rr=0); CSV `results/ces_b09_*.csv`; figure
  `ces_b09_dose_response.png`, `ces_b09_sigma_star_rr.png`, `ces_b09_collapse_map.png`,
  `ces_b09_trace.png`. Note parametro (`rr` ancorato OECD *Society at a Glance 2024* /
  Benefits and Wages; `max_tax`=0.6 convenzione) in `parameter_notes.md`. **Fuori scope:**
  spesa in beni/servizi, occupazione pubblica, debito, tassazione progressiva, salario di
  riserva.

- **Brief 10 — probe di viability dell'eterogeneità di impresa (punto 8: DECISIONE
  PRESA, feature NON implementata)**: dial sperimentale `productivity_spread` (default
  0.0, validato ∈[0,1)) che ventaglia le produttività d'impresa in modo mean-preserving
  (`A_i = A·(1 + spread·(2i−(n−1))/(n−1))`, media esatta in float, ogni impresa con la
  propria A_i **anche nell'aspettativa iniziale**). Nessuna modifica a flussi, sequenza,
  SFC. `spread=0` annida bit-for-bit (**byte-check vs `ces_b05`/`ces_b07`/`ces_b09`:
  3/3 PASS, dev=0.0**). Reporter `Dead_Firms` (K<0.5) e `TopK_Share` (quota di K delle
  prime 3), pure diagnostiche. **Esito: è una SCOGLIERA, non un gradiente** — sotto soglia
  nessuna impresa muore, uno step di griglia sopra **tutte e 10 sono morte** (Y=0, U=1,
  K→3.5e-34 allo step 2000). Soglia fra spread **0.10 e 0.125** (anchor c0=2.0/σ=1/η=0) e
  fra **0.125 e 0.15** (headline c0=1.0/σ=0.5/η=0.10). **Claim mean-field resa precisa:**
  Y resta dentro la banda inter-seed di spread=0 solo fino a **0.05** (anchor) / 0.125
  (headline); a 0.10 gli aggregati anchor si muovono in modo rilevabile e **verso l'alto**
  (Y 132.1→134.7, U 0.258→0.229) — la dispersione è **lievemente espansiva** fin quando
  non è fatale. Enunciato difendibile: *quasi-rappresentativo negli **aggregati** fino a
  ~±5%, viabile fino alla scogliera*. **Domino tracciato** (headline, spread=0.20, seed 0):
  l'impresa a bassa A si decapitalizza per prima (K 38→~0 allo step 250), le quote di spesa
  restano puntate su di lei (domanda distrutta) e i suoi licenziati perdono reddito
  (esternalità di domanda) → cadono anche le imprese ad alta A (K della più forte a 0 allo
  step 500, U→1). **E2 (sussidio brief 09 come cuscinetto): FALSIFICATO, peggiora** — a
  spread=0.125 headline ha 0/20 seed con imprese morte, a rr=0.5 ne ha **18/20** (7/20 in
  collasso pieno, bacino misto); soglia di collasso pieno invariata a 0.15. **Meccanismo
  verificato** (seed 8): il sussidio abbassa U (0.544→0.445), la wage curve **alza w_t**
  (0.836→0.853) e l'impresa a bassa A è la prima spinta sotto `I=δK` (a rr=0 steady state
  stabile K≈28/L=6; a rr=0.5 decapitalizzazione monotona a 1.8e-6 allo step 800). Stesso
  canale salario→U dei brief 07 e 09. **Confronto empirico qualitativo:** dispersione TFP
  intra-settore 90/10 ≈2:1 (Syverson 2004; Bartelsman & Doms 2000) vs soglia max/min
  ≈1.22–1.29 → **l'eterogeneità realistica è ben fuori dal range viabile**, perché manca
  il canale di riallocazione. **Unità diverse: nessuna mappatura quantitativa pretesa.**
  **Reperto collaterale (dai test):** anche a spread=0 le imprese **non** restano identiche
  — i link di consumo sono casuali, quindi `TopK_Share` parte da 0.30 a t=0 e si assesta a
  **0.35–0.38**: quasi-rappresentatività negli **aggregati, non nella sezione trasversale**.
  **438 test verdi** (397 invariati + 41 nuovi). Driver `scripts/run_brief10.py` (fase
  unica — il collasso È il deliverable, non c'è nulla da gattare; due pool raggruppati per
  σ); CSV `results/ces_b10_*.csv`; figure `ces_b10_aggregates_spread.png`,
  `ces_b10_domino_trace.png`. Note parametro in `parameter_notes.md`. **Fuori scope:**
  implementare il punto 8 come feature (selezione, riallocazione, rewiring, entry/exit) —
  tagliato, future work punto 12; distribuzioni di A diverse dal ventaglio lineare (il
  probe stabilisce esistenza e posizione della soglia, non la sua forma distribuzionale —
  limite dichiarato).

- **Brief 11 — chiusura dei debiti di ancoraggio (documentazione + un solo script)**:
  nessuna modifica a `src/`, nessun parametro cambiato, nessuna simulazione nuova (**438
  test invariati e verdi**). Chiude i tre debiti dichiarati prima della SA globale.
  **D1 — unità temporale: 1 periodo = 1 anno, dichiarato** (coerente con δ annuale e con
  l'elasticità Blanchflower–Oswald stimata su dati annuali; λ_e e rr sono quindi annuali).
  I 2000 step sono un **dispositivo di convergenza**, non una serie storica: tutti i
  risultati sono statica comparata su steady state. **D2 — ancoraggio flows-first del
  blocco capitale, con comparatore unico dichiarato** (capitale privato **non
  residenziale**, cioè d'impresa, su entrambi i lati). I/Y ancorato a **0.138–0.141**
  (PNFI/PIL, FRED `A008RE1Q156NBEA`, Q1 2025–Q1 2026); **misurato** sul modello (script
  §11) **0.158** (anchor) e **0.182** (headline) a ρ=0.40 — sopra l'ancora di 2 e 4 punti,
  con `ρ≈0.36` che la centra allo scenario **anchor** e l'headline che **non** la raggiunge
  dentro il supporto sweepato. **δ=0.05 declassato a CONVENZIONE dichiarata** (il δ
  implicito BEA è ≈0.090, gonfiato dall'IPP al 20–30%; le strutture sole stanno a 2–3%):
  **non ricalibrare a fine progetto**, cambierebbe ogni numero canonico senza comprare
  ancoraggio. **K/Y del modello (3.17 anchor / 3.64 headline) è un ESITO MECCANICO di
  g=0**: la chiusura contabile è `I/K = δ + g`, i dati la rispettano con g≈0.022 (K/Y
  business = 1.23), il modello ha g=0 (punto 13 tagliato) ⇒ `I = δK` ⇒ `K/Y = (I/Y)/δ`
  segue — verificato, `I/K` misurato = 0.0500. **Il modello non può matchare insieme I/Y e
  K/Y business senza crescita: limite strutturale dichiarato.** **Correzione registrata:**
  il vecchio §"sistema congiunto" **mescolava comparatori** (I/Y business con K/Y
  whole-economy da PWT/manuali) e da lì derivava δ come "ancorato" — errore dichiarato
  esplicitamente nelle note (regola §5: vale anche per la documentazione); cade anche
  l'identità `I/Y = ρα` (era del core Cobb-Douglas senza mercato del lavoro: **citare il
  misurato, mai la formula**). **D3 — `c0` dichiarato NON ancorabile per decisione:**
  è consumo autonomo in unità del modello, e le unità del modello non hanno tasso di
  cambio con i dati (numerario = 1); la sensitivity è il doppio regime `c0`∈{1.0, 2.0} già
  riportato in ogni brief, più la SA globale. **Non chiude** la tensione della
  disoccupazione fuori scala (di design, non di ancoraggio). Script
  `scripts/compute_anchoring_ratios.py` (legge i panel committati, **nessuna
  simulazione**, deterministico per costruzione, non coperto da pytest — dichiarato);
  CSV `results/ces_b11_anchoring_ratios.csv`. **Nota di provenienza:** le tre serie FRED
  sono citate con ID e data ma la ri-verifica automatica non è stata possibile (FRED
  risponde 403 a fetch programmatici) — dichiarato nelle note.

- **Brief 12 — proprietà d'impresa e SFC fuori dal default (prerequisito della SA
  globale)**: correzione di un **bug latente**, nessun parametro nuovo, nessuna modifica a
  flussi o sequenza. La proprietà si assegnava ciclando sulle **famiglie**
  (`firms[i % num_firms]` per `i < num_capitalists`): biiezione **solo** al default
  (10 capitalisti, 10 imprese). **Sotto 0.10 — moneta distrutta** (imprese senza
  proprietario: `dividend_pool` e residuo di `money_buffer` svaniscono dentro
  `if self.owner is not None`): misurato, moneta 400.00 → **11.34** a `pct=0.05`,
  → **46.15** a 0.08, → **6.14** a 0.02, in 200 step. **Sopra 0.10 — ricchezza contata
  due volte:** riferimenti `owned_firm` obsoleti ancora sommati in `net_worth()`,
  Σ net worth **840.0 contro K=400.0 (2.10×)** a `pct=0.20` (5.25× a 0.50).
  **Fix:** ciclo sulle **imprese** (`firm.owner = capitalists[j % n_cap]`), in un secondo
  loop che **non estrae dall'RNG** (la sequenza dei `random.sample` dei link di consumo è
  invariata); `Capitalist.owned_firm` → **`owned_firms` (lista)**, `net_worth()` somma
  sulla lista (nessun alias di compatibilità: l'ambiguità silenziosa è ciò che ha prodotto
  il difetto); `ValueError` se i capitalisti sono 0. **Semantica dichiarata:** un
  capitalista può possedere più imprese (n_cap < n_firms) o nessuna (n_cap > n_firms —
  famiglia a MPC bassa con solo reddito da lavoro). **Annidamento: al default
  `j % 10 == j`**, quindi assegnazione identica alla precedente — byte-check di una fetta
  dei panel committati (`ces_b05`/`ces_b07`/`ces_b09`/`ces_b10`, 440 celle, 2000 step,
  20 seed, artifact-su-disco): **7/7 PASS, max_abs_dev = 0.0**; nessun risultato committato
  si muove. **463 test verdi** (438 invariati + 25 nuovi: SFC parametrizzata su
  `pct_capitalists ∈ {0.02, 0.05, 0.10, 0.15, 0.20, 0.50}`, copertura della proprietà,
  assenza di doppio conteggio, annidamento al default, determinismo fuori dal default,
  validazione). Script `scripts/check_brief12_nesting.py` (**non un driver**: non genera
  scienza nuova, ri-esegue una fetta e confronta); CSV `results/ces_b12_byte_check.csv`,
  `ces_b12_nesting_slice.csv`; note in `parameter_notes.md` (`pct_capitalists` **ora
  sweepabile**, range SA 0.05–0.20). **Lezione metodologica registrata in §9:** l'invariante
  SFC era testato **solo al default** — è esattamente ciò che una SA globale avrebbe
  calpestato in silenzio, producendo indici di sensitivity su un modello che perde moneta.
  **Fuori scope:** la SA globale (brief successivo); strutture di proprietà più ricche
  (quote frazionarie, mercato azionario, proprietà incrociata) = future work dichiarato.

- **Brief 13 — SENSITIVITY ANALYSIS GLOBALE (punto 5), l'ultima analisi prima della
  stesura.** Nuova dipendenza **SALib** (pinnata in `requirements.txt`). Nessuna modifica a
  meccanismi o parametri: la SA misura. Due aggiunte tecniche dichiarate — reporter
  `Capitalist_Consumption` (**fuori** da `_PANEL_METRICS`, viaggia sull'override `metrics`
  del brief 08) e `u_min` **esposto** come parametro opzionale (`None` = il derivato
  `1/N`, annidamento bit-for-bit testato), perché §2 lo vuole sweepato e il debito del
  brief 07 non era altrimenti pagabile.
  - **Task 0 — audit dei tre parametri strutturali congelati.** `num_firms ∈ {5,10,20}` ×
    `num_households ∈ {50,100,200}`: moneta conservata ovunque (peggior deviazione
    **2.1e-12**), `money_buffer ≡ 0`, copertura proprietà 9/9, determinismo per seed.
    **Nessun difetto analogo al brief 12.** Ma l'audit ha trovato il motivo *economico*
    per congelarli: `initial_capital` è **per impresa**, quindi
    `num_firms·initial_capital/num_households` è il capitale per lavoratore a t=0 — a
    **1.0 l'economia muore** (K→0, U→1), a 2.0 vive, a 4.0 vive meglio. Sono **selettori
    di bacino**, non di scala; sweeparli confonderebbe isteresi e sensitivity.
  - **Disegno.** `retention_ratio` è il **trattamento** (ρ_lo=0.35, ρ_hi=0.55) con
    **common random numbers**; 16 parametri uniformi (scelta di ignoranza dichiarata);
    QoI primaria il **segno**, non il livello. **Pilot** (32 punti) per fissare `n_seed`
    su evidenza: noise ratio 0.207/0.170/0.111 a 3/5/10 seed, scala come 1/√n. **Morris**
    k=17 r=20 con **regola di sfoltimento congelata nel sorgente PRIMA** di guardare i
    risultati → 11 sopravvissuti. **Sobol** N=256, CI bootstrap.
  - **⚠️ LIMITE DI DISEGNO, dichiarato e da risolvere prima della stesura.** La QoI di §3 è
    una **corda** a due punti (ρ=0.35 vs 0.55), ma il brief 05 aveva già misurato che
    `Y(ρ)` è **a U con la svolta DENTRO il supporto in 19 celle su 22**: su una curva a U il
    segno della corda dipende da dove la si prende e può differire dalla pendenza OLS
    sull'intero supporto (il metodo del brief 07). Quindi l'headline è esatto su *"la corda
    [0.35,0.55] è negativa"*, **non** su *"la derivata è negativa"*. Il brief 13 ha ereditato
    la QoI dal proprio §3 senza raccordarla al reperto di curvatura del brief 05.
    **Resta valido:** gli indici decompongono correttamente *quella* quantità, `viable` non
    è una differenza e non è toccata, i sottoprodotti sono su livelli/viability. **Da
    rifare:** segno su ≥3 valori di ρ per punto (~1,5× il costo).
  - **Esito headline: `P(corda < 0 | viable) = 0.095 ± 0.007`, frazione viable 0.483.**
    **Il wage-led è l'eccezione, non la regola**, e metà dello spazio empirico non è
    viable. **`delta` domina tutto** (`ST`≈1.00 sulla viability): a δ∈[0.075,0.09]
    **0/832 punti sopravvivono**, e δ=0.05 siede appena dentro il bordo — il brief 11
    aveva ragione a non ricalibrare, ma per la ragione sbagliata. **`sigma` è irrilevante
    nella banda empirica** (`ST`=0.024): **la frontiera σ\* del brief 07 non sopravvive
    alla globalizzazione** — era condizionata alla cella in cui fu misurata. `ST ≫ S1`
    ovunque: modello dominato dalle interazioni, come previsto.
  - **Check σ largo (0.30–1.00, N=128, secondario):** viability identica (0.483),
    `P(corda<0|viable)` **raddoppia a 0.201**, concentrata sopra σ≈0.65 (per bin: 0.042 /
    0.057 / **0.338** / **0.380**). **La soglia cade dove il brief 04/07 mette σ\*, ma la
    DIREZIONE è invertita** rispetto a come la conclusione è scritta.
    **DUE CAUSE CANDIDATE, NON DISTINTE — e nessuna va scritta come "la" spiegazione
    finché un esperimento non le separa.** **(a) corda vs derivata:** il brief 07 usa OLS
    su tutto [0.35,0.65], qui è una corda [0.35,0.55], e su una `Y(ρ)` a U con svolta dentro
    il supporto le due possono avere segno opposto. **(b) condizionale vs marginale:** σ\* è
    misurato con *tutti gli altri parametri fissi*, la SA **marginalizza** su 15 parametri
    sorteggiati; in un modello con `ST ≫ S1` non c'è ragione perché coincidano, e l'ipotesi
    ha già riscontro nei dati di questo brief — **`ST(sigma) = 0.024`**, cioè marginalmente
    σ spiega ~2% della varianza. Un σ\* condizionale robusto e un σ marginale quasi inerte
    sono compatibili. **Esperimento che le separa:** corda *e* OLS su ≥3 valori di ρ, a due
    regimi (altri parametri fissi ai default del brief 07 / marginalizzati). Finché non
    esiste, **la contraddizione resta aperta e va riportata come aperta**. Che la
    **posizione** si riproduca con due metodi indipendenti è evidenza *a favore* della
    frontiera; è il **segno** a non essere confrontabile. **È il punto su cui la tesi
    rischia di affermare l'opposto del vero.**
  - **Sottoprodotti.** **Kalecki: confermato in LIVELLI** — `capitalist_mpc` alto vs basso
    dà consumo capitalisti +10.83 e profitto **+11.56 (+22%)**, corr **+0.83**; sulla
    *quota* −0.06 (l'output cresce più in fretta). È l'**intervento** che il brief 11
    dichiarava impossibile con l'identità tautologica. **Punto 10-bis: ipotesi
    ROVESCIATA** — a β<0.1 **zero punti wage-led su 338** e viability 0.385 contro 0.533 a
    β≈1: il segno wage-led è in larga misura *prodotto* dall'acceleratore, e β governa
    **sia** il segno **sia** la sopravvivenza.
  - **Due reperti metodologici, entrambi trovati DALLA SA** (dettagli in
    `parameter_notes.md` §"Tensioni aperte" 7bis e 8): (a) il criterio **`dev = 0.0`** dei
    byte-check **non è riproducibile nel tempo** — `7c2670f` oggi devia di 1 ULP dai propri
    risultati, otto ipotesi escluse per misura, causa non identificata; ampiezza **max 2,1
    ULP, zero flip di regime**, nessuna conclusione economica si muove. (b) **bug latente a
    σ→1** in `ces_labour_for_demand` (`OverflowError`, banda |r|<5.7e-4 che `R_EPS=1e-6`
    non copre): stessa forma del difetto del brief 12, mai toccato dalle griglie perché
    usano σ=1.0 **esatto**. Corretto instradando al ramo Cobb-Douglas, non saturando.
  - **512 test verdi.** Driver `scripts/run_brief13.py` (fasi `pilot`/`morris`/`sobol`/
    `wide`/`report`, seed di campionamento fissato e dichiarato, ambiente registrato in
    `ces_b13_environment.json`); CSV `results/ces_b13_*.csv` + 3 figure. **Fuori scope:**
    ricalibrare qualunque parametro sulla base della SA (sarebbe calibrazione mascherata
    da robustezza); consolidamento del notebook (b07–b13, subito dopo).

**Attivo:** nessun task di implementazione in corso. Prossimo blocco sotto.

**Successivi:** ~~8) produttività eterogenea tra imprese~~ — **CHIUSO dal brief 10:
decisione presa, lato imprese dichiarato quasi-rappresentativo con evidenza misurata,
feature non implementata, riallocazione = future work (punto 12)**; **9) prezzi endogeni
(parte salario FATTA col brief 07; resta il PREZZO — vedi sotto)**; **10) aspettative
adattive — parte DOMANDA FATTA col brief 08** (σ\* λ_e-invariante; ipotesi di
stabilizzazione c0=2.0 non confermata); **resta l'aspettativa sull'INVESTIMENTO**
(oggi l'acceleratore usa `utilization_last_period`, un segnale realizzato, non
un'aspettativa — punto 10-bis);
12) entrata/uscita/fallimento imprese; 13) cambiamento tecnologico (crescita di
A); 14) banche e credito (estende la matrice SFC: depositi, prestiti);
**15) politica monetaria e fiscale — il sussidio a bilancio in pareggio è REINNESTATO
(brief 09, forma minima)**; restano spesa in beni/servizi, occupazione pubblica, debito
pubblico e tassazione progressiva (future work dichiarato in `brief_09_government.md` §8);
16) stesura metodologia e risultati.

> **Punto 9 riscritto — e parzialmente FATTO col brief 07.** Diceva: "markup
> endogeno che risponde a domanda/concorrenza; il markup fissa oggi le quote
> fattoriali, quindi endogenizzarlo tocca la quota salari". **Obsoleto dal punto
> 11**, che rimuove il parametro `markup` (§6bis). Restavano due cose da
> endogenizzare: il **salario `w̄`** e il **prezzo**. **Il salario è FATTO (brief
> 07):** wage curve di Blanchflower–Oswald, `w̄` declassato a punto di
> normalizzazione, `η` nuovo parametro distributivo (vedi la voce "Fatto" sopra e
> `parameter_notes.md`). **Resta aperto il PREZZO** (oggi numerario = 1) — punto
> **9-bis**, esplicitamente fuori scope nel brief 07 (niente spirale
> prezzi-salari). Nota: già senza prezzi endogeni il **markup implicito**
> (`prodotto medio / w_t`) è un **esito**. Per il blocco prezzi serviranno dati sui
> markup (De Loecker, Eeckhout & Unger 2020).

**Ricerca bibliografica (continua, primo blocco FATTO → `parameter_notes.md`):**
ogni parametro deve avere una fonte o essere dichiarato come scelta di
modellazione. Stato attuale:
- **Ancorati:** α (1/3), quote fattoriali, **I/Y** (ancora BEA `A008RE1Q156NBEA`
  = 0.138–0.141, brief 11) e **`retention_ratio` (0.40)** — ρ fissa I/Y, quindi si
  ancora lì e non al payout.
  > **⚠️ Corretto dal brief 11.** Questa riga diceva che δ (0.05) e ρ erano ancorati
  > **congiuntamente**, perché "dati `K/Y≈2.6` e `I/Y≈0.13`, `I=δK` impone δ≈0.05".
  > **Quella derivazione mescolava comparatori** (I/Y business con K/Y whole-economy)
  > ed è stata ritirata. Ora: **δ = 0.05 è una CONVENZIONE dichiarata** (BEA implica
  > ≈0.090 con IPP; strutture 2–3%), e **K/Y non è un'ancora ma un esito meccanico di
  > g=0**. Resta vero il monito operativo — **non ricalibrare δ "verso il centro della
  > letteratura"** — ma perché invaliderebbe ogni numero canonico, non perché 0.05 sia
  > implicato. Vedi `parameter_notes.md`, §"Il sistema congiunto" (riscritto).
- **Scelte di regime dichiarate (non stime):** `c0`, `wealth_effect`,
  `target_utilization`, e l'utilizzo realizzato 0.99 (l'empirico è ~0.80).
  Ancoraggio **rimandato al punto 11**, dove λ può scendere a ~0.05.
- **Scelte di modellazione senza referente:** `investment_floor`, `beta` — si
  trattano in sensitivity analysis (punto 5), non con l'ancoraggio.
- **Nuovi dal punto 11, da dichiarare:** `w̄`, `N`. Per un eventuale reinnesto del
  governo (punto 15): `benefit_replacement_rate`, `max_tax`, tarati nel branch
  Leontief senza ancoraggio.

~~**Punto 5 (analisi di sensibilità globale): RIMANDATO PER DECISIONE**~~ — **FATTO col
brief 13.** Entrambi i prerequisiti sono stati saldati prima di eseguirla:
`pct_capitalists` reso sweepabile dal brief 12, e `num_firms`/`num_households`/
`initial_capital` auditati dal Task 0 del brief 13 (nessun difetto; congelati come
**selettori di bacino** con la ragione misurata, non asserita).

**Debito residuo:** ~~verificare I/Y con una serie BEA primaria~~ e ~~fissare
l'unità temporale del periodo~~ — **entrambi CHIUSI dal brief 11** (I/Y verificato
contro `A008RE1Q156NBEA`, con esito: il modello sta **sopra** l'ancora, non "match
incoraggiante"; periodo = 1 anno dichiarato). Aperto: la **sensitivity di `U_min`**
(convenzione della wage curve, brief 07 — dentro la SA globale, punto 5); e
**notebook: aggiungere le sezioni "wage curve"
(σ*(η), brief 07) e "aspettative adattive" (σ*(η;λ_e) + mappa di collasso,
brief 08) al prossimo consolidamento** — i brief 07 e 08 hanno lasciato le figure
(`ces_b07_sigma_star_eta.png`, `ces_b08_sigma_star_lambda.png`,
`ces_b08_collapse_map.png`, `ces_b08_trace.png`) in `results/` e referenziate dal
README, ma il notebook copre ancora solo brief 04/05. **Il brief 08 non aggrava né
salda questo debito** (i risultati λ_e sono nel README; notebook al consolidamento).

---

## 9. Vincoli / invarianti — DA RIPORTARE ESPLICITAMENTE IN OGNI BRIEF

Claude Code non conosce la storia del progetto e non vede queste conversazioni.
Ogni brief deve elencare gli invarianti pertinenti come non negoziabili.

- **Stock-flow consistency — su tutto lo spazio dei parametri, e testata lì:**
  nessuna creazione/distruzione di moneta nel settlement. Con il finanziamento a
  utili trattenuti, la ritenzione **non deve** rompere la conservazione (profitti
  trattenuti = posta monetaria d'impresa, da aggiungere alla grandezza conservata).
  *(Riformulato dal brief 12. Diceva solo "nel settlement", e i test lo verificavano
  **solo alla configurazione di default**: `pct_capitalists` fuori dal default
  distruggeva moneta — 400.00 → 11.34 in 200 step a 0.05 — perché le imprese senza
  proprietario non distribuivano nulla. Un invariante testato in un punto vale in
  quel punto. Ogni invariante va parametrizzato sui parametri che la SA globale
  vorrà sweepare, **prima** della SA.)*
- **Sequenza del periodo** in `model.py`, esplicita e motivata nel docstring.
  Sequenza **effettiva sul codice committato** (aggiornata al brief 09):
  wage curve (step 0, brief 07) → mercato del lavoro → domanda → piani di
  investimento → registrazione domanda → produzione/razionamento → contabilità
  imprese → **settlement investimenti** → **governo** (step 8, brief 09: sussidio a
  bilancio in pareggio, `rr=0` no-op) → **settlement famiglie**. Nota: il settlement
  investimenti precede il governo (che precede le famiglie), così la tassa colpisce
  il reddito interamente maturato e il sussidio arriva col medesimo lag di un salario.
  *(Correzione 2026-07: questo file elencava l'ordine inverso — famiglie prima di
  investimenti — in contraddizione col codice committato e col README. Il drift è
  durato dalla riscrittura del core al punto 11. Il documento anti-drift era
  driftato: è il motivo per cui va riletto contro il codice a ogni brief.)*
  Ogni deviazione va dichiarata e giustificata.
- **Determinismo per seed** e **test verdi** dopo ogni modifica.
  > **⚠️ Reperto del brief 13 — il determinismo per seed regge, l'uguaglianza byte a
  > distanza di tempo NO.** Il codice di `7c2670f`, il cui byte-check riportò *7/7 PASS,
  > dev = 0.0*, oggi devia di **1 ULP** sulle stesse celle. Otto ipotesi escluse per
  > misura (reporter, `u_min`, riduzione pandas, modifiche brief 13 via checkout,
  > pool vs processo principale, `scipy`, P-core vs E-core, versioni di libreria):
  > **causa non identificata**. Ampiezza su 160 celle × 24 metriche: **max 2,1 ULP, non si
  > amplifica, zero flip di regime** — nessuna conclusione economica si muove, e dentro
  > una sessione il determinismo per seed è intatto (3/3). **Non ho riscritto il criterio
  > dentro il brief che lo viola** (sarebbe post-hoc): la proposta — tolleranza ULP
  > dichiarata + check di regime a tolleranza **zero** — è registrata in
  > `parameter_notes.md` §"Tensioni aperte" 7bis per il brief successivo.
- **README, codice e figure coerenti tra loro** (è già emerso un disallineamento
  documentale in passato — la spec "Fase 2" fantasma: non deve ripetersi).
- **Ancoraggio bibliografico:** ogni scelta di modellazione e ogni parametro
  motivato su due piani — teorico ed empirico (fonte citabile). Se una fonte non
  esiste o non è nota, **dichiararlo e cercarla, non inventarla.**

---

## 10. Flusso di lavoro e divisione dei ruoli

- **L'implementazione del codice è di Claude Code**, che lavora sul repository.
- **Queste conversazioni** servono a: progettazione economica e architetturale,
  ricerca bibliografica e stime dei parametri, analisi e interpretazione dei
  risultati, revisione critica, scrittura. **Non** implementazione.
- Quando una decisione è matura, l'output è un **brief di implementazione per
  Claude Code**, autosufficiente: cosa cambiare e dove (file/funzioni), equazioni
  e parametri con valori e fonti, invarianti da preservare (§9), test da
  aggiungere/aggiornare, criteri di accettazione (benchmark attesi). Niente
  implementazioni complete da copiare a mano: al massimo pseudocodice.
- Distinguere sempre lo stato dei tre branch (§2) quando si ragiona sul modello.

---

## 11. Struttura del codice

- `src/agents.py` — **brief 13: guardia numerica in `ces_labour_for_demand`** — la banda
  |r| < 5.7e-4 attorno a σ=1 andava in `OverflowError` (il termine `−log1p(−pi0)` non
  svanisce con r) e ora è instradata al ramo Cobb-Douglas, che è il limite vero; `R_EPS`
  **non** è stato allargato, la guardia è locale e la costante `_LOG_HUGE` è dichiarata.
  Firm (CES normalizzata, salario dalla wage curve, finanziamento
  interno, aspettativa adattiva di domanda), Household, Capitalist (brief 12:
  **`owned_firms` lista** al posto di `owned_firm`, `net_worth()` che somma sulla lista
  — nessun doppio conteggio, nessun alias di compatibilità); helper CES
  (`ces_capacity`, `ces_labour_*`, `ces_mpl`, …) e `adaptive_expectation` (brief 08,
  branch esplicito λ_e=1). Nessuna modifica funzionale al brief 09: solo docstring
  aggiornati dove i disoccupati "earn nothing" (ora salvo il sussidio brief 09). Nessuna modifica al brief 10: la `A` d'impresa era già un attributo
  di `Firm`, il ventaglio la popola dal modello
- `src/model.py` — MacroModel: mercato del lavoro, sequenza del periodo (step 0 =
  wage curve, brief 07; update aspettativa adattiva dentro lo step di produzione,
  brief 08; **step 8 = governo, brief 09**), settlement, metriche (incl.
  `Expected_Demand` brief 08; `Tax_Rate`/`Benefit_Per_Head`/`Gov_Transfers`/`Tax_At_Cap`
  brief 09); ancore di normalizzazione `ANCHOR_*`, costante `U_REF` e helper
  `wage_from_curve` (brief 07); parametro `expectation_gain` (λ_e, default 1.0,
  validato ∈[0,1]); metodo `government()` e parametri `benefit_replacement_rate`
  (rr, default 0.0, validato ≥0, branch esplicito rr=0) e `max_tax` (0.6, validato
  ∈[0,1]) (brief 09); helper `productivity_fan` (ventaglio mean-preserving, branch
  esplicito spread=0), parametro `productivity_spread` (default 0.0, validato ∈[0,1)),
  costanti `DEAD_FIRM_K`/`TOPK_N` e reporter `Dead_Firms`/`TopK_Share` (brief 10);
  assegnazione della proprietà **ciclando sulle imprese**, in un loop separato che non
  tocca l'RNG, e validazione `pct_capitalists` ⇒ almeno 1 capitalista (brief 12)
- `src/experiment.py` — runner Monte-Carlo, sweep ρ, griglia (σ, ρ) e sign
  frontier (brief 04), stack di robustezza brief 05 (`run_grid_panel`,
  `bootstrap_sigma_star`, `slopes_by_sigma`, `quadratic_curvature`, …); `eta`,
  `expectation_gain` e `benefit_replacement_rate` passano al modello via `**params`,
  come `c0` (nessuna modifica di firma al brief 09); `run_grid_panels`
  (brief 08: **single-pool**, più config in un solo pool, `metrics` override); `productivity_spread`
  passa via `**params` come gli altri (nessuna modifica di firma al brief 10); **brief 13:
  blocco SA** — `run_design_points` (valuta i punti di design ai due ρ con **CRN**, pool
  singolo; l'intero vettore di parametri viaggia dentro `params` perché nella SA ogni punto
  ha la **sua** σ, cosa che `run_grid_panels` — una sola lista `sigmas` per tutte le config
  — non può esprimere) e `qoi_from_runs` (distingue `slope_raw`, **misurata ovunque** e
  usata dalla decomposizione, da `slope`, **condizionale** ai punti viable e mai imputata);
  costanti `SA_RHO_LO/HI`, `SA_U_COLLAPSE`, `SA_K_COLLAPSE`, `SA_METRICS`
- `scripts/run_brief04.py` — driver **riproducibile** dello sweep (σ, ρ) e della
  sign frontier del brief 04; rigenera 5 dei 6 `results/ces_*.csv` (thread BLAS
  pinnati). **Non** rigenera `ces_decomposition.csv` (vedi sotto).
- `scripts/run_brief05.py` — driver **riproducibile** degli stage A/B/C del brief
  05; rigenera `results/ces_b05_*.csv` (thread BLAS pinnati per determinismo)
- `scripts/run_brief07.py` — driver **riproducibile** dello sweep σ×ρ×η×c0 del
  brief 07 (wage curve); due fasi (recon 3-seed con soglie di halt esplicite →
  panel 20-seed), check di annidamento byte-identico η=0 vs `ces_b05_stage_a_panel`,
  σ*(η) sul supporto comune-across-η; rigenera `results/ces_b07_*.csv`
- `scripts/run_brief08.py` — driver **riproducibile** dello sweep σ×ρ×η×λ_e×c0 del
  brief 08 (aspettative adattive); due fasi in **single-pool** (recon 3-seed con gate
  E1 su perdita di supporto vs λ_e=1 → panel 20-seed), 4 byte-check λ_e=1 vs
  `ces_b05`/`ces_b07` (artifact-su-disco), σ*(η;λ_e) sul supporto comune-across-config,
  mappa di collasso E2 vs b07 e trace della cella di riferimento; rigenera
  `results/ces_b08_*.csv` + 3 figure
- `scripts/run_brief09.py` — driver **riproducibile** del brief 09 (governo); 8 config
  di griglia `(c0, η, rr)` in **single-pool**, due fasi (recon 3-seed con gate E2 su
  perdita di supporto vs rr=0 → panel 20-seed). Tre esperimenti: **E1** dose-risposta
  fiscale (2 scenari × rr∈{0,0.25,0.5,0.75}, con `Cash_Constrained` e `Tax_Rate`),
  **E2** σ*(η;rr) c0=1.0 bootstrap CS, **E3** mappa di collasso c0=2.0 (con `mean_tax`,
  `frac_periods_at_cap`) + trace della cella di riferimento (con `Tax_At_Cap`). 4
  byte-check rr=0 vs `ces_b05`/`ces_b07` (artifact-su-disco, dev=0.0); rigenera
  `results/ces_b09_*.csv` + 4 figure
- `scripts/run_brief10.py` — driver **riproducibile** del brief 10 (probe di
  eterogeneità); 3 scenari (S1 anchor, S2 headline, S3 = S2 + rr=0.5) × 7 spread × 20 seed
  a ρ=0.40, **fase unica** (il collasso è il deliverable, niente da gattare), due pool
  raggruppati per σ (`run_grid_panels` prende una sola lista `sigmas`). Byte-check spread=0
  vs `ces_b05`/`ces_b07`/`ces_b09` (artifact-su-disco, 3/3 dev=0.0); soglie di viability a
  convenzione dichiarata (`THRESHOLD_FRAC`=0.5) e trace del domino con K dell'impresa più
  debole e più forte; rigenera `results/ces_b10_*.csv` + 2 figure
- `scripts/compute_anchoring_ratios.py` — **brief 11**, l'unico codice nuovo del brief
  e **non un driver di simulazione**: legge i panel già committati
  (`ces_b05_stage_a_panel.csv` → cella anchor, `ces_b07_stage_a_panel.csv` → cella
  headline), riduce a I/Y, K/Y e I/K per scenario e ρ (convenzione dichiarata: media
  **sui seed** del rapporto **per-seed**, non rapporto delle medie) e scrive
  `results/ces_b11_anchoring_ratios.csv`. Nessuna simulazione, nessun RNG, nessun
  parallelismo ⇒ **deterministico per costruzione**; **non coperto da pytest**
  (dichiarato: non c'è comportamento del modello da pinnare). Emette anche `I/K`, che
  è la verifica della chiusura `I = δK` a g=0 (misurato 0.0500 = δ)
- `scripts/check_brief12_nesting.py` — **brief 12**, e **non un driver di simulazione**:
  non produce scienza nuova e non rigenera nessun panel committato. Ri-esegue una **fetta**
  dei panel (7 config × 20 seed × 2000 step = 440 celle, sia `c0`, η on/off, governo on/off,
  dispersione on/off) col codice corrente e la confronta **artifact-su-disco** con le righe
  committate: è ciò che rende falsificabile la claim di annidamento del fix di proprietà.
  Fetta e non griglia intera perché la claim è **meccanica** (`j % 10 == j`): una cella
  rappresentativa per referente la falsifica se è sbagliata. Scrive
  `results/ces_b12_byte_check.csv` e `ces_b12_nesting_slice.csv`; exit code ≠ 0 su FINDING
- `scripts/run_brief13.py` — **brief 13**, driver della SA globale. Fasi separabili
  (`pilot` → `morris` → `sobol` → `wide` → `report`), thread BLAS pinnati prima di numpy,
  **seed di campionamento SALib fissato e dichiarato** (`SAMPLE_SEED`), ambiente registrato
  in `results/ces_b13_environment.json`, **regola di sfoltimento Morris congelata nel
  sorgente** (`MORRIS_KEEP_RULE`) prima di qualunque esecuzione. `--reuse-runs` ri-analizza
  le run Morris salvate senza ri-simulare; `--phase report` produce sottoprodotti e figure
  leggendo i CSV committati, **senza simulazione**. La matrice di design viaggia **con** le
  QoI (`ces_b13_*_design.csv`), così le analisi a valle non dipendono dal campionatore che
  si riproduce
- `notebooks/01_Endogenous_Investment.ipynb` — sweep ρ a σ=1 (wage-led) + sweep σ
  con sign frontier; figure `retention_sweep.png`, `ces_sign_frontier.png`
- `results/` — output misurati committati. `ces_b13_*.csv` + `ces_b13_environment.json`
  e 3 figure (brief 13) → rigenerati da `run_brief13.py` (fasi separabili; `--phase report`
  non simula). `ces_b12_byte_check.csv` e
  `ces_b12_nesting_slice.csv` (brief 12) → rigenerati da `check_brief12_nesting.py`.
  `ces_b11_anchoring_ratios.csv` (brief 11) →
  rigenerato da `compute_anchoring_ratios.py`. `ces_b10_*.csv` (brief 10) → rigenerati
  da `run_brief10.py`. `ces_b09_*.csv` (brief 09) → rigenerati
  da `run_brief09.py`. `ces_b08_*.csv` (brief 08) → rigenerati
  da `run_brief08.py`. `ces_b07_*.csv` (brief 07) → rigenerati
  da `run_brief07.py`. `ces_b05_*.csv` (brief 05) → rigenerati
  da `run_brief05.py`. `ces_sigma_rho_grid.csv`, `ces_derivatives*.csv`,
  `ces_sign_frontier*.csv` (brief 04, 5 file) → rigenerati da `run_brief04.py`.
  **`ces_decomposition.csv` è ARCHIVIATO: generatore non committato, non
  riproducibile** (analisi ad hoc di spiazzamento del lavoro; i suoi numeri non
  sono citati in alcun documento). Da ricostruire con spec dichiarata se servirà.
- `tests/test_model.py`, `tests/conftest.py` — SFC, determinismo, contabilità del
  lavoro, nesting CES, pin di regressione (tolleranza), stack di robustezza,
  wage curve (brief 07: annidamento η=0, lag U_{t-1}, canale di sostituzione),
  aspettative adattive (brief 08: convergenza geometrica, annidamento λ_e=1, lag,
  SFC/determinismo a λ_e<1, single-pool), governo (brief 09: bilancio in pareggio
  esatto incl. cap, annidamento rr=0, base su `max(0,·)` con reddito negativo,
  SFC/determinismo a rr>0, lag del sussidio, crowding-in direzionale), eterogeneità
  (brief 10: ventaglio e mean-preservation, annidamento spread=0, validazione del range,
  SFC/determinismo a spread>0, reporter, collasso direzionale, e il pin del fatto che a
  spread=0 le imprese divergono comunque per via della rete), proprietà d'impresa
  (brief 12: SFC parametrizzata su `pct_capitalists`, copertura della proprietà, assenza
  di doppio conteggio in `net_worth()`, biiezione al default = annidamento, determinismo
  fuori dal default, `ValueError` a 0 capitalisti, semantica multi-proprietà/nessuna
  proprietà), parametri strutturali e SA (brief 13: SFC/proprietà/determinismo su
  `num_firms × num_households`, pin direzionale del **bacino** via capitale per lavoratore,
  annidamento `u_min=None` bit-for-bit e validazione, reporter `Capitalist_Consumption`
  fuori da `_PANEL_METRICS`, e la **regressione sulla banda σ→1** che il bug di overflow
  avrebbe fatto fallire — continuità attraverso σ=1 e guardia inerte sulle σ sweepate).
  **512 test.** *(Brief 11 non aggiunge test: non tocca `src/`.)*
- `performance/engine.cpp` — **STALE**: implementa il modello additivo di Fase 1,
  non il core CES. Non usare per risultati finché non è portato.
- `parameter_notes.md` — note bibliografiche: fonte, stima, range e verdetto di
  ancoraggio per ogni parametro; §"Il sistema congiunto" (α, ρ, δ, K/Y, I/Y).
  **Da estendere a ogni nuova estensione.**
- `CLAUDE.md` — questo file. **Da rileggere contro il codice a ogni brief**: ha
  già driftato una volta (§9).