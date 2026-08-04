# METHODOLOGY.md — Istruzioni del progetto

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
Fino a poco fa esisteva **solo come specifica di design** (mai implementata) in
una vecchia versione di questo file. Ora è **costruita, calibrata e committata**: Cobb-Douglas
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

**Raffinamento (brief 17): ogni numero ha IL SUO artifact.** Non basta che un numero sia
*ricalcolabile* da UN artifact; prima di dichiararlo sbagliato bisogna stabilire da QUALE
artifact viene. Un numero **corretto di un'altra vintage** non è un refuso, e «correggerlo»
a pezzi **rompe la coerenza** del documento che lo contiene. **Regola operativa: un claim si
dichiara sbagliato solo dopo averne identificato il referente.** Due casi misurati, entrambi
**falsi allarmi del triage del brief 17** (una diagnosi «stale» su citazioni in realtà corrette
di `ces_b13`):
- **`0/843`**: veniva dal **binning di `ces_b13`**, non da `ces_b16`; la «correzione» poggiava
  anche su un'**aritmetica falsa** (821+843 = 1664, la tabella tornava a 3328). **Revertita** in
  `667003b`.
- **`ST≈1.00`**: **1.0018 è il valore corretto di `ces_b13`** (corda); l'edit a 0.916 **resta**,
  ma è un **cambio di vintage** verso la QoI riparata (`ces_b14` OLS, 0.9158), non la correzione
  di un errore.

**Raffinamento (brief 20): ogni tabella di numeri MISURATI stampata nel paper ha un generatore
committato.** Corollario dell'«ogni CSV committato ha un generatore» delle istruzioni: correggere a
mano una cella di una tabella misurata lascia in piedi la causa (la trascrizione). `tab:sobol` è la
prima a passare da un generatore (`scripts/make_tab_sobol.py`, brief 20); `tab:delta`, `tab:baseline`
e `tab:marginalturn` restano senza — debito dichiarato.

**Raffinamento (brief 22): `tab:prices` è la SECONDA tabella con generatore committato**
(`scripts/make_tab_prices.py`), e porta una **CLASSE DI DIFETTO NUOVA**, distinta dai tre refusi
di `tab:sobol`. `tab:wagecurve` stampava `σ*=0.725` **senza dichiarare che i crossing sono due**:
il numero è corretto per la sua vintage `ces_b07`, ma la trascrizione ha perso il **qualificatore**.
Non un errore di cifra — una **perdita di informazione** nella trascrizione — corretto dichiarando
`n_crossings` in caption **a cifre invariate** (referente `ces_b07_sigma_star.csv`, `target=Y`/`across_eta`,
`n_crossings=2` a η=0.10 **e** η=0.15; il brief 22 ne citava solo una, seguito **artifact > brief**).
**Debito generatori aggiornato:** `tab:wagecurve` resta **senza** generatore ma con **referente
identificato**, quindi retrofittabile a **basso costo** — a differenza di `tab:baseline`, la cui
sorgente non è fra gli artifact inclusi (punto cieco #2). `tab:delta`, `tab:baseline`,
`tab:marginalturn` restano senza.

**Falsi positivi noti dello sweep — DA NON CORREGGERE MAI** (sarebbe il movimento di `667003b`):
- **`0.771`** (§9, `tab:marginalturn`) è **1230/1596 = 0.770677**, che round-once dà 0.771: **il
  paper è corretto**. L'abbinamento di `sweep_rounding.py` a `ces_b07_sigma_star_by_rho/ci_hi`
  **resta una coincidenza** (numero derivato — punto cieco #1 del brief 19). **Aggiornamento brief
  27-quinquies: il numero non è più *solo asserito*.** È ora registrato e **verificato cella per
  cella** da `verify_paper.py` in `fraction` mode (`marginal_curvature_resolved`: media di
  `curvature_resolved` sui punti `viable` di `results/ces_b16_turning_points.csv` = 1230/1596). Lo
  `sweep_rounding.py` continua a segnalarlo come firma coincidente — è una proprietà **dello sweep**,
  non del claim — quindi il monito «DA NON CORREGGERE MAI» qui vale per l'**abbinamento dello sweep**
  e non è più l'unica copertura del numero. È un **cambio di categoria** (da falso positivo dichiarato
  a numero verificato da un detector), non di copertura.
- **`59.4`** ×2 (§6, `tab:baseline`) è **non attribuito**: la sorgente di `tab:baseline` non è fra i
  51 artifact inclusi (punto cieco #2), e l'abbinamento a `ces_sigma_rho_grid` è un'altra cella.

**Punto cieco #3 della toolchain (brief 22), accanto ai due del b19.** I primi due sono dello
`sweep_rounding.py` (numeri derivati; tabelle senza sorgente inclusa); il terzo è di
`verify_paper.py`/`coherence.py`: il matching a **substring non può verificare un intero piccolo**
quando la sua riga porta la **stessa cifra altrove**. Caso misurato: il claim `n_crossings=2` a
η=0.10 di `tab:prices` è **indiscriminabile** perché la sua riga porta `σ*=0.726` (la cifra «2» è
già nel numero); nessun `context` di riga lascia un solo «2». **Rimosso dal registro** perché
sarebbe un check vacuo (un check che passa senza ispezionare è peggio di nessun check, §6); il
claim falsificabile «off sviluppa un secondo crossing» **sopravvive** via η=0.15, la cui riga
(`0.711`, `[0.658, 0.800]`) non contiene «2». Gli `n_crossings=1` (interi non discriminanti) e i
conteggi di collasso c0=2.0 (interi piccoli/derivati) sono **dichiarati e riconciliati contro
l'artifact nel report del brief**, non auto-registrati.

**Punto cieco #4 della toolchain (brief 24): un numero MISURATO senza artifact CSV.** Il conteggio
dei test stampato nel paper (`app:repro`) è un claim **misurato** — viene da `pytest -q` — ma non ha
un CSV committato da cui leggerlo, quindi è **fuori dalla portata di tutti e tre i verificatori**:
`verify_paper.py`/`coherence.py` cercano il referente in un artifact (che non c'è), e
`sweep_rounding.py` guarda solo i token `\d+\.\d+` (un intero non lo è). Ha infatti **derivato in
silenzio**: il paper diceva 527, `pytest -q` ne conta **569** (allineato in `a_validation.tex`,
commit a sé). Regola operativa: **il conteggio dei test si allinea a mano da `pytest -q` prima di
ogni push**, perché nessun detector lo farà. Distinto dal punto cieco #2 (lì la sorgente CSV esiste
ma non è fra gli artifact inclusi; qui una sorgente CSV **non esiste per natura**).

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
  resta **sotto** σ\* per ogni λ_e — quindi **profit-led a ogni gain** — e σ=1 resta
  sopra, quindi il wage-led di σ=1 sopravvive a ogni gain: **è la posizione della
  frontiera a essere robusta al gain**, con entrambe le letture ai suoi due lati.
  Nessun finding di selezione del bacino.
  *(Formulazione corretta dal brief 14: diceva "il wage-led è robusto al gain" citando
  come prova che l'empirico resta sotto σ\*, che è invece il lato profit-led. La
  λ_e-invarianza misurata non cambia; cambia l'etichetta.)* **E2 (c0=2.0): ipotesi di stabilizzazione NON CONFERMATA** —
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
    **0/843 punti sopravvivono** *(⚠️ QoI-corda del brief 13; la QoI OLS riparata del
    brief 14 misura `ST(delta|viable)`=0.916 (`ces_b14` OLS; il ≈1.00 di qui è **1.0018**,
    `ces_b13` corda — entrambe corrette per il proprio referente) e il taglio δ∈[0.075,0.090] conta 832 punti
    — vedi la voce brief 14 e §9)*, e δ=0.05 siede appena dentro il bordo — il brief 11
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

- **Brief 14 — RIPARAZIONE DELLA QoI: le due cause del brief 13, separate per
  esperimento.** Il brief 13 si era chiuso con una contraddizione dichiarata e due cause
  candidate che non sapeva distinguere. Qui vengono separate **su una sola griglia di run**,
  sotto una **regola di verdetto congelata nel sorgente** (`VERDICT_RULE` in
  `scripts/run_brief14.py`) **prima** di qualunque esecuzione.
  - **Task A — il ponte (2×2: metodo × condizionamento).** Le celle 1 e 2 **non costano
    simulazione**: i panel committati b05/b07 portano già la griglia σ canonica × supporto ρ
    × 20 seed ai default del brief 07, quindi corda e pendenza OLS sono **due funzionali
    lineari degli stessi dati**. Controllo di ancoraggio **a 14 cifre**
    (σ\* = 0.6540142777288407 contro il canonico 0.654).
    | cella | parametri | metodo | σ\* | CI 95% | banda empirica |
    |---|---|---|---|---|---|
    | 1 | fissi | corda | **0.447** | [0.395, 0.501] | a cavallo |
    | 2 | fissi | OLS | **0.643** | [0.596, 0.701] | sotto |
    | 3 | marginalizzati | corda | 0.938 | [0.573, 0.976] | sotto |
    | 4 | marginalizzati | OLS | **0.962** | [0.723, 0.985] | sotto |
    **VERDETTO: causa (a)** — a parametri identici il solo cambio di stimatore muove σ\* con
    **CI non sovrapposte**. Riportato accanto al verdetto, perché la regola meccanica lo
    sotto-descrive: **marginalizzare muove σ\* PIÙ di quanto faccia lo stimatore**
    (0.643→0.962, anch'esse non sovrapposte), solo che lo muove **lontano** dalla banda
    invece che **attraverso**. Entrambi gli spostamenti spingono nello stesso verso: la banda
    empirica è profit-led **più robustamente** di quanto il brief 07 da solo affermasse.
  - **REPERTO — la premessa della contraddizione non regge.** Il README §2 enunciava la
    convenzione correttamente (sotto σ\* è profit-led) e il wide check del brief 13 trovava
    il wage-led raro sotto 0.65 e comune sopra: **è la STESSA direzione, non l'opposta**. La
    stesura aveva **mal letto i documenti di questo repo**. Corretto nel README con la
    misura a supporto.
    > **⚠️ Errata sul messaggio di commit `67d4a80`, verificata contro gli artifact
    > (2026-07-21).** Quel messaggio afferma che «`P(wage-led)` supera 0.5 sopra σ≈0.82, non
    > a 0.65». **È falso, e contraddice sia il commit successivo `4728117` sia il paper**,
    > che dicono entrambi che non supera 0.5 da nessuna parte. Misurato su
    > `ces_b14_wide_design.csv` e `ces_b13_wide_design.csv`, a 4 e a 8 bin, su entrambi gli
    > stimatori: il massimo è **0.434** (b13, 8 bin) e **0.404** (b14 corda, 8 bin) —
    > `P(wage-led|viable)` **non attraversa mai 0.5** in nessun sotto-intervallo di σ. La
    > formulazione corretta è quella del paper: *non c'è soglia a 0.65 né altrove*.
    > L'affermazione **non è mai entrata** in README, paper o notebook (verificato per grep):
    > vive solo nel messaggio di commit, che è storia e non si riscrive. È il **terzo**
    > episodio della stessa famiglia — una claim in prosa smentita dalle tabelle del progetto
    > stesso — e per questo è registrata, non cancellata.
    Secondo errore di formulazione corretto in §4: σ\* che sale con η
    **non "rafforza"** il wage-led per la banda empirica, la spinge **più a fondo nel
    profit-led** (vedi la nota già inserita nella voce del brief 08).
  - **Task B — tre quantità al posto di "la pendenza":** pendenza OLS, **la svolta ρ\***, e
    **da che lato della svolta cade il ρ ancorato**. ρ\* **cresce monotonicamente in σ** ed è
    risolto dentro il supporto in **10 celle su 11** — che è esattamente ciò che produceva il
    disaccordo corda/OLS. Al ρ ancorato l'economia sta **a SINISTRA della svolta per ogni
    σ ≥ 0.5**.
  - **Task C — la SA rifatta sulla QoI riparata.** Morris e Sobol ri-eseguiti con la pendenza
    OLS su **quattro** ρ al posto della corda a due punti; parametri, range, valori congelati
    e seed di campionamento **importati** da `run_brief13.py` anziché ricopiati, così la QoI è
    **dimostrabilmente l'unica cosa che cambia**, ed entrambi gli stimatori sono calcolati
    **sulle stesse run**. **Lo screening cambia** (stessa keep rule, stesso seed):
    `target_utilization` **entra** nel set dei sopravvissuti, `benefit_replacement_rate`
    **esce** — il che chiude retroattivamente anche la questione del riuso: *un set di
    sopravvissuti diverso è una design matrix diversa*, quindi le run del brief 13 non erano
    riusabili nemmeno in linea di principio.
    | analisi | frazione viable | P(wl\|viable) corda | P(wl\|viable) OLS |
    |---|---|---|---|
    | brief 13 (sola corda) | 0.483 | 0.095 | — |
    | primaria, σ 0.40–0.60 | 0.480 | 0.094 | **0.026** |
    | wide, σ 0.30–1.00 | 0.468 | 0.202 | **0.098** |
    La colonna corda **riproduce** il brief 13 (0.094 vs 0.095; 0.202 vs 0.201), col residuo
    imputabile al set di sopravvissuti e non allo stimatore. **Il conto chiude esatto:** corda
    e OLS discordano di segno su **112 punti viable su 1596**, **110** «corda negativa, OLS
    positiva» e **2** l'inverso ⇒ netto **108**, e `(0.0940 − 0.0263) × 1596 = 108`. **Il
    discriminante è quello predetto:** dove discordano la svolta media è **ρ\* = 0.473**,
    *dentro* la finestra [0.35, 0.55] della corda; dove concordano è **0.820**, fuori dal
    supporto, dove `Y(ρ)` è monotòna e ogni stimatore vede la stessa cosa.
    **Ma la decomposizione non si muove:** δ `ST` 0.900 vs 0.966, π0 0.561 vs 0.562, σ 0.021
    vs 0.024; sulla viability δ 0.916 vs 1.002. **QUALI** parametri generano la varianza è
    robusto allo stimatore, il **LIVELLO** della probabilità wage-led no: la risposta del
    brief 13 alla prima domanda **resta in piedi**.
    **Wide check ripetuto** (il test diretto), `P(wage-led|viable)` per bin di σ:
    0.000 / 0.025 / 0.154 / 0.211 sotto OLS, 0.016 / 0.127 / 0.299 / 0.363 sotto corda — il
    wage-led diventa **più** comune al crescere di σ **sotto entrambi**, stessa direzione
    della sign frontier, e **non supera mai 0.5** in tutto il range. **La contraddizione è
    chiusa perché non è mai esistita.**
    **Limite dichiarato sul task B nello spazio marginalizzato:** ρ\* è risolto dentro il
    supporto solo nel **37.7%** dei punti viable (mediana 0.323; sotto il supporto nel
    **58.7%**), contro 10 su 11 nelle celle canoniche a parametri fissi. Dove cade fuori, **la
    U non è risolta lì** e viene riportata come tale, **non estrapolata**.
  - **Task D — criterio dei byte-check RITIRATO, con la misura a supporto.** Vedi §9, dove il
    criterio nuovo è già registrato come applicato: due limbi che non si compensano (≤8 ULP
    con pavimento assoluto sui **livelli**, regime a tolleranza **zero**) e i due limiti
    misurati (ULP puro inutilizzabile vicino allo zero — `Tax_Rate` a rr=0: **3460 ULP** su
    un gap di 1.7e-16; e **non applicabile a quantità differenziate o fittate** —
    `slope_raw`: **3410 ULP** da input a 4 ULP, controllate dal **segno**). Baseline
    ri-fissata a **7/7 PASS**; driver b07–b10 e b12 aggiornati, e **tutti continuano a
    registrare il `byte_equal` ritirato** perché il cambiamento resti visibile.
  - **Task E — `delta` elevato da sensitivity a LIMITE STRUTTURALE.** Registrato in §9: al δ
    implicato dai dati il modello **non esiste** (0 punti viable su **832** in
    δ∈[0.075,0.090], `ST(delta|viable)`=**0.916** (`ces_b14` OLS) — la QoI-corda del brief 13 leggeva
    **1.0018**/843 (`ces_b13`; due vintage, entrambe corrette per il proprio referente);
    `ces_b14_sobol_indices.csv`, `ces_b16_turning_points.csv`); è la firma di
    `g = 0` letta attraverso `I/K = δ + g`.
  - **527 test verdi** (512 + 15 nuovi, che pinnano **la ragione** di ogni costante dichiarata,
    non il suo valore). Driver `scripts/run_brief14.py` (fasi `bridge`/`morris`/`sobol`/
    `wide`/`report`, `SAMPLE_SEED` fissato, ambiente in `ces_b14_environment.json`, verdetto
    meccanico serializzato in `ces_b14_verdict.json`); **18 CSV** `results/ces_b14_*.csv` +
    **2 JSON** (`environment`, `verdict`). **Nessuna figura nuova** — l'unico brief che non
    ne produce, perché ripara una quantità invece di misurarne una nuova. **Fuori scope:** ricalibrare alcunché sulla base della
    riparazione; i limiti di campionamento del brief 13 (3 seed, N=256 su 11 parametri)
    restano **invariati e non migliorati** — le S1 piccole restano indistinguibili da zero; e
    il σ\* marginalizzato del ponte (0.96) e lo sweep Sobol wide **sweepano set di parametri
    diversi** (quindici contro undici, cinque fissati ai midpoint): concordano nel messaggio
    (la frontiera marginalizzata sta a σ ≳ 1) ma **non sono la stessa stima** e non vengono
    presentati come tale.

- **Brief 15 — ristrutturazione del paper: dall'ordine cronologico a quello
  argomentativo** (solo `paper/`; **nessun numero nuovo o modificato**, nessuna modifica a
  `src/`/`scripts/`/`results/`/`tests/`). La U di `Y(ρ)` è enunciata **una volta sola e
  presto** (nuova §6): ρ\*, la sua crescita in σ, il lato su cui cade il ρ ancorato, e
  **poi** σ\* come riduzione dichiarata sotto stimatore — il che rende superfluo il
  `declbox` difensivo della vecchia §7, rimosso. §10 e §11 **fuse** in una sola §9 con
  headline sulla QoI riparata (`P(wage-led|viable) = 0.026`) e il conto dei 108 punti che
  chiude esatto; **2×2, regola di verdetto ex-ante e controllo di ancoraggio a 14 cifre
  spostati in appendice**. La conditionality fiscale **promossa** a §8 autonoma (che il
  sussidio *elimini* la regione wage-led è un risultato sulle istituzioni, non un
  controllo di robustezza). Nuova **appendice A "Validation and reproducibility"**: §9
  vecchia (invariante valido al solo default), criterio byte-check coi due limiti
  dichiarati, 2×2 completo, **trail delle retrattazioni**, riproducibilità — aperta dal
  principio, non dal mea culpa. §4 espansa 128→575 parole (tassonomia dei tre livelli di
  ancoraggio, I/Y su BEA, δ a convenzione con banda, `I/K = δ + g`); le **tre serie FRED
  ora citate** in `references.bib` (34→37 voci) invece che asserite. Abstract 550→**249
  parole**. **Verifica: zero discrepanze** sui numeri contro gli artifact, **18/18**
  headline allineati notebook/README/paper, zero `\cref` pendenti, linter e definizioni
  puliti. **Deviazione dichiarata e CHIUSA:** l'appendice sta a **1.340 parole contro il
  target ~700 del brief (+91%)**, fuori dalla banda ±20%. Il target era **sotto-stimato dal
  brief stesso**: i cinque elementi che elenca pesavano già ~1.370 parole nei file
  d'origine, e scendere a 840 richiederebbe tagliarne uno. Accettato dal PI; la banda vale
  per le altre voci, tutte rientrate (§8 a +21% accettata come irrilevante).
  **Due detector riparati** (fuori repo, in tooling di sessione): il linter LaTeX
  segnalava 79 falsi positivi mascherando i veri, e il cross-check dei 18 numeri leggeva
  una **lista di file scritta a mano**, diventata falsa al primo rinomino — avrebbe
  riportato un accordo mai testato. Entrambi ora falliscono su un caso sintetico con
  difetti noti **prima** di essere creduti. È la stessa lezione di §9: *un check che
  riporta successo senza ispezionare nulla è peggio di nessun check.*
  > **⚠️ Superato dal brief 18.** Il «zero discrepanze, 18/18 headline allineati» qui sopra
  > **non è più citato**: girava su **tooling di sessione non committato** (una lista di file
  > scritta a mano). Il verificatore committato del brief 18 (`verify_paper.py` +
  > `paper_claims.yaml`), al **primo giro**, ha trovato **tre discrepanze vere** in `tab:sobol`
  > (colonna Slope) — chiuse dal brief 20. È la misura di cosa valeva quel «18/18».

- **Brief 17 — aspettativa sull'investimento (punto 10-bis): l'acceleratore su `u^e`.** L'acceleratore
  d'investimento passa dal segnale realizzato `utilization_last_period` a un'**aspettativa di utilizzo**
  `u^e`, aggiornata con lo schema a parziale aggiustamento del brief 08, gain `λ_u` (codice:
  `utilization_expectation_gain`, default 1.0). `λ_u=1` annida il pre-brief-17 **bit-for-bit** (branch
  esplicito di `adaptive_expectation`; verificato via **git-stash** su 6 celle headline+collasso: dev=0.0,
  e byte-check slice **detector-first** — un λ_u fittizio FALLISCE prima di credere al PASS — **regime-esatto
  sui 4 panel**; il residuo numerico oltre 8 ULP su b05/b07/b09 è **drift d'ambiente pre-esistente**
  (max abs 7,6e-11 su `Total_Capital`, celle di collasso c0=2.0), non del brief 17, e b10 è PASS pulito).
  Due reporter `Expected_Utilization`/`Util_Effect` **fuori da `_PANEL_METRICS`** (come
  `Capitalist_Consumption`). **Perché priorità 1:** `ces_b14_sobol_indices.csv` mette `S1(β)=0.64` della
  varianza del segno di dY/dρ su β, senza referente empirico e agganciato a questo segnale arbitrario —
  vulnerabilità **misurata** dell'headline. **La premessa NON dipende dalla riparazione della QoI:** β è
  **primo per S1 su `slope|viable` in ENTRAMBE le vintage** — **0.370** (corda, `ces_b13`) e **0.641** (OLS,
  `ces_b14`) — quindi «il parametro che porta il segno non è ancorato» regge su entrambi gli stimatori, e cade
  l'obiezione «avete scelto la QoI che vi conviene». **Ipotesi pre-registrata (§4, scritta nel driver PRIMA dei
  run):** lo smoothing riduce la varianza di `util_effect`, `λ_u<1` come β efficace più basso ⇒ ρ\* scende
  (0.37–0.40), la quota «a sinistra» cala, i wage-led si diradano. **Esito Fase A (scenario headline
  c0=1.0/σ=0.5/η=0.10/rr=0; 6 β × 5 λ_u × 4 nodi ρ × 20 seed): IPOTESI FALSIFICATA.** (a) **Meccanismo
  falsificato alla radice:** la **sd temporale** di `util_effect` **non cala** con λ_u — è piatta su
  [0.25,1.0] (β=1.0: 0.026/0.022/0.025/0.024), = 0 solo a λ_u=0 (congelato); `u` è **persistente** in
  steady state, e lisciare un segnale autocorrelato non ne riduce la varianza. (b) **ρ\*, slope OLS,
  wage-led λ_u-invarianti** entro le bande inter-seed su [0.25,1.0] (spread di ρ\* ≤ semi-ampiezza CI;
  escluso β=0.05 che siede sull'ancora, max **0.72 bande**); ρ\* **sale con β** (0.36→0.53), wage-led solo
  **4/30** celle a β=1.0. **Conclusione a due tempi:** *(a — segnale)* H1 è **robusto alla specifica del
  SEGNALE** (λ_u): ρ\*/slope/wage-led invarianti su [0.25,1.0], meccanismo falsificato — rafforzamento reale.
  *(b — forza)* H1 è **load-bearing sulla FORZA** (β): il margine all'ancora (ρ ancorato **fuori** dalla CI
  bootstrap di ρ\*, `ces_b17_margin.csv`) è **risolto solo per β≥0.5**, e il default 0.5 sta sul bordo;
  spegnere l'acceleratore in **due modi indipendenti** (λ_u=0 *o* β=0.05) dà lo stesso esito — il margine
  **SVANISCE** (l'ancora entra nella CI), **non si inverte**. Quindi **λ_u=0 non è un controllo degenere:
  è metà del risultato**. β **resta senza referente** (meno load-bearing sul segnale, non ancorato nel livello).
  **Due limiti di scope dichiarati:** (i) il 64% (S1 su `slope|viable`) è **marginalizzato** su 11 parametri,
  la Fase A è **condizionale** su un punto (σ=0.5/η=0.10/c0=1.0/rr=0) — **NON** «H1 sopravvive al canale che
  porta il 64%» (sarebbe la confusione condizionale/marginale dei brief 13-14); la **Fase B non è stata
  eseguita**. (ii) la Fase A **non ha testato il regime di collasso c0=2.0**, dove il brief 08 trovò l'unico
  effetto interessante di λ_e — **lacuna di disegno del brief** (§5 fissa lo scenario headline), future work,
  non eseguita. **Gate (§5):** la regola congelata (`ces_b17_gate.json`) è OPEN, ma la decomposizione post-hoc
  mostra i 6 trigger come **4 degeneri (λ_u=0) + 2 rumore near-anchor (β=0.05) + 0 gradiente di lisciamento**;
  **chiuso sulla sostanza** (§5: se inerte entro le bande, chiudi; non eseguire la Fase B per completezza). **551 test verdi** (527 invariati + 24 nuovi di §7). Driver
  `scripts/run_brief17.py` (fasi `byte-check`/`phaseA`/`report`, ipotesi §4 e soglia del gate **congelate
  nel sorgente prima dei run**, thread BLAS pinnati, ambiente in `ces_b17_environment.json`); CSV
  `results/ces_b17_*.csv` + `ces_b17_gate.json` + figura `ces_b17_rho_star_lambda.png`. Variante B (`u^e`
  da `expected_demand`) registrata come scartata in `parameter_notes.md` perché non annida. **Fuori scope:**
  smoothing di `profit_last_period` (registrato come punto **10-ter**, non fatto); regole di apprendimento
  più ricche (RLS, switching); **Fase B** (design b14 marginalizzato) **non eseguita — gate chiuso**.
  **Debito notebook:** il consolidamento del notebook arriva a b14; il brief 17 ne **apre uno nuovo** (le
  sezioni λ_u / margine — `ces_b17_*` — non sono nel notebook). **Debito byte-check:** il pin a 8 ULP è
  troppo stretto per l'ambiente attuale — registrato in §9, non risolto qui.
  **Task 0 (correzioni documentali, `7e404f8`) — riclassificazione (brief 17, post-revisione).** Dei sei
  item «corretti», **quattro erano davvero stale** (conteggio test → 527; #1 «svolta ≥0.420»; #2 «16 vs 17
  parametri»; #6 mediana ρ\* 0.414 vs 0.323) e **due erano citazioni CORRETTE di `ces_b13`** (chord vintage)
  **mal diagnosticate come stale** dal triage: **`ST≈1.00`** (= **1.0018** su `ces_b13`; l'edit a **0.916**
  sopravvive come **cambio di vintage** verso la QoI riparata `ces_b14`, non come refuso) e **`0/843`**
  (binning `ces_b13`; **revertito** in `667003b` perché toccava il blocco chord-vintage coerente del paper
  §9 — tabella + figura `ces_b13` + prosa — e poggiava su aritmetica falsa). L'oggetto del commit `7e404f8`
  («six stale SA figures») è quindi impreciso su due dei sei; **non riscritto** (storia). Vedi il
  raffinamento §5 «ogni numero ha il suo artifact».

- **Brief 18 — etichettatura di vintage del paper + verificatore dei numeri committato**
  (solo `paper/` e `scripts/`; nessun `src/`, nessun run del modello). Due mosse.
  **(a) Vintage esplicita in §9:** `tab:sobol` e `tab:delta` dichiarano `ces_b13` (corda);
  `fig:sa` dichiara **Morris su 17 = 16 parametri difendibili + `max_tax`** (screenato solo lì)
  e **Sobol sui 16**; nuova **`fig:sa-b14` a tre pannelli** generata da
  `run_brief14.py --phase figures`, col terzo pannello `slope|viable` a **RBD-FAST, solo S1**
  (nessun ST — lo stimatore ne definisce solo il primo ordine). **Zero cifre cambiate** nel paper.
  **(b) Toolchain committata (non più tooling di sessione):** `scripts/paper_claims.yaml`
  (registro dei numeri headline, ognuno con lookup eseguibile — artifact, filtro, colonna,
  `decimals`, mappa simbolo→parametro), `scripts/verify_paper.py` (paper↔artifact,
  `round(cella, decimals) == valore`, round-once) e `scripts/coherence.py` (documento↔documento).
  **CHIUDE il debito «verificatori inesistenti»:** in brief 15 il cross-check dei 18 numeri
  girava su una **lista di file scritta a mano**, non committata. **CHIUDE il debito «paper §9
  chord-vintage»:** il blocco `ces_b13` non è più implicito, è etichettato. **Conseguenza tenuta
  onesta:** il «zero discrepanze, 18/18 allineati» del brief 15 **non è più citato**; è sostituito
  da un verificatore che gira, e che **al primo giro ha trovato tre discrepanze vere** in
  `tab:sobol` (colonna Slope, doppio arrotondamento) — chiuse dal brief 20.

- **Brief 19 — `scripts/sweep_rounding.py`: firma del doppio arrotondamento su TUTTO il paper,
  registry-free. RISULTATO NEGATIVO, registrato come tale** (solo `scripts/`; nessun `src/`,
  nessun run). Per ogni token numerico del paper cerca celle candidate negli artifact inclusi e
  classifica OK / DOUBLE-ROUND / NO-CANDIDATE. **Nessuna discrepanza nuova** oltre le tre già note:
  i quattro candidati «non ambigui» rimanenti sono **falsi positivi verificati a mano**. **Due
  punti ciechi STRUTTURALI, registrati perché nessuno li riscopra inseguendo un detector più furbo:**
  1. **I numeri DERIVATI non sono verificabili cella per cella** — conteggi, mediane, rapporti
     calcolati al volo (`0.771` = 1230/1596, `538`, `0.414`, `477`) non esistono come cella in
     nessun CSV; lo sweep li abbina solo a qualcosa di **casuale**.
  2. **Le tabelle la cui sorgente non è fra i 51 artifact inclusi non sono coperte affatto** —
     `tab:baseline` in primis (nessuno dei suoi numeri ha un referente identificato). «Zero firme
     in una sezione» **non** è «la sezione è pulita».
  **Corollario operativo: la prossimità numerica NON è attribuzione;** la copertura si estende
  **col registro**, non affinando lo sweep. **Esclusione dichiarata dei dump a >100 righe**
  (frattura misurata: il più grande aggregato incluso è a **88 righe** — `ces_b07_slopes.csv` —, il
  più piccolo dump per-cella escluso a **154** — `ces_b05_stage_a_cells.csv`; niente in mezzo), e
  ogni file escluso è elencato nel report col conteggio. `RESULTS.md` **untracked per scelta** →
  `coherence.py` emette `DOCUMENT UNTRACKED` (debito dichiarato), non passa in silenzio. **Il check è
  sullo stato di tracciamento git (`git ls-files --error-unmatch`), NON sull'esistenza del file
  (riparato dal b27, `--selftest` che FIRE): spara identico su clone fresco (assente) e sulla macchina
  dell'autore (presente ma untracked); l'ex check per esistenza taceva sulla seconda — la modalità di
  guasto del pin 8 ULP (un detector che smette di essere letto).**

- **Brief 20 — `tab:sobol` corretta IN BLOCCO, da un generatore committato** (solo `paper/`,
  `scripts/`, `results/`, `README.md`, `parameter_notes.md`; nessun `src/`, nessun run). Le tre
  discrepanze del brief 18/19 erano errori di **trascrizione a mano** (CSV → LaTeX con doppio
  arrotondamento), **non di calcolo**. Corrette dal referente `ces_b13_sobol_indices.csv`
  (`estimator=saltelli`, round-once **ROUND_HALF_UP** a 3 decimali), colonna Slope:
  **`c0` S1 -0.030 → -0.029**, **`c0` S_T 0.277 → 0.276**, **λ (=`wealth_effect`) S1 0.040 → 0.039**.
  Nessun'altra cifra cambia (generatore vs tabella, cella per cella). Chiusa da
  **`scripts/make_tab_sobol.py`** — **prima tabella del paper con un generatore committato**
  (estensione della regola §5, vedi lì). Propagata alle **repliche a mano** della stessa tabella
  `ces_b13`: `README.md`, `parameter_notes.md`, `RESULTS.md`, **nello stesso commit** (working tree
  per `RESULTS.md`, untracked). **Notebook NON toccato:** calcola la colonna `ces_b13` **live** dal
  CSV (già `0.276`, round-once) e non conteneva **nessuna** delle tre celle — «correggerlo» sarebbe
  stato il movimento di `667003b`. I tre claim `..._OPEN` diventano claim normali e passano;
  `verify_paper.py` a **0 FAIL**, `coherence.py` a **0 DIVERGENT**. Resta **`sobol_sigma_ST_viable`
  AMBIGUOUS per costruzione** (S1 e ST viability leggono entrambi `0.008` sulla stessa riga di
  `tab:sobol`): ambiguità dichiarata, non residuo. **Copertura del registro: 26 claim contro i 574
  token del paper** (582 prima del fix della regex dello sweep — brief 20 Task 0: un `-` dopo un `-`
  è un trattino di range `--`, non un segno; 8 falsi negativi di range rimossi, il vero `-0.030` di
  riga 97 conservato). **Build CI verde** (run `30468591546`: 35 pagine, 0 error, 0 overfull/underfull,
  0 reference/citation undefined).

- **Brief 21 — PROBE sui prezzi (punto 9-bis): H2 è un artefatto del numerario?** Un dial
  `enable_prices` (default **False**, fuori dai default e fuori dalla SA), **zero nuovi
  parametri liberi**, byte-identico a `main` da spento. Normal-cost pricing con markup e
  produttività costanti dà `P_t = (1+mu)·w_t/A`; normalizzando `P=1` al salario di
  riferimento (`A=(1+mu)·w_bar`) collassa a **`P_t = w_t/w_bar`** e **`mu` sparisce** — `P` è
  il salario normalizzato. A numerario 1, `w_t` È il salario reale, e H2 (b07: «la
  flessibilità salariale non autocorregge la disoccupazione», meccanismo = oscillazione
  salario-occupazione che erode capitale a c0=2.0) potrebbe misurare **il numerario, non il
  mercato del lavoro**: con markup costante, un taglio del salario *nominale* abbassa anche il
  prezzo e il salario *reale* `w/P=w_bar` non si muove.
  - **Ordine di lavoro (b12): libro mastro di §1.3 come docstring + test SFC PRIMA
    dell'aritmetica.** Il libro mastro nominale/reale separa moneta e beni: domanda desiderata
    delle famiglie **reale** (`d=min(max(c0+c1·(income/P)+λ·(wealth/P),0),(wealth+income)/P)`,
    `c0` reale non deflazionato), pagamento consumo e ricavo d'impresa **nominali** (`P·unità`),
    investimento **reale in quantità/nominale in denaro** (le imprese comprano `budget/P` unità,
    pagano `P` per unità). `enable_prices=False` è un **branch esplicito** al percorso attuale in
    ogni sito, mai `·1.0`. **Test contro input noto come cattivo (§3):** iniettata l'asimmetria di
    §1.3 (famiglie pagano `P·d`, imprese incassano `d`) → l'invariante SFC **FALLISCE NETTO**
    (400.0 → 8.66 in 10 step, **391.3 distrutti = 3.9e9× la tolleranza**, monotòno); il detector
    non è vacuo.
  - **⚠️ La rottura silenziosa di §1.3, materializzata (reperto metodologico).** La prima
    implementazione (5 siti monetari, §1.3 tabella) faceva **migliorare** l'allocazione reale con
    η a prezzi ON (c0=1.0/σ=0.5: U 0.541→0.497, L 45.9→50.3): η muoveva l'allocazione per **DUE**
    canali reali, non uno. Diagnosi: l'impresa massimizza il profitto **nominale** `P·Q−w_t·L`,
    quindi la FOC di profit-max è `P·MPL=w_t` cioè `MPL=w_t/P=` salario **reale** `=w_bar`
    (costante). `plan_employment` usava ancora `w_t` → secondo canale reale spurio, che viola §1.1
    («**un solo canale reale**: Pigou»). **Né l'SFC né il byte-check a η=0 lo catturano** (verdi in
    entrambi i casi): lo cattura solo l'economia (§1.1) e l'indizio di sequenza di §1.4 (`P`
    calcolato **prima del mercato del lavoro** — è lì perché il mercato del lavoro usa `P`; Chekhov:
    calcolato ma non usato nella FOC). Corretto (`agents.plan_employment` e
    `compute_wage_share_profitmax` al salario reale `w_t/P`); P1 resta byte-identico. **È
    esattamente il tipo di difetto che P1/SFC non vedono e che il brief avvisava di cercare.**
  - **P1 — annidamento: CONFERMATO byte-identico.** `enable_prices=True, η=0` (dove `w=w_bar`
    quindi `P=1` esatto) vs `main` (`ces_b05`): `n_exceed=0/3080`, `regime_equal=True`,
    **`max_abs_dev=5.68e-14`** (solo rumore di round-trip CSV, sotto `atol`). Detector-first: il
    self-test (`η=0.10`, P≠1, vs main) **FIRES** (2228/3080, dev 184). Regime-first col dev accanto
    (il `byte_equal` ritirato è False solo per il drift d'ambiente dichiarato, §9/b17).
  - **P2 — σ\*(η) η-invariante: FALSIFICATO, e nel verso opposto.** Atteso piatto (salario reale
    indipendente da η ⇒ solo Pigou, ipotizzato trascurabile). Misurato: a prezzi ON σ\*(η) **sale
    PIÙ ripido** (0.648→0.716→0.806→**0.871**, CI η=0 vs η=0.15 **non sovrapposte**) del controllo
    OFF (0.648→0.680→0.726→0.711, CI sovrapposte a 12 seed). Il canale Pigou **non** è trascurabile:
    alza l'output a η alto e spinge la banda empirica (0.40–0.60, **sotto** σ\*) **più a fondo nel
    profit-led** al crescere di η. La predizione specifica (piattezza) cade; la *direzione* è quella
    stabilizzante.
  - **P3 — collasso a c0=2.0 si restringe/sparisce: CONFERMATO (la scommessa vera paga).** Celle
    con qualche collasso (pooled su η) **36 → 10** (piene 17 → 4); e — il punto — la **crescita in η
    del collasso è ELIMINATA**: ON `2,3,3,2` (piatto sul baseline η=0) vs OFF `2,8,12,14`. Il residuo
    ≈ baseline di η=0 (presente anche senza flessibilità salariale). Con il salario reale costante
    l'occupazione dell'impresa non oscilla col salario nominale, quindi **il capitale non si erode**:
    il meccanismo di b07 è in larga parte un artefatto del numerario.
  - **P4 — H1 non si muove: CONFERMATO dove conta.** Contro dei σ wage-led (dY/dρ<0) **4/11 in
    entrambi**; per σ≥0.4 (banda empirica e oltre) il ρ ancorato (0.3632) resta **a sinistra della
    svolta ρ\* in entrambi**, e dY/dρ a σ∈[0.4,0.6] è invariato di segno e ~magnitudo. Differiscono
    solo σ∈{0.05,0.30} (sotto la banda) e σ=1.5 OFF (un outlier +62.6 tra vicini negativi).
  - **Canale Pigou isolato (§1.1, ora l'unico canale reale).** c0=1.0, prezzi ON: η↑ ⇒ P↓
    (1.000→0.912) ⇒ ricchezza reale↑ ⇒ domanda↑ ⇒ **U 0.528→0.487 e Y 90.9→99.2**; OFF fa l'opposto
    (U 0.528→0.580, Y 90.9→81.8). Stabilizzante, e singolo (occupazione η-invariante per la FOC
    corretta).
  - **H2, forma a due tempi (b17): il MECCANISMO è UCCISO e la CONCLUSIONE è ROVESCIATA — due
    oggetti separati.** *Meccanismo* (oscillazione che erode capitale): killed dal probe (P3, collasso
    36→10 e non più crescente in η). *Conclusione* (nessuna autocorrezione): rovesciata — col probe
    più flessibilità salariale **ABBASSA** la disoccupazione (U 0.528→0.487) e alza l'output, via un
    canale **diverso** (bilanci reali/Pigou, non il loop salario-occupazione). **È la prima ipotesi di
    stabilizzazione CONFERMATA dopo quattro falsificazioni consecutive** (λ_e b08, rr b09-E3, rr
    b10-E2, governo esteso), e la prima da un canale diverso. **Limiti dichiarati:** è un probe
    (`enable_prices` resta default False, non entra nella SA); la variante a costo unitario endogeno
    (§1.2, che pinna la quota salari) **non è eseguita**; il pricing è normal-cost a markup costante
    (l'esito è specifico a quello); la magnitudo del Pigou non è calibrata; budget **12 seed** (il
    rialzo di σ\* del controllo OFF non è CI-risolto a 12 seed, quello ON sì). **Il probe non
    sostituisce nessun numero canonico di `main`.**
  - **569 test verdi** (551 invariati + 18 nuovi: SFC parametrizzata `enable_prices × η × c0`,
    input-cattivo che fallisce netto, annidamento byte η=0, Price fuori da `_PANEL_METRICS`,
    `P=w_t/w_bar`, salario reale costante, FOC dell'impresa al salario reale). Driver
    `scripts/run_brief21.py` (fasi `byte-check`/`panel`/`report`, ipotesi P1–P4 e **gate congelati nel
    sorgente PRIMA dei run**, BLAS pinnati, ambiente in `ces_b21_environment.json`); CSV
    `results/ces_b21_*.csv` (panel, byte_check, sigma_star_eta, collapse_c0_2, h1_rho_star, pigou_c0_1)
    + 2 figure. **Fuori scope:** la variante §1.2; markup variabile/prezzi eterogenei/stickiness/moneta
    come stock separato; promuovere il probe a feature; rifare i numeri canonici.

- **Brief 22 — qualificazione di H2 nel paper, IN BLOCCO (solo `paper/`+`scripts/`):**
  H2 riformulata da headline incondizionato a **BRACKET fra due convenzioni sul
  pass-through, nessuna delle due ancorata**. Commit `3f1f6a2` (prosa in blocco),
  `d4fdbf4` (generatore + `tab:prices` + registro), `d95cfed` (nuova sottosezione
  §10). Nessun `src/`, nessun run del modello, **569 test invariati per costruzione**.
  - **I SEI siti di H2 toccati insieme** (individuati con **grep reale**, non a
    memoria — lezione b18): `frontmatter.tex`, `01_introduction.tex`, `07_stress.tex`
    (`sec:wagecurve`), `10_discussion.tex` §9, la **nuova** sottosezione
    `sec:frontierlocal`, `11_limitations.tex`. Toccarne uno e non gli altri sarebbe
    il movimento di `667003b`.
  - **Enunciato a bracket — DIVIETO REGISTRATO.** A pass-through **zero** (numerario
    ≡ 1, il modello canonico) la flessibilità salariale non autocorregge e il capitale
    si erode; a pass-through **completo e istantaneo** (probe b21) autocorregge via
    Pigou. **Mai «H2 cade», «H2 tiene», «H2 è rovesciata»**: sono tutti e tre un capo
    del bracket spacciato per il bracket. Il probe occupa l'estremo **massimamente
    stabilizzante** (markup e produttività costanti, zero vischiosità), quindi è un
    **upper bound** sul pass-through, non un verdetto. (Nota: la voce b21 sopra usa
    «rovesciata» come shorthand di processo per l'estremo ON — **nel paper vive solo
    il bracket**.)
  - **`tab:prices` da `scripts/make_tab_prices.py` committato — SECONDA tabella del
    paper con generatore**, dopo `tab:sobol` (§5). σ\*(η) a c0=1.0, off (numerario
    fisso) vs on (`P=w_t/w̄`): on 0.648→0.716→0.806→0.871, off 0.648→0.680→0.726→0.711
    (**non monotona**, endpoint sotto η=0.10). Caption con **vintage `ces_b21`
    dichiarata** (12 seed, 11 nodi σ), colonna `#cross`, e la dichiarazione esplicita
    che **la colonna off è il controllo del probe, NON `tab:wagecurve`** (vintage non
    commensurabili — divieto §5/b17).
  - **`tab:wagecurve`: corpo BYTE-INVARIATO** (i suoi 0.654/0.666/0.725/0.740 sono
    corretti per `ces_b07`). La caption ora dichiara **`n_crossings=2` a η=0.10 E
    η=0.15** (referente `ces_b07_sigma_star.csv`, `target=Y`, `support_kind=across_eta`).
    **Classe di difetto NUOVA** (vedi §5): non un refuso di trascrizione come le tre di
    `tab:sobol`, ma una **perdita di informazione** nella trascrizione — il numero è
    corretto, cade il **qualificatore**. Il brief diceva «a η=0.10» e l'artifact ne
    aveva **due**: seguito **artifact > brief**, che è la gerarchia giusta.
  - **Nuova sottosezione `sec:frontierlocal`** («la sign frontier non generalizza»):
    tre canali indipendenti su tre disegni diversi convergono — §8 (b09, condizionale
    alle istituzioni fiscali), §9 (b13/b14, `S1(slope|viable)=0.019` su σ), §7+probe
    (b21, condizionale al numerario, σ\* su di ~un nodo). **Gerarchia — la conclusione
    da citare:** ciò che sopravvive a tutti e tre **non è la posizione della frontiera**
    ma il **margine ancorato di H1** (il ρ ancorato resta a sinistra della svolta per
    σ≥0.4 in ogni configurazione testata). Headline fragile su margine robusto.
  - **Registro 26 → 49 claim** (+22 `ces_b21`: 7 σ\*, 14 CI, 1 `n_crossings`; +1
    `ces_b14` per 0.019); **token 574 → 611**. **Entrambe le letture:** **8%** sul
    paper intero (49/611), ma **23 claim su 37 token nuovi = 62%** sul materiale b22.
  - **Detector, entrambi riportati** (regola §6/b19): `verify_paper.py --selftest`
    **ALL PASS**; iniezione deliberata `0.871→0.870` in `tab:prices` → **1 FAIL netto**
    (`CLAIM NOT FOUND IN TEX`), ripristinato → **0 FAIL**. `sweep_rounding` probe **BOTH
    PASS**, i **3 falsi positivi noti intatti** (59.4 ×2 in 06_shape, 0.771 in
    09_sensitivity), **0 firme nuove** nelle sezioni toccate. `coherence.py` **0
    DIVERGENT**.
  - **CI: NON eseguita, in attesa di push** — è uno **stato**, non un esito. Il push
    del b22 è ciò che fa girare `.github/workflows/paper.yml` (gated `paths: paper/**`;
    il b21 è fuori da `paper/`, quindi l'esito resta attribuibile al solo b22).
  - **Fuori scope (dichiarato):** retrofit dei generatori di `tab:wagecurve` (referente
    identificato, vedi §5), `tab:delta`, `tab:baseline`, `tab:marginalturn`; promuovere
    `enable_prices` a feature; eseguire la variante §1.2 del b21 (pinna la quota salari,
    citata come scartata in `11_limitations`).

- **Brief 22-bis — tre correzioni di documentazione/artifact (commit `c2275f6`, solo
  `paper/`+`results/`):**
  - **`results/paper_rounding_sweep.csv` rigenerato 84.354 → 94.125 righe.** Lo snapshot
    committato descriveva il paper **pre-b22**. **Precedente registrato come REGOLA:**
    uno snapshot **tracciato** deve seguire la sua sorgente; lasciarlo stale per
    preservare un piano di commit è la classe di drift che b18–b20 hanno chiuso. **Il
    piano di commit è una convenzione; la corrispondenza artifact↔sorgente è un
    invariante.** (Il b22 l'aveva *ripristinato* invece di aggiornarlo — corretto qui.)
  - **Omonimia «pass-through» disambiguata.** `03_model.tex:131` (senso cassa, già
    «*intra-period* pass-through») resta **byte-intatto**; qualificato il senso nuovo
    alla **prima occorrenza** in `07_stress.tex:78` («price pass-through»). Principio:
    **il costo lo paga il testo che ha introdotto l'ambiguità**, non la prosa consolidata.
  - **`numéraire` uniformato** alla forma maggioritaria pre-esistente (accentata): **0
    piane / 16 accentate**. Nessuna cifra, solo grafia.

- **Brief 23 — riposizionamento rispetto al modello base (commit `6e65ce2`, solo
  `paper/` + lo sweep CSV):** quattro siti toccati insieme, sola prosa, solo
  aggiunte. Nessuna cifra cambiata, nessun ambiente `tabular` sfiorato,
  `paper_claims.yaml` intatto ⇒ registro fermo a 49 claim, 569 test invariati per
  costruzione (nessun `src/`, nessun run). Origine: confronto integrale fra il PDF
  di `\citet{Teglio2025}` e i sorgenti `paper/*.tex` a `fb4060a`.
  - I quattro siti (righe post-edit): `06_shape.tex:115` (la congettura),
    `01_introduction.tex:14` (una frase di motivazione), `02_literature.tex:21`
    (variabili congelate + genealogia del numerario), `08_fiscal.tex:50` (la
    replica come validazione incrociata).
  - **IL REPERTO** — le conclusioni del paper base nominano questa estensione e ne
    congetturano l'esito. Teglio §5: il modello «[does] not consider the relation
    between capitalists' accumulated wealth and investments, which can affect both
    the demand and the supply sides», e «it is hard to imagine how it could solve
    the problem of the lack of consumption goods demand by low income households,
    at least in a model that does not envisage income growth». Il nostro è
    esattamente quel modello (`A` costante, `g=0`), quindi la congettura vi è
    testabile. Il paper ci era arrivato da solo: `06_shape` diceva già «investment
    itself becomes the leak» senza sapere che il reperto era stato previsto.
  - **La mappatura HA TENUTO, al livello calibrato** — e la differenza di oggetto è
    dichiarata nella stessa frase. La congettura riguarda il vincolo di ricchezza
    sulla spesa delle famiglie a basso reddito; `tab:baseline` misura `dY/dρ` al ρ
    ancorato. Il paper scrive «the closest available counterpart […] not a test of
    the household constraint itself». Nessuna delle forme vietate (`confirm`,
    `proves`, `vindicat`) compare. Il declassamento a «risuona con» era l'esito
    accettabile previsto e non è stato necessario.
  - La clausola condizionale di Teglio è **legata a L1, non promessa**: «income
    growth large enough» rimanda a `\cref{sec:limits}`, e il punto 13 resta una
    decisione non presa.
  - **Le due variabili indipendenti del paper base sono dichiarate congelate**
    (`02_literature`): razionalità delle famiglie (quattro livelli) e simmetria
    della rete. Con la ragione (per attribuire un effetto al canale
    dell'accumulazione la topologia va tenuta ferma) e il costo misurato
    internamente, non asserito: `\cref{sec:heterogeneity}` mostra il domino che
    passa proprio per le quote di spesa fisse, l'oggetto congelato. Individuato con
    grep reale: `Teglio2025` compariva in 3 siti soli e mai in `02_literature`;
    `rationality`/`network`/`topology`: zero occorrenze pertinenti in tutto
    `paper/`.
  - **Genealogia del numerario — DECISIONE §5.1: il blocco H2 NON è stato
    riaperto.** Nel modello base il prezzo fisso è innocuo, perché il salario non è
    un prezzo ma una quota di ricavi distribuita in parti uguali (Teglio, eq. 8):
    «reale ≡ nominale» non costa nulla se nessun prezzo relativo si muove. Con una
    wage curve il salario è un prezzo relativo, e la convenzione diventa
    load-bearing. Il punto vive in `02_literature` come affermazione genealogica
    (da dove viene l'assunzione, perché era innocua, perché qui non lo è più), non
    come riformulazione di H2. H2 resta bracketed e byte-invariata nei sei siti del
    b22: `07_stress`, `10_discussion`, `11_limitations`, `frontmatter` → zero hunk,
    verificato.
  - **Detector, tutti e quattro riportati (regola §6/b19):** `verify_paper.py` 0
    FAIL, `--selftest` ALL PASS; input noto-cattivo → 1 FAIL netto → ripristino →
    0 FAIL byte-esatto; `sweep_rounding.py` rigenerato (regola b22-bis), 0 firme
    nuove, i 3 falsi positivi noti intatti (59.4 ×2 in `06_shape` righe 98/109,
    0.771 in `09_sensitivity` riga 204), variazioni CSV confinate ai 4 file toccati
    (soli shift di `tex_line`).
  - **DEVIAZIONE DICHIARATA #1 — il bersaglio dell'iniezione, e un debito di
    copertura scoperto così.** Il brief indicava `tab:government`; nessun claim del
    registro copre quella tabella, quindi iniettare lì è vacuo (0 FAIL: un check
    che passa senza ispezionare, §6). Il detector è stato provato su una cella
    coperta (`0.718` in `tab:sobol`, unica nel file) → `CLAIM NOT FOUND IN TEX`.
    `tab:government` si aggiunge quindi al debito di copertura, accanto a
    `tab:baseline`: stessa classe, scoperta per caso mentre si verificava un
    detector. È la regola §6 che si paga da sola.
  - **DEVIAZIONE DICHIARATA #2 — `coherence.py` a 6 DIVERGENT, causa DIAGNOSTICATA
    AL CONTRARIO nel report di sessione** (e nel messaggio di commit di `6e65ce2`,
    che resta com'è: si corregge nel record, non si riscrive la storia). Il
    messaggio attribuisce le 6 divergenze a una «riscrittura non committata di
    `METHODOLOGY.md`». Falso, e verificato: il file presente nel working tree era
    una copia di `istruzioni_progetto.md` — un documento diverso, che inizia con
    `# Istruzioni del progetto`. `METHODOLOGY.md` a HEAD non era stale: contiene
    569 test (riga 1032), 49 claim (riga 1081) e il record b22-ter (riga 1513). Le
    prove usate per dichiararlo stale — «Fase 2», «345 test» — sono menzioni
    storiche dentro un registro cronologico (righe 5, 69, 136, 1282; l'ultima dice
    «non deve ripetersi»). Provato col detector: ripristinato `METHODOLOGY.md` da
    HEAD, `coherence.py` passa da 6 DIVERGENT / 4 coherent a 0 DIVERGENT / 10
    coherent. I sei valori (`1.002`, `0.966`, `0.024`, `0.900`, `0.561`, `0.021`)
    sono presenti a HEAD e assenti dalla copia. Nessuna divergenza era reale.
  - **REGOLA NUOVA, e costosa se ignorata:** prima di stabilire quale di due
    versioni è stale, verificare che siano lo stesso documento. È il raffinamento
    b17 («ogni numero ha IL SUO artifact») applicato a un documento invece che a un
    CSV, e con una posta più alta: committare la copia avrebbe cancellato 823 righe
    della fonte di verità del progetto. Il difetto è stato evitato dalla regola
    «segnalare invece di sovrascrivere», non dalla diagnosi, che era invertita.
  - **CI: VERDE** — run `30593953273` (#11), conclusione **success**, durata
    **2m11s** (job `build` 00:35:03→00:37:11Z, 2m08s). Il push conteneva `6e65ce2`
    (blocco paper) e `ac98384` (questo record); il workflow ha buildato l'albero a
    `ac98384`, e dal run #10 (`fb4060a`) l'unico cambiamento in `paper/**` è il b23,
    quindi l'esito è attribuibile al b23. Contatori del passo diagnostico
    (annotazioni pubbliche del run, referente = il run stesso): **error LaTeX 0,
    reference/citation undefined 0, Overfull hbox 0, Underfull hbox 0**; unico
    warning = deprecazione Node.js 20 (infrastruttura GitHub, non il paper). Nessun
    conteggio di pagine: il workflow non lo emette (debito dichiarato §3).
  - **Fuori scope, dichiarato:** il punto 13 (la clausola di Teglio si cita, non si
    esegue); il credito (Teglio nomina il debito nello stesso passaggio — non
    raccolto: il cap `I ≤ π` non morde, `investment_floor` μ\* = 0.226 in entrambe
    le vintage Morris); retrofit dei generatori di `tab:wagecurve`, `tab:delta`,
    `tab:baseline`, `tab:marginalturn`; `PaperV1.pdf` stale (tracciato, fermo a
    `e9403be`) — commit a sé.

- **Brief 24 — portare il paper a working paper di qualità da rivista (solo `paper/`
  + un generatore di figura + rigenerazione dello snapshot sweep; nessun `src/`,
  nessun run del modello; 569 test invariati per costruzione):** sette commit locali
  per blocco, STOP pre-push. Destinazione: working paper completo da mandare ad
  Andrea Teglio col repository (non una submission). Principio guida: **il paper è il
  risultato, METHODOLOGY è il processo** — la voce narrante del diario esce, la
  sostanza metodologica resta. Eseguito **dopo** il b25 (fuori ordine: il b25 aveva
  registrato «b24 non ancora fatto»).
  - **Blocco 1 — §1+§2 (commit `31b123c`):** blocco autore compilato (cognome
    Saramin, email istituzionale `904394@stud.unive.it`, affiliazione Ca' Foscari,
    URL repo nel footnote — cognome e URL **derivati da CITATION.cff/git remote**,
    email e affiliazione **chiesti al PI**, non inventati). **DEVIAZIONE DICHIARATA:**
    `\date{}` **vuoto** su richiesta esplicita del PI, non una data-stringa fissa come
    da brief — ma ugualmente **build-independent** (due build della stessa sorgente
    danno lo stesso documento), che era la preoccupazione del brief con `\today`.
    Abstract 304 → **243 token resi** (≤250; contati escludendo/i­ncludendo i token
    math): tolti i dettagli dello stimatore e la percentuale dei punti risolti (in
    §9). **Bracket H2 preservato BYTE-INVARIATO**; nessuna delle tre forme vietate
    («H2 cade/tiene/è rovesciata»). Azzerata anche la checklist stale in
    `paper/README.md` (unico residuo del grep placeholder di criterio 1; è la guida
    di build della cartella paper, distinta dal README-radice del b25).
  - **Blocco 2 — §3 registro (commit `095fbb3`):** inventario del diario costruito con
    **grep reale** (lezione b18). Nell'introduzione «A note on what this paper reports»:
    la sostanza (regola sui numeri, negativi riportati non ricalibrati) **fusa** nel
    paragrafo «The reported numbers» di `05_protocol`; nell'intro restano 2 frasi con
    `\cref`. Nove occorrenze riformulate/espunte (`the project('s)`, `an earlier
    draft`, `we set out`, `unlooked-for`). **Lasciate con ragione:** `01_intro:37`
    «This paper's organising finding» (uso accademico standard); `paper/README.md:155`
    (prosa di build). Solo prosa, nessuna cifra.
  - **Blocco 3 — §4 declbox (commit `bfacf31`):** +`amsthm`; due ambienti `amsthm` resi
    come box `mdframed` (stile `declstyle` invariato) via `\newmdtheoremenv`, definiti
    dopo `cleveref` con `\crefname` espliciti. **8 box convertiti, testo interno
    BYTE-INVARIATO:** `modelassumption` ×2 (invariante L≤N, SFC in `03_model`),
    `remark` ×6. **Residuo dichiarato:** `04_calibration` porta «An earlier version of
    this project» (voce di diario) **dentro** un box; la regola §4 «testo interno
    invariato» prevale sul §3, quindi resta. Nessun box era `\cref`'d: nessun
    riferimento rotto.
  - **Blocco 4 — §5.1 figura (commit `09a9a5d`, + igiene `600cd2d`):** `03_model`
    passa da 0 a 1 figura. Schema del flusso monetario (`fig:model`) con **generatore
    committato** `scripts/make_fig_model.py` (matplotlib, la toolchain esistente:
    **niente TikZ**, che il preambolo evita per il timeout Overleaf). Schema, nessuna
    cifra misurata. La larghezza `0.92\textwidth` creava 2 firme di doppio
    arrotondamento **spurie** (coincidenza con `ces_b17_util_effect.csv`); corretta in
    `.92\textwidth` (zero iniziale omesso → nessun token `\d+\.\d+`) → **0 firme nuove**.
  - **Blocco 5 — §5.2 tabella di confronto (commit `71509ef`):** nuova `tab:teglio` in
    `02_literature`, qualitativa (nessuna cifra, nessun generatore) su 9 dimensioni.
    **RIVERIFICATA riga per riga contro `2024_Teglio_JEIC.pdf`** (estrazione pypdf, 33
    pagine), non copiata da `confronto_teglio.md`: fixed job links («a firm has always
    the same number of employees»), salario come quota di ricavi «in equal parts»
    (eq. 8), investimento assente, quattro «rationality endowments», «regularity of
    economic interactions», inventari, «progressive tax … universal basic income»,
    «Monte carlo». `confronto_teglio.md` resta materiale di lavoro non tracciato.
  - **Blocco 6 — §5.3 data & code availability (commit `57e745b`):** paragrafo in coda
    a `05_protocol`: URL repo + rimando a `CITATION.cff` (nessun hash hard-coded, non
    auto-referenziabile); registro dei claim (**49 claim, letto live** da
    `paper_claims.yaml`, non ricopiato dal brief); `verify_paper.py`/`coherence.py`
    committati ed eseguibili; eccezione `ces_decomposition.csv` (archiviata, «not
    recoverable from the committed CSV», citata da 0 file in `paper/`). **DEVIAZIONE
    DICHIARATA (§6):** «49» stampato ma **non** aggiunto a `paper_claims.yaml` — è la
    dimensione del registro stesso (auto-referenziale, non esprimibile come
    artifact+filtro+cella) ed è riprodotto eseguendo `verify_paper.py`, citato nella
    stessa frase.
  - **Detector, tutti eseguiti e riportati (regola §6/b19):** `verify_paper.py`
    **0 FAIL**; `--selftest` **ALL PASS**; iniezione noto-cattivo su cella coperta
    (`sobol_delta_S1_viable`, `tab:sobol`, 0.718→0.719 — **non** `tab:government`, che
    nessun claim copre) → **1 FAIL netto** (`CLAIM NOT FOUND IN TEX`) → ripristino
    byte-esatto → **0 FAIL**. `coherence.py` **0 DIVERGENT**. `sweep_rounding.py`
    rigenerato (regola b22-bis: `results/paper_rounding_sweep.csv` segue la sorgente);
    confronto set-wise (chiave senza `tex_line`): **0 firme nuove, 0 rimosse**, i **3
    falsi positivi noti intatti** (59.4 ×2 in `06_shape`, 0.771 in `09_sensitivity`);
    probe **BOTH PASS**.
  - **CI: NON eseguita, in attesa di push** (stato, non esito). Il brief tocca
    `paper/**` e **aggiunge `amsthm`**: la build CI è l'unico banco di prova (nessun
    motore LaTeX locale). `amsthm`/`mdframed` sono TeXLive standard, rischio basso; un
    primo push che fallisse per un pacchetto è esito **normale** (brief §7).
  - **Fuori scope (dichiarato):** nessuna nuova scienza, nessun run; retrofit dei
    generatori di `tab:wagecurve`/`tab:delta`/`tab:baseline`/`tab:marginalturn` (debito
    dichiarato); versione submission-ready JEIC (decisione separata, non presa).

- **Brief 25 — igiene del repository prima dell'invio a Teglio (solo documentazione
  + una eccezione §5 approvata; nessun `src/`, nessun run del modello; 569 test
  invariati per costruzione, eseguiti e riportati prima 569 / dopo 569):** sei
  commit locali, uno per task, STOP pre-push. Il repo era da mandare a Teglio col
  working paper (b24, **non ancora fatto**: b25 eseguito fuori ordine).
  - **Task 1 — nuovo `README.md` (commit `214fdd6`, 125 righe):** il vecchio README
    era diventato un diario (1106 righe) che duplicava METHODOLOGY.md. Sostituito con
    una porta d'ingresso convenzionale (badge CI, abstract in riuso stretto dal paper
    + link all'artifact PDF, install, quickstart verificato in 0.2 s, tabella compatta
    driver→artifact coi tempi e i thread BLAS, Verification in prima pagina, albero,
    cite, licenza, further docs). **Nessun risultato per brief né cronologia.** Unico
    numero stampato oltre l'abstract: 569 test, **letto da pytest in questo run** (§5).
  - **Task 2 — archiviato il vecchio README in `docs/project_log.md` (commit `de193bb`):**
    `git mv` (rename al 99%) + intestazione di congelamento (snapshot a `bcab5c0`,
    2026-07-31; fonti correnti METHODOLOGY.md e paper/). Un log archiviato non ha una
    sorgente da seguire — ma solo se lo dichiara (il difetto chiuso dal b22-bis).
    **Controllo materiale orfano:** l'*Interpretive frame* (assente da METHODOLOGY.md,
    grep=0) è **conservato dall'archiviazione stessa** (vive nel log archiviato, in
    `RESULTS.md` e in gran parte in `11_limitations.tex`); l'operazione è uno spostamento,
    non una cancellazione, quindi **nulla è orfano**.
  - **Task 3 — `LICENSE` (MIT) e `CITATION.cff` (commit `8919f70`):** titolare/autore
    **Mattia Saramin**, **chiesto e confermato dal PI** (il frontmatter del paper usa
    ancora placeholder `[Surname]`; non inventato). CITATION.cff formato GitHub standard,
    senza version tag (nessun tag di release esiste).
  - **Task 4 — `.gitattributes` tracciato, `_results_body.tmp` rimosso (commit `b83cff6`):**
    `.gitattributes` (`text=auto eol=lf` + marcatori binari) normalizza i fine-riga
    Windows↔CI Linux; il `.tmp` era un frammento Results non tracciato (residuo di build).
  - **PREMESSE DEL BRIEF GIÀ STALE — verificate contro il repo, non rieseguite alla
    lettera** (il brief era scritto prima del b23): **(a)** `PaperV1.pdf` era dato per
    tracciato → in realtà **già risolto dal b23** (`bcab5c0`: untracked + `.gitignore
    /PaperV1.pdf` con commento che rimanda alla "Repository structure" del README —
    era il "commit a sé" promesso qui sopra); nulla da rifare. **(b)** `RESULTS.md` dato
    per emettere `DOCUMENT MISSING` → coherence.py riportava **0 missing**, perché il
    file **esiste su disco** (untracked) e coherence legge il filesystem.
  - **Task 4.3 — `RESULTS.md`: RIDICHIARATO debito, non cambiato (opzione 3).** La
    decisione è **già presa e documentata** ("untracked by explicit decision, Mattia
    2026-07-28", docstring di `coherence.py`; target `required:false` nel registro).
    L'opzione "rimuoverlo dalla lista di `coherence.py`" **tocca `scripts/`** → vietata da
    §5. Lasciato com'è: su clone pulito è assente e coherence emette il declared-debt,
    per costruzione. **`.claude/`** resta escluso via `.git/info/exclude` (non tracciato);
    non aggiunto a `.gitignore` committato — un clone esterno non ha un `.claude/` da
    ignorare.
  - **REGRESSIONE DI COHERENCE INTRODOTTA DAL TASK 1, e la sua ECCEZIONE §5 (commit
    `f3e27c0`, approvata dal PI).** Rendere il README magro ha tolto **10 numeri headline**
    (indici Sobol/b14, slope) che `scripts/paper_claims.yaml` marcava README.md come
    documento **richiesto**: coherence.py è passato da **10 coherent / 0 DIVERGENT / EXIT 0**
    a **10 DIVERGENT / EXIT 1**. Il brief prevedeva un cambio di output di coherence dal
    **Task 4.3**, non dal Task 1: **premessa mancata, dichiarata.** La correzione onesta
    è togliere README.md dall'`appears_in` di quei 10 claim (il registro dichiara che
    `appears_in` è costruito con grep reale — elenca *dove* un numero appare; dopo il Task 1
    non appare più nel README), **non** `required:false` (fingerebbe un doc opzionalmente
    assente). Tocca `scripts/` → **eccezione §5 mirata, decisa dal PI** perché è il
    completamento del Task 1 ed evita di spedire a Teglio un checker rosso. **Esito:
    coherence torna a 10 coherent / 0 DIVERGENT / EXIT 0** (sommario identico al pre-brief);
    i 10 claim restano incrociati su paper+METHODOLOGY+notebook (+RESULTS se presente);
    solo `sobol_delta_S1_viable`, che viveva solo in paper+README+RESULTS, scende a
    single-doc su clone pulito (onesto). `verify_paper.py` **invariato** (0 FAIL prima e dopo).
  - **Detector prima/dopo (regola §6):** `verify_paper.py` 0 FAIL / EXIT 0 prima e dopo;
    `coherence.py` 0 DIVERGENT / EXIT 0 prima e dopo (con la finestra rossa intermedia
    sopra, chiusa dall'eccezione); `pytest` 569 verdi prima e dopo (nessun `src/`, `tests/`
    toccato). **Fuori scope, dichiarato:** il paper (b24); tracciare i documenti di lavoro
    (`brief_*.md`, `istruzioni_progetto.md` — non riunificare con METHODOLOGY.md, è la
    confusione che ha prodotto la diagnosi invertita del b23); `performance/engine.cpp`
    resta STALE (il README lo dichiara non in uso).

- **Brief 26 — audit di coerenza paper ↔ CODICE ↔ artifact (solo VERIFICA; nessun
  `src/`, nessun `paper/`, nessun run del modello; 569 test invariati, eseguiti e
  riportati 569 prima / 569 dopo):** chiude il **quarto asse** della toolchain, che era
  il buco — nessuno strumento verificava che equazioni e parametri *stampati* nel paper
  fossero quelli che il codice *calcola*. Referto in `docs/audit_b26_paper_codice.md`;
  commit locale, STOP pre-push.
  - **Fase 1 — `scripts/verify_model.py` (deliverable nuovo committato).** Confronta i
    default reali di `MacroModel.__init__` (letti via `inspect.signature`, **import senza
    run**) e le costanti di modulo (`U_REF`, `ANCHOR_*`) contro i valori di `tab:params`;
    round-once `ROUND_HALF_UP`; `context` regex per pinnare la riga (come `verify_paper`).
    `--selftest` **FALLISCE netto** su default iniettato (0.05→0.09 ⇒ MISMATCH) e su
    needle forgiato (⇒ NOT_IN_TEX). **Esito: 19/19 MATCH** (`results/audit_b26_params.csv`).
  - **Fase 2 — audit manuale delle 13 equazioni/sequenza.** Il sito a rischio massimo, la
    **FOC dell'impresa** (`af27915`, `w_t/P`), è **PULITO**: il paper dice `MPL=w`, il
    codice usa `w_t` nel default (numerario 1) e `w_t/P` solo col probe prezzi, dichiarato
    in `07_stress`. Zero divergenze di cifra. Divergenze trovate, tutte fra un'equazione
    stampata e una **generalizzazione del codice inerte nei risultati**: **sito 7**
    (`eq:accelerator` scrive `u_{t-1}` realizzato; il codice legge l'aspettativa `u^e` con
    `λ_u`, uguali a `λ_u=1` default mai sweepato — `NON_DICHIARATO`, inerte); **sito 2**
    (il codice ha un **quarto** regime `"capital"` / soffitto `Y_max(K)` per σ<1,
    `ces_capital_ceiling`, che il paper non nomina — `NON_DICHIARATO`); **sito 8** (cap a
    `Π_{t-1}` nel codice vs `Π_t` nel paper, immateriale in steady state); floor intero
    su `L` e guardia `max{·,0}` sul consumo (triviali). Siti 1,3,5,9,10,11,12,13 OK.
  - **Fase 3 — copertura misurata:** 49 claim di registro; **611 token decimali** (=sweep)
    + 415 interi, 423 distinti; generatore committato `scripts/audit_b26_uncovered.py` →
    `results/audit_b26_uncovered.csv`. **Falsi positivi §5.3 verificati ancora tali e NON
    corretti** (`0.771` derivato #1; `59.4` `tab:baseline` #2). Retrofit generatori
    **proposti non eseguiti** (`tab:wagecurve` prossimo candidato; `tab:baseline` va prima
    dotata di referente).
  - **STATO EREDITATO, non mio, dichiarato:** all'avvio l'albero portava **`paper/`
    modificato non committato** (7 file, 71+/341−: anglicizzazione + ristrutturazione
    intro/lit) che **non ho toccato**. Una modifica del WIP è una **regressione**:
    `eq:investment` ha perso `\clip` (HEAD corretto: `\clip(ρΠ_{t-1}φ_t,I̲,Π_t)` = il
    codice; worktree: tupla senza operatore). La Fase 2 è classificata contro **HEAD** come
    referente canonico. Il byte-diff del CSV `paper_rounding_sweep.csv` rigenerato è
    **interamente spiegato dal WIP** (il committato è coerente con `HEAD:paper/`, **non è
    stale** — token `0.42` da riga 46 in HEAD a riga 23 nel worktree); CSV ripristinato.
  - **NUOVO PUNTO CIECO (causa diversa dai #1–#4).** I quattro punti ciechi esistenti sono
    tutti del **toolchain dei numeri** (sweep: derivati / tabelle senza sorgente; verify/
    coherence: substring; b24: misurato-senza-CSV). Il b26 aggiunge, di **natura diversa**:
    **l'asse paper↔codice delle EQUAZIONI resta solo-manuale.** `verify_model.py` copre i
    **default dei parametri**, non le equazioni: una divergenza equazione↔codice (siti 2,
    7, 8) è colta **solo** dall'audit a mano — parsare LaTeX produrrebbe falsi positivi.
    Regola operativa: **rieseguire l'audit manuale di Fase 2 a ogni modifica di `03_model`/
    `agents.py`/`model.py`**, perché nessun detector lo farà. Distinto dai #1–#4: non è il
    registro né lo sweep, è che le equazioni non sono meccanicamente confrontabili.
  - **Detector prima/dopo (regola §6):** `pytest` 569 verdi prima e dopo (nessun `src/`,
    `tests/` toccato); `verify_paper` 0 FAIL, `coherence` 0 DIVERGENT, `sweep_rounding`
    0 firme invariati; nuovo `verify_model` 0 FAIL. **Osservazione, non riparata:**
    `verify_paper` usa `round()` builtin (half-even) mentre `sweep_rounding`/`verify_model`
    usano `ROUND_HALF_UP` — immateriale sui valori attuali (nessun caso half-way), latente.
  - **Fuori scope, dichiarato:** riparare qualsiasi finding (gerarchia §6: paper vs codice
    non normato ⇒ arbitrato di Mattia, non chiusura d'iniziativa); committare o toccare il
    WIP di `paper/`; promuovere `enable_prices`; affinare `sweep_rounding.py` per i derivati.

- **Brief 27 — sblocca il WIP di `paper/` e ripristina la riproducibilità del b26 (blocco
  paper + `scripts/coherence.py`; nessun `src/`; 569 test invariati, 569 prima / 569 dopo):**
  il working tree di `paper/` era sporco dal b26 (WIP non committato, ereditato) ⇒ i finding
  di Fase 2 del b26 erano senza referente riproducibile. Questo brief **landa il blocco** e li
  rende citabili. **Gate rispettato:** la caratterizzazione è committata **prima** del blocco
  paper (l'ordine dei commit è la prova). Commit locali, STOP pre-push.
  - **Fase A — caratterizzazione (`docs/wip_paper_caratterizzazione.md`, sola lettura).** Il WIP
    ereditato è **anglicizzazione + ristrutturazione**: contenuto e le **5 conseguenze operative
    del b23** preservati (citati riga per riga), **H2 bracket intatto** in `frontmatter` (nessuna
    delle 3 formulazioni vietate), token decimali invariati (614=614). **0 RIMOZIONE_DI_CONTENUTO**;
    **2 REGRESSIONI**: `\clip` perso in `eq:investment` e **`paper/.gitignore` cancellato** (ignorava
    solo artefatti build LaTeX). Regressione oltre `\clip` ⇒ **decisione al gate a Mattia**.
  - **Fase B — riparato e landato IN BLOCCO** (un solo commit `paper/`). Decisioni del gate: (1)
    `.gitignore` **ripristinato** a HEAD; (2) `\clip\big(...)` **ripristinato** (forma HEAD = codice
    `min(max(·, investment_floor), profit_last_period)`); (3) **de-dash PAPER-WIDE** (Mattia: niente
    em/en-dash) — 123 `---`→virgola, 35 `--`→trattino su `sections`+`appendices`; 2 celle n/a
    `& ---`→vuote; marcatori `do-not-hand-edit` ripristinati; blocchi generati byte-identici.
  - **CONSEGUENZA NUOVA del de-dash sui token (dichiarata).** Convertire i `--` dei **range** in
    trattino **disattiva la guardia-range b20 dello sweep** (che si basava sul `--`): gli estremi
    superiori dei range in `09_sensitivity` (`0.030-0.045`… e `0.475-0.649`…) sono ora letti come
    **negativi** (`-0.045`…). Token decimali **611→619**; candidati sweep 803→804 righe / 172→173
    occorrenze — **tutti coincidenti** (blind-spot #1: prossimità ≠ attribuzione; artefatti senza
    referente), **nessuna firma double-round confermata**. Non riparato: lo sweep funziona, la
    guardia è **muta non rotta**, e un range con trattino è tipografia corretta. Distinto dai punti
    ciechi #1–#4 (è una conseguenza di una *decisione*, non un difetto latente del detector).
  - **Fase C — verde e provato:** `pytest` **569**; `verify_paper` 0 FAIL (1 AMBIGUOUS per
    costruzione, 1 SKIP dichiarato) + `--selftest` PASS; `coherence` 0 DIVERGENT + `--selftest` PASS;
    `verify_model` 19 MATCH + `--selftest` PASS; `sweep_rounding` nessuna firma nuova. **CI: il PDF si
    verifica solo su push** (nessun engine LaTeX locale) ⇒ i quattro contatori (overfull/underfull/
    errori LaTeX/ref-cit undefined) sono **deferiti al push** (conferma di Mattia); il conteggio
    pagine NON è emesso dal workflow, non citarlo come misurato.
  - **Fase D — b26 rieseguito sul tree pulito** (`docs/audit_b26_paper_codice.md` §0). **RISOLTI:**
    stato ereditato §0.1; sito 8(a) `\clip`. **CONFERMATO** sito 2 `NON_DICHIARATO` con ricerca
    **paper-wide** (nessun capital ceiling/`Y_max`/4° regime in alcuna sezione o appendice — il
    raffinamento b17 non lo ribalta). `verify_model` 19 MATCH invariato.
  - **Fase E — riparato il detector `DOCUMENT MISSING` (commit a sé).** `RESULTS.md` untracked ma
    presente su disco ⇒ il check per `os.path.exists` taceva sulla macchina dell'autore e sparava
    solo su clone fresco. Riparato al **tracciamento git** (`git ls-files --error-unmatch`): emette
    `DOCUMENT UNTRACKED` identico ovunque; `--selftest` che **FIRE** su file presente-ma-untracked;
    invariante §6 riallineato (sopra). **0 DIVERGENT invariato.**

- **Brief 27-bis — riparazione trattini + passaggio a prosa scientifica, e il paper COMPILA
  (branch `b27-verify`; nessun `src/`; 569 test invariati). NON mergiato, NON su `main`.** Chiude
  il de-dash del b27 (che aveva reso i `--` in trattino breve anche negli intervalli), elimina
  liste ed enfasi, e — l'unica prova che regge — **compila in CI**. Le fasi sono commit separati
  sul branch, sul precedente b22/b22-bis/b22-ter.
  - **Gate §1 (deciso da Mattia):** `make_tab_sobol.py` emetteva `\textbf` dentro il blocco
    generato di `tab:sobol` ⇒ «togliere tutto il grassetto» collideva con l'invariante b20.
    Decisione: **Opzione A — grassetto rimosso anche dalle tabelle**, modificando il **generatore**.
  - **Fase 1 — intervalli:** ripristinati i `--` **solo negli intervalli numerici** (`$X$--$Y$`,
    22 math + 8 bin δ bare in `09_sensitivity`), **non** gli em-dash (restano virgole). Chiusura:
    `sweep_rounding` torna a **611 token**, gli 8 candidati fantasma da intervallo spariscono
    (la guardia-range b20 dello sweep, che si basa sul `--`, torna operativa).
  - **Fase 2 — rilettura umana dei 147 siti em-dash→virgola** (punto cieco #4, nessun detector):
    la gran parte è appositiva e legge bene; corretti **8 comma splice** (`:` dove elabora, `;`
    dove coordina). Referto in `docs/b27bis_prosa.md`.
  - **Fase 3 — 8 liste → prosa:** **0 `itemize` / 0 `enumerate`**; ogni `\item` mappato a una frase
    (nessuna proposizione persa/nuova); numerazione conservata dove referenziata (`04` tier, `07`
    step); **611 token invariati**; nessun `\label` dentro un `\item` (nessun `\cref` rotto).
  - **Fase 4 — enfasi rimossa: `\textbf` 65 / `\textit` 7 / `\emph` 133 / `\mathbf` 3 → 0/0/0/0.**
    19 titoli run-in → `\paragraph` (rule 1; il pattern First/Second/Third di `01` era già piano
    dal WIP b27). Generato: `make_tab_sobol.py` de-grassettato, `tab:sobol` rigenerato e
    **byte-identico**. Rilette le 133 `\emph`: **0 riformulazioni** necessarie (il lessico porta
    già i contrasti — «rather than», «not…but», «only if», i numeri). `verify_paper` **0 CLAIM
    NOT FOUND** (togliere `\textbf{0.718}`→`0.718` non ha scollegato alcun `context`).
  - **Fase 5 — COMPILA.** Il b27 aveva lasciato il paper mai compilato dopo 158 modifiche + `\clip`;
    il b27-bis ne aggiunge molte di più e tocca **strutture** (liste, `\paragraph`). Pushato **solo
    `b27-verify`** (workflow su `paths: paper/**`, nessun filtro di branch; `main` intatto). **CI
    VERDE** (run #13, sha `ea75f7f`): **Overfull hbox 0, Underfull hbox 0, errori LaTeX 0,
    reference/citation undefined 0**. (Il conteggio pagine **non** è emesso dal workflow ⇒ non
    citato come misurato.)
  - **Detector (regola §6):** `pytest` 569 invariati (nessun `src/`); `verify_paper` 0 FAIL +
    `--selftest` PASS; `coherence` 0 DIVERGENT + `DOCUMENT UNTRACKED: RESULTS.md` + `--selftest`
    PASS; `verify_model` 19 MATCH + `--selftest` PASS; `sweep_rounding` **611**, nessuna firma nuova.
    `paper_rounding_sweep.csv` rigenerato **dopo** l'ultimo commit del paper (b22-bis).
  - **Fuori scope, dichiarato:** merge o push su `main` (vietato dal brief — `main` resta a `ec18707`);
    il sito 7 (`u^e`/`λ_u`, b17 assente dal paper — è il brief 28); i due falsi positivi noti
    (`0.771`, `59.4`).

- **Brief 27-ter — incisi ambigui, record §11, e il gate di lettura (branch `b27-verify`;
  nessun `src/`; 569 test invariati). NON mergiato, NON su `main`.** Brief piccolo a tre voci.
  - **Fase 1 — §11 stale (commit a sé).** `METHODOLOGY.md` §11 descriveva ancora
    `make_tab_sobol.py` con gli «stessi grassetti»: dopo l'Opzione A del b27-bis il generatore
    **non emette più grassetto**. Allineata. Terza occorrenza della modalità «un documento
    anti-drift che drifta» (b22-ter). `coherence.py` in §11 era **già** corretto
    (`DOCUMENT UNTRACKED` via tracciamento git, b27 Fase E).
  - **Fase 2 — incisi ambigui → parentesi (commit a sé).** La Fase 2 del b27-bis aveva coperto
    solo i *comma splice*, non l'altra voce del criterio: «apposizione con lista interna, confine
    perso». Il de-dash aveva reso in virgola em-dash che delimitavano apposizioni; con una lista
    interna il confine sparisce. Riparati con **parentesi tonde** (nessun em-dash reintrodotto):
    **3 confermati** (`01_intro` ×2, `02_lit`) + **6 residui** (`07_stress` ×3, `10_disc`,
    `a_validation` ×2); **4 lasciati** con ragione (apposizione pulita / corta / lista legittima /
    avverbio). Screen di 42 candidati sfoltito a ~10 leggendo per sito (punto cieco #1: la
    prossimità non è attribuzione). Verdetti in `docs/b27bis_prosa.md` §27-ter.
  - **Detector + CI:** `pytest` **569**; `verify_paper` 0 FAIL / **0 CLAIM NOT FOUND** (le parentesi
    non hanno scollegato alcun `context`) + `--selftest`; `coherence` 0 DIVERGENT +
    `DOCUMENT UNTRACKED` + `--selftest`; `verify_model` 19 + `--selftest`; blocchi generati
    byte-identici; token decimali **611**; sweep rigenerato dopo l'ultimo commit del paper
    (b22-bis; **byte-identico** — le parentesi non muovono token né righe). **CI VERDE** su
    `b27-verify` (run su `c206e79`): **Overfull 0, Underfull 0, errori LaTeX 0, ref/cit undefined 0**
    (pagine non emesse ⇒ non citate). Il commit verde è la **tip** del paper.
  - **Fase 4 — GATE DI LETTURA (di Mattia).** La CI prova che il documento **compila**, non che
    **si legge**: fra b27 e b27-ter sono cambiate 8 liste, 19 `\paragraph`, 186 unwrap di enfasi,
    123 em-dash, 8 splice, 9 incisi. Nessun detector copre la prosa (punto cieco #4). **STOP:** il
    PDF (artifact `paper-pdf` dell'ultima run verde) va letto da Mattia (almeno `01`, `11`, `10`,
    `12`) **prima** di qualunque merge su `main`. Nessun merge finché non lo dice.

- **Brief 27-quater — quattro difetti trovati nel PDF (esito del read-gate del b27-ter;
  branch `b27-verify`; nessun `src/`; 569 test invariati). NON mergiato, NON su `main`.**
  Mattia ha letto il PDF e ha segnalato quattro difetti, uno sistematico.
  - **Fase 1 — anglicizzazione a metà (sistematico).** Il WIP del b27 non era arrivato in
    fondo: documento misto (`labour`/`labor`, `-isation`/`-ization`, `modelling`, `centre`)
    anche in titoli e indice. Uniformato ad **American** con **lista esplicita di parole**
    (80 sostituzioni; evitati i falsi amici `surprise`/`otherwise`/`comprise`/`rise`/
    `raise`/`analysis`). Esenzioni rispettate (citazioni, `.bib`, nomi propri, blocchi
    generati). **0 forme britanniche residue.**
  - **Fase 2 — due punti sospesi (intro).** Residuo dell'`itemize` Supply/Demand convertito
    in prosa: i due punti introducevano un'interruzione di paragrafo ⇒ **chiusi con punto**.
    I tre due-punti che introducono equazioni in display (3.2/3.4/7.2) NON toccati.
  - **Fase 3 — §11 limite quota salari.** Intestazione = soggetto, corpo senza verbo ⇒
    intestazione-etichetta + frase compiuta; 4 numeri invariati.
  - **Fase 4 — 37.7% nominato e registrato (il paper è corretto).** §11 `37.7\%` (in-support
    602/1596) vs `tab:marginalturn` `0.337` (resolved 538/1596): righe adiacenti che
    differiscono di una cifra, confondibili. (1) Nel paper: il 37.7% è **nominato** come
    in-support di `tab:marginalturn`, distinto dal resolved (parole, nessun numero nuovo,
    611 invariati). (2) Nel registro: aggiunti 2 claim (`marginal_rho_star_in_support`,
    `..._resolved`), erano scoperti ⇒ **49 → 51**. **`verify_paper.py` esteso** con un campo
    `fraction` (`scale*mean` di una colonna 0/1 dopo il filtro): un rapporto derivato diventa
    verificabile cella per cella (chiude il punto cieco #1 per colonne booleane); detector
    modificato ⇒ `--selftest` esteso ([4]: 3/4→75.0, valore sbagliato rifiutato). Il **58.7%**
    (below-support) è identificato ma senza colonna booleana ⇒ dichiarato, non registrato.
  - **Fase 5.5 — inventario:** 18 tabelle + glossario notazione (`\cref{app:notation}`) + 8
    figure, tutte numerate e richiamate; i «buchi» del testo estratto sono artefatti `pdftotext`.
  - **Detector + CI:** `pytest` **569**; `verify_paper` **51 claim, 0 FAIL** (1 AMBIGUOUS + 1
    SKIP, 0 CLAIM NOT FOUND) + `--selftest` (incl. frac [4]) PASS; `coherence` 0 DIVERGENT +
    `DOCUMENT UNTRACKED` + `--selftest`; `verify_model` 19 + `--selftest`; blocchi generati
    byte-identici; **611 token**; enfasi 0/0/0/0; liste 0/0; 0 forme britanniche. `sweep`
    rigenerato dopo l'ultimo commit del paper (b22-bis). **CI VERDE** su `b27-verify`
    (4 contatori a 0). **Read-gate del b27-ter RISOLTO** (Mattia ha letto e segnalato); il
    merge su `main` resta la sua decisione esplicita, non presa in questo brief.

- **Brief 27-quinquies — anglicizzazione sui RADICALI, e le frazioni derivate nel registro
  (branch `b27-verify`; nessun `src/`; 569 test invariati). NON mergiato, NON su `main`.**
  Due voci: chiude ciò che l'anglicizzazione del 27-quater aveva lasciato a metà, e rende
  utile il `fraction` mode.
  - **Fase 1 — check dell'anglicizzazione rifatto per RADICALE (detector committato).**
    Il 27-quater dichiarava «0 forme britanniche» ma due erano rimaste (`Modelling` in un
    `\multicolumn`, `stabiliser` nella conclusione): il suo check verificava la lista di
    **inflessioni già osservate**, cioè il proprio input, non la proprietà (invariante §6).
    Nuovo `scripts/check_anglicization.py`: 47 radicali × inflessioni **enumerate**
    `{'', e, es, ed, ing, er, ers, ation, ations}`, su `sections`+`appendices`+`frontmatter`
    (titoli, caption, celle, `\multicolumn`, indice per transitività); **32 falsi amici
    dichiarati** sottratti prima del conteggio e **stampati**; `--selftest` (British→FLAGGED,
    americano/falsi amici→no, blocco generato + citazione→EXEMPT). **Conteggio finale
    stampato: 0** fuori dalle esenzioni. Corretti i due residui (`Modelling`→`Modeling`,
    `stabiliser`→`stabilizer`). **Falso amico scoperto eseguendo il check e dichiarato:**
    `cancellation` (universale, doppia -l- nella forma `-ation` anche in americano) — aggiunto
    ai falsi amici, non special-cased. `realise` verificato **assente**.
  - **Fase 1b — regressione della toolchain, scoperta e riparata.** `verify_model.py` era
    rimasto **britannico** (`target utilisation`, `normalisation anchor/point once`, scritte al
    b26) mentre il 27-quater aveva anglicizzato `tab:params` all'americano: sul tip `007d028`
    dava **15 MATCH / 4 NOT_IN_TEX**, non i «19» del record del 27-quater (**claim stale** —
    l'anglicizzazione aveva rotto il match in silenzio, quarta occorrenza del «documento che
    drifta», qui la toolchain). Allineate le 4 regex all'americano ⇒ **19 MATCH** ripristinato.
    Nessun `src/`, nessun numero cambiato; `results/audit_b26_params.csv` rigenerato.
  - **Fase 2 — frazioni derivate nel registro (`fraction` mode), 51 → 57 claim.** +6 claim:
    5 su `ces_b16_turning_points.csv` (`0.480` contesto marginalizzato, `0.771`, `0.945`,
    `0.887`, `88.7`) + `0.094` ordinario su `ces_b14_summary` (colonna chord della riga
    primary di `tab:repaired`). **`0.771` cambia CATEGORIA** (da falso positivo dichiarato
    dello sweep a numero verificato cella per cella: `curvature_resolved`/`viable` =
    1230/1596): la nota §5 su `0.771` è aggiornata di conseguenza (l'abbinamento dello sweep a
    `ces_b07` resta coincidenza). Le **due occorrenze di `0.480`** puntano ciascuna al **proprio
    artifact** (l.24→`ces_b16.viable`, `context: 'Fraction viable'`; l.63→`ces_b14.frac_viable_4rho`,
    invariato). Nessun `AMBIGUOUS` nuovo.
  - **DEVIAZIONE DICHIARATA (aritmetica): +6, non il «~59» del brief (+8).** (1) **`0.299` non
    registrato**: `anchored_left_of_turn` è NaN sui 1058 punti viable non risolti, quindi
    `fraction` (media, skipna) dà 477/538 = 0.887 non 477/1596 = 0.299 (⇒ MISMATCH); e il
    «0.299» stampato (`09_sensitivity:295`) è la cella chord di `tab:widesigma` (bin σ
    0.649–0.823, n=201), quantità estranea (aggancio in stile `667003b`). (2) **`0.026` già
    registrato** (`repaired_primary_P_wl_OLS`, b19): dei due nominati in §2.2 solo `0.094` era
    scoperto. **Zero righe di `paper/` toccate in Fase 2** (il registro legge; le uniche
    modifiche a `paper/` del brief sono i due fix di Fase 1).
  - **Detector + CI:** `check_anglicization` **0 FLAGGED** + `--selftest`; `pytest` **569**;
    `verify_paper` **57 claim, 0 FAIL** (1 AMBIGUOUS + 1 SKIP, 0 CLAIM NOT FOUND) + `--selftest`
    (incl. frac); `coherence` 0 DIVERGENT + `DOCUMENT UNTRACKED` + `--selftest`; `verify_model`
    **19** + `--selftest`; blocchi generati byte-identici; **611 token**; enfasi 0/0/0; liste
    0/0; 0 forme britanniche. `sweep` rigenerato dopo l'ultimo commit del paper (b22-bis;
    **byte-identico**, sha1 `bdfdefd3` invariato). **CI: in attesa di push** (stato, non esito;
    il paper cambia solo due parole su righe esistenti, nessun token/riga spostati — l'unico
    banco di prova resta la build su `b27-verify`; quattro contatori e verifica green-vs-tip da
    riportare qui appena verde). **STOP: nessun merge, nessun push su `main`.**

**Attivo:** nessun task di implementazione in corso. Prossimo blocco sotto.

**Successivi:** ~~8) produttività eterogenea tra imprese~~ — **CHIUSO dal brief 10:
decisione presa, lato imprese dichiarato quasi-rappresentativo con evidenza misurata,
feature non implementata, riallocazione = future work (punto 12)**; **9) prezzi endogeni
(parte salario FATTA col brief 07; il PREZZO PROBATO col brief 21 — `P=w_t/w_bar`, probe non
feature, H2 rovesciata via Pigou — vedi sotto)**; **10) aspettative
adattive — parte DOMANDA FATTA col brief 08** (σ\* λ_e-invariante; ipotesi di
stabilizzazione c0=2.0 non confermata); **10-bis) aspettativa sull'INVESTIMENTO — FATTA
col brief 17** (acceleratore su `u^e`; ipotesi §4 **falsificata**: λ_u inerte entro le bande su
[0.25,1.0], meccanismo falsificato — `u` persistente; **H1 più forte**; solo λ_u=0 muove ρ\*).
**Resta il punto 10-ter** (smoothing di `profit_last_period`, dichiarato non fatto);
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
> `parameter_notes.md`). **Il PREZZO è ora PROBATO (brief 21, punto 9-bis):** normal-cost
> `P=w_t/w_bar` (markup e produttività costanti, `mu` cancella, zero parametri liberi nuovi),
> **probe non feature** (`enable_prices` default False, fuori dalla SA). Esito: col salario reale
> costante per costruzione il meccanismo di H2 (oscillazione che erode capitale) è **ucciso** e la
> sua conclusione è **rovesciata** via il canale Pigou (bilanci reali) — prima ipotesi di
> stabilizzazione confermata dopo quattro falsificazioni. Fuori scope dichiarato: la variante a
> costo unitario endogeno (§1.2, che pinna la quota salari) e la spirale prezzi-salari. Nota: già
> senza prezzi endogeni il **markup implicito** (`prodotto medio / w_t`) è un **esito**. Per il
> blocco prezzi come *feature* (non probe) serviranno dati sui markup (De Loecker, Eeckhout &
> Unger 2020).

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
incoraggiante"; periodo = 1 anno dichiarato). ~~Aperto: la **sensitivity di `U_min`**~~ **CHIUSA dal brief 13/14**
(`u_min` è fra i **17 parametri** dello screening Morris: μ\*=8.52, conf 7.87 su
`slope_raw`, **0.0000** su `viable` — screenato inerte, non sopravvissuto al Sobol;
`ces_b14_morris.csv`); e
**notebook: aggiungere le sezioni "wage curve"
(σ*(η), brief 07) e "aspettative adattive" (σ*(η;λ_e) + mappa di collasso,
brief 08) al prossimo consolidamento** — i brief 07 e 08 hanno lasciato le figure
(`ces_b07_sigma_star_eta.png`, `ces_b08_sigma_star_lambda.png`,
`ces_b08_collapse_map.png`, `ces_b08_trace.png`) in `results/` e referenziate dal
README, ma il notebook copre ancora solo brief 04/05. **Il brief 08 non aggrava né
salda questo debito** (i risultati λ_e sono nel README; notebook al consolidamento).

---

## 9. Vincoli / invarianti — DA RIPORTARE ESPLICITAMENTE IN OGNI BRIEF

Chi implementa non ha accesso alla storia del progetto né alle conversazioni di
progettazione. Ogni brief deve elencare gli invarianti pertinenti come non
negoziabili.

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
  >
  > **✅ APPLICATO dal brief 14 (task D).** Il criterio nuovo vive in `src/experiment.py`
  > come costanti sorgente (`BYTE_CHECK_ULP = 8`, `BYTE_CHECK_ATOL = 1e-12`,
  > `compare_artifacts`, `regime_signature`), non come scelta per run. Due limbi che non
  > si compensano: **≤8 ULP con pavimento assoluto sui LIVELLI**, e **regime a tolleranza
  > zero** (viability, vincolo che morde, segno risolvibile, `Dead_Firms`). Baseline
  > ri-fissata sulla fetta del brief 12: **7/7 PASS, deriva significativa 0,00 ULP** — cioè
  > *oggi* riproduce esattamente, mentre il brief 13 misurò 2,1 ULP sullo stesso codice:
  > **la deriva è intermittente**, che è la ragione più forte per ritirare l'uguaglianza
  > esatta (un criterio che passa a seconda del giorno non porta informazione).
  > Due limiti misurati mentre lo si costruiva, entrambi dichiarati nel sorgente:
  > **(i)** ULP puro è inutilizzabile vicino allo zero (`Tax_Rate` a `rr=0`: 3.460 ULP su
  > 1,7e-16) — da qui il pavimento assoluto, e da qui il fatto che il limbo di regime non
  > dichiara un segno che non sa risolvere; **(ii)** il criterio **non si applica a
  > quantità differenziate o fittate** (corda, pendenza, curvatura): la cancellazione
  > catastrofica le rende relativamente instabili da input stabili (`slope_raw`: 3.410 ULP
  > da input a 4 ULP). Quelle sono controllate dal **segno**, non da una tolleranza
  > (`BYTE_CHECK_SCOPE`). Driver aggiornati: b07, b08, b09, b10, b12.
  >
  > **⚠️ DEBITO DICHIARATO (brief 17) — il pin a 8 ULP è troppo stretto per l'ambiente attuale.**
  > Il byte-check di annidamento del brief 17 (λ_u=1 vs i quattro panel committati) dà `ok=False`
  > su b05/b07/b09 per **solo drift d'ambiente a regime intatto**: max abs dev **7,6e-11** su
  > `Total_Capital`, **immutato dal brief 17** (git-stash: brief-17-default ≡ pre-brief-17, dev=0.0),
  > e b10 è PASS pulito (0 ULP). Il pin `BYTE_CHECK_ULP = 8` fu tarato dal brief 14 su una busta di
  > **2,1 ULP**; le celle di collasso c0=2.0 in questo ambiente arrivano a **~1342 ULP relativi** a
  > regime intatto — oltre il pin, ma cinque-sei ordini sotto un cambiamento reale (~1e13 ULP). **Se il
  > pin resta com'è, ogni brief futuro mostrerà `ok=False`, e un detector che fallisce sempre smette di
  > essere letto.** Da risolvere in un brief dedicato: **o** ri-derivare il pin sulla busta misurata,
  > **o** riformulare il criterio come **regime-first** con la **deviazione ASSOLUTA riportata accanto**
  > (il limbo di regime già c'è e passa; è il limbo ULP a essere mal tarato). **Registrato, non risolto
  > qui.** Referto: `results/ces_b17_byte_check.csv`.
- **⚠️ Limite strutturale del blocco capitale — `delta` (elevato dal brief 14, task E).**
  Il brief 11 ha misurato il δ implicito BEA per il perimetro del modello (**≈0.090**); il
  brief 13/14 ha misurato che nella banda δ ∈ [0.075, 0.09] sopravvivono **0 punti su 832**
  (taglio `ces_b16_turning_points.csv`), con `ST(delta|viable)` = **0.916** (`ces_b14` OLS) vs
  **1.0018** (`ces_b13` corda) — due vintage, entrambe corrette per il proprio referente
  (`ces_b14_sobol_indices.csv`, `ces_b13_sobol_indices.csv`). Messi insieme: **al δ che i dati implicano il
  modello non esiste.** Non è robustezza, è la firma di `g = 0` letta dalla chiusura
  `I/K = δ + g` (brief 11): senza crescita l'investimento di steady state copre solo il
  deprezzamento, quindi δ empirico erode il capitale a ogni periodo. δ=0.05 non è dove i
  dati lo mettono, è **dove `g=0` lo costringe a stare perché il modello sopravviva**.
  Stessa firma già registrata dal lato dei livelli (I/Y e K/Y business non stanno insieme
  senza crescita). Da riportare come **limite dichiarato**, mai da ricalibrare; la
  riparazione è un meccanismo (punto 13, crescita di `A`), dichiarato future work.
- **README, codice e figure coerenti tra loro** (è già emerso un disallineamento
  documentale in passato — la spec "Fase 2" fantasma: non deve ripetersi).
- **Ancoraggio bibliografico:** ogni scelta di modellazione e ogni parametro
  motivato su due piani — teorico ed empirico (fonte citabile). Se una fonte non
  esiste o non è nota, **dichiararlo e cercarla, non inventarla.**

---

## 10. Flusso di lavoro e divisione dei ruoli

- **L'implementazione del codice** è un'attività separata, che lavora sul
  repository a partire dai brief.
- **La fase di progettazione** serve a: progettazione economica e architetturale,
  ricerca bibliografica e stime dei parametri, analisi e interpretazione dei
  risultati, revisione critica, scrittura. **Non** implementazione.
- Quando una decisione è matura, l'output è un **brief di implementazione**,
  autosufficiente: cosa cambiare e dove (file/funzioni), equazioni
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
  di `Firm`, il ventaglio la popola dal modello; **brief 17:** stato `expected_utilization`
  (u^e) aggiornato via `adaptive_expectation` in `step_production` e **letto dall'acceleratore
  in `plan_investment`** al posto di `utilization_last_period` (che resta come diagnostica);
  **brief 21 (probe prezzi):** i 5 siti del libro mastro nominale/reale con **branch esplicito**
  su `enable_prices` (`step_demand` domanda reale con `income/P`,`wealth/P`; `register_demand`
  investimento reale `.../P`; `step_accounting` `sales=P·production`; `step_investment` unità reali
  `budget/P`, denaro `P·unità`; `step_settlement` pagamento `P·unità`, `actual_consumption` resta
  reale), e — completamento del libro mastro (§1.1/§1.4) — **`plan_employment` usa il salario reale
  `w_t/P` nella FOC di profit-max** (a `P=1` == `w_t`, annida η=0)
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
  tocca l'RNG, e validazione `pct_capitalists` ⇒ almeno 1 capitalista (brief 12);
  **brief 17:** parametro `utilization_expectation_gain` (λ_u, default 1.0, validato ∈[0,1]),
  init `expected_utilization = target_utilization`, reporter `Expected_Utilization`/`Util_Effect`
  (media sulle imprese) tenuti **fuori da `_PANEL_METRICS`** come `Capitalist_Consumption`;
  **brief 21:** parametro `enable_prices` (bool, default False, **probe** — non nei default, non
  nella SA), attributo `self.price` (init 1.0, aggiornato `= w_t/w_bar` nel `step()` **subito dopo
  lo step 0, prima del mercato del lavoro**, §1.4, solo se `enable_prices`), reporter `Price`
  (**fuori da `_PANEL_METRICS`**), e `compute_wage_share_profitmax` al salario reale sotto il probe.
  Blocco docstring "PRICE PROBE" col libro mastro di §1.3 (la SPEC, scritta prima dell'aritmetica)
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
- `scripts/run_brief17.py` — **brief 17**, driver dell'aspettativa sull'investimento. Fasi
  `byte-check` (annidamento λ_u=1 su slice, **detector-first**, criterio brief-14) / `phaseA`
  (griglia β×λ_u allo scenario headline, 4 nodi ρ con CRN, 20 seed) / `report` (rigenera i
  deliverable dai run committati, **senza simulazione**). **Ipotesi §4 e soglia del gate §5
  congelate nel sorgente PRIMA dei run** (`HYPOTHESIS`, `GATE_RULE`); thread BLAS pinnati,
  ambiente in `ces_b17_environment.json`. La `sd` raccolta per `Util_Effect` è la **within-tail**
  (temporale), perché la media è ~λ_u-invariante per linearità
- `scripts/run_brief21.py` — **brief 21**, driver del PROBE sui prezzi. Fasi `byte-check` (i due
  annidamenti byte **detector-first**: self-test η=0.10 che FIRES, poi `enable_prices=False`/`=True`
  a η=0 vs `ces_b05`) / `panel` (griglia η×c0×`enable_prices`×σ×ρ, 12 seed, **CRN** — a parità di
  seed il probe non cambia RNG, quindi off/on condividono rete e matching) / `report` (σ\*(η),
  mappa di collasso c0=2.0, ρ\*/H1, canale Pigou — **senza simulazione**). **Ipotesi P1–P4 e gate
  congelati nel sorgente PRIMA dei run** (`HYPOTHESES`, `GATE`); BLAS pinnati; ambiente in
  `ces_b21_environment.json` (conteggio seed letto dal panel per non essere sovrascritto da un
  report-only). Il gate esclude il controllo degenere (`enable_prices=False`) dal test di movimento
  (lezione b17: è il riferimento, non un'osservazione)
- `scripts/paper_claims.yaml` + `scripts/verify_paper.py` + `scripts/coherence.py` — **brief 18**,
  toolchain di verifica dei numeri del paper, **committata** (non più tooling di sessione).
  `paper_claims.yaml` è il registro (26 claim, ognuno con lookup eseguibile: artifact, filtro,
  colonna, `decimals`, mappa simbolo→parametro — es. `$\lambda$` = `wealth_effect`).
  `verify_paper.py` controlla paper↔artifact (round-once; `--selftest` su input noto-cattivo);
  `coherence.py` controlla documento↔documento (`--selftest` su input noto-cattivo, b27), con
  `RESULTS.md` untracked → `DOCUMENT UNTRACKED` (check su tracciamento git, non su esistenza — b27).
  `sobol_sigma_ST_viable` resta AMBIGUOUS **per costruzione** (S1 e ST viability leggono entrambi
  0.008 sulla stessa riga di `tab:sobol`)
- `scripts/sweep_rounding.py` — **brief 19**, firma del doppio arrotondamento su tutto il paper,
  **registry-free**; risultato negativo (nessuna discrepanza nuova). Regex `(?<!-)-?\d+\.\d+`
  (brief 20: un `-` dopo `-` è un trattino di range, non un segno). Due punti ciechi dichiarati
  (numeri derivati; tabelle senza sorgente inclusa), esclusione dei dump a >100 righe. Rigenera
  `results/paper_rounding_sweep.csv`
- `scripts/make_tab_sobol.py` — **brief 20**, genera il corpo `tabular` di `tab:sobol` da
  `ces_b13_sobol_indices.csv` (`saltelli`, round-once ROUND_HALF_UP, mappa `$\lambda$`=`wealth_effect`,
  **nessun grassetto** — b27-bis Opzione A: il set `BOLD` e il ramo `\textbf` sono stati rimossi dal
  generatore, così il paper non ha grassetto neppure in tabella); stampa su stdout, il `.tex` contiene il blocco inline col marcatore
  `do not hand-edit` sulla riga `\midrule`. **Prima tabella del paper con generatore committato**
- `scripts/make_tab_prices.py` — **brief 22**, genera il corpo `tabular` di `tab:prices` da
  `ces_b21_sigma_star_eta.csv` (`c0=1.0`, round-once ROUND_HALF_UP); a η=0 **asserisce** l'identità
  off≡on (`P≡1` per costruzione) ed emette una riga sola. Stampa su stdout, blocco inline nel `.tex`
  col marcatore `do not hand-edit` sulla riga `\midrule`. **Seconda tabella del paper con generatore
  committato** (dopo `tab:sobol`)
- `notebooks/01_Endogenous_Investment.ipynb` — sweep ρ a σ=1 (wage-led) + sweep σ
  con sign frontier; figure `retention_sweep.png`, `ces_sign_frontier.png`
- `results/` — output misurati committati. `ces_b21_*.csv` (brief 21: `stage_a_panel`,
  `byte_check`, `sigma_star_eta`, `collapse_c0_2`, `h1_rho_star`, `pigou_c0_1`) +
  `ces_b21_environment.json` + 2 figure → rigenerati da `run_brief21.py` (`--phase report` non
  simula). `ces_b17_*.csv` + `ces_b17_gate.json` +
  `ces_b17_environment.json` + figura `ces_b17_rho_star_lambda.png` (brief 17) → rigenerati da
  `run_brief17.py` (`--phase report` non simula). `ces_b13_*.csv` + `ces_b13_environment.json`
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
  avrebbe fatto fallire — continuità attraverso σ=1 e guardia inerte sulle σ sweepate),
  aspettativa sull'investimento (brief 17: legge di update di u^e — geometrica/congelata a
  target/uguaglianza esatta a λ_u=1 — annidamento λ_u=1 bit-for-bit, l'acceleratore legge u^e e
  non l'utilizzo realizzato, lag di un periodo, floor di `util_effect`, SFC/determinismo
  parametrizzati su λ_u<1, validazione, neutralità a t=0 per ogni λ_u, e reporter fuori da
  `_PANEL_METRICS`), probe sui prezzi (brief 21: **SFC parametrizzata su `enable_prices × η × c0`**
  incl. buffer=0, **input noto come cattivo** che fallisce netto sull'asimmetria di §1.3, annidamento
  byte η=0 `enable_prices=True`≡False, `Price` fuori da `_PANEL_METRICS` e ≡1 da spento, `P=w_t/w_bar`
  quando acceso, salario reale `w/P==w_bar`, e **la FOC dell'impresa al salario reale** `w_t/P`).
  **569 test** (551 invariati + 18 nuovi). *(Brief 11 non aggiunge test: non tocca `src/`.)*
- `performance/engine.cpp` — **STALE**: implementa il modello additivo di Fase 1,
  non il core CES. Non usare per risultati finché non è portato.
- `parameter_notes.md` — note bibliografiche: fonte, stima, range e verdetto di
  ancoraggio per ogni parametro; §"Il sistema congiunto" (α, ρ, δ, K/Y, I/Y).
  **Da estendere a ogni nuova estensione.**
- `METHODOLOGY.md` — questo file. **Da rileggere contro il codice a ogni brief**:
  ha già driftato una volta (§9). **Ha driftato di nuovo:** i brief 22 e 22-bis non
  erano registrati qui — i criteri di accettazione §7 del brief 22 **omettevano il
  record** (che b17, b18–20 e b21 avevano), e questo documento anti-drift è rimasto
  indietro di **due brief** (chiuso dal brief 22-ter, questa voce). **Invariante d'ora
  in poi: ogni brief ha il proprio record in `METHODOLOGY.md` FRA I CRITERI DI
  ACCETTAZIONE.** Il record non è un extra a fine lavoro: è parte del deliverable, alla
  pari del codice e dei detector. Un documento anti-drift che drifta è il caso peggiore.