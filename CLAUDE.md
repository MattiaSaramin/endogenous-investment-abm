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
l'offerta.

**Stella polare (confermata):** l'investimento deve guidare l'output **via
capitale** — l'accumulazione di capitale endogenizza il lato dell'offerta.
Non è "l'investimento cura la disoccupazione da domanda" (tesi diversa, vedi
§3): il canale di offerta deve essere vivo e marginalmente attivo.

Il modello deve essere insieme **teoricamente coerente** (l'investimento guida
davvero l'output) ed **empiricamente fondato** (coerente con benchmark
macroeconomici reali). Framework: **Mesa** (Python), test con `pytest`.

---

## 2. Stato reale del repository (topologia dei branch)

Tre branch, tre significati distinti. Tenerli separati è un invariante.

- **`main`** — **Baseline Fase 1** (additiva-nesting). Economia a bene unico,
  prezzo fisso, stock-flow-consistent. Capacità con capital-deepening
  `Y* = A·L·(1 + γ·(K/L)^α)`; investimento `I = θ·hoard·util_effect` finanziato
  dal risparmio monetario personale del capitalista (stock). Nessun mercato del
  lavoro. README e codice **coincidono**. È la **baseline citabile in tesi**.

- **`labour-market-leontief`** — **Checkpoint del punto 11 della roadmap,
  costruito fuori sequenza.** Produzione **Leontief** `output = A·L` con vincolo
  di capitale sui posti (`max_jobs = K/κ`); mercato del lavoro con
  disoccupazione involontaria; settore pubblico con sussidio a bilancio in
  pareggio. ~818 righe testate (15 test verdi). **Prezioso ma fuori rotta**
  (vedi §3): verrà reinnestato al punto 11 sulla fondazione corretta, non prima.

- **`cobb-douglas-core`** — **Core di offerta: costruito, calibrato, committato.**
  Diverge da `main`. Cobb-Douglas vera + finanziamento interno via utili
  trattenuti (conto d'impresa infra-periodo, nessun sequestro di moneta). 19 test
  verdi. Numeri misurati e cornice di regime in §4 e §7. **Ancora sul branch
  `experiment.py`, notebook, README, figure e C++ engine con l'API vecchia
  (`theta`):** è lo stato "core nuovo, contorno vecchio" da chiudere nel
  **consolidamento** (§8), che è il task attivo ora.

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

## 6. Decisione architetturale corrente: sequenziare il mercato del lavoro

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

## 7. Architettura del core di offerta (IMPLEMENTATA — riferimento al codice su `cobb-douglas-core`)

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

**Fatto:** core Cobb-Douglas + finanziamento interno (§7) — costruito, calibrato,
committato su `cobb-douglas-core` (19 test verdi).

**Prossimo (attivo): consolidamento.** Il core è committato ma `experiment.py`,
notebook, README, figure e `engine.cpp` usano ancora l'API vecchia (`theta`).
Allinearli alla nuova architettura (`retention_ratio`, sweep su ρ), rifare il
confronto baseline-vs-esteso e le figure, e **scrivere nel README la cornice
onesta** (regime di offerta, canale di domanda dormiente, parametri scelti per
regime) per prevenire il prossimo mismatch. Poi: **blocco bibliografico**
(punto 4) per saldare il debito di ancoraggio parametri (§4).

**Successivi:** 8) produttività eterogenea tra imprese; 9) prezzi e markup
endogeni (tocca la calibrazione della quota salari, da ricalibrare con α);
10) aspettative adattive su domanda e investimento; **11) mercato del lavoro
esplicito con disoccupazione** (reinnesto del checkpoint Leontief sulla nuova
fondazione); 12) entrata/uscita/fallimento imprese; 13) cambiamento tecnologico
(crescita di A); 14) banche e credito (estende la matrice SFC: depositi,
prestiti); 15) politica monetaria e fiscale; 16) stesura metodologia e risultati.

**Ricerca bibliografica (continua):** ogni parametro deve avere una fonte o
essere dichiarato come scelta di modellazione. Priorità immediate senza fonte,
tutte nel core corrente: **α (=1/3), `retention_ratio` (=0.40), δ (=0.05),
`c0` (=1.0), `wealth_effect` (=0.08), `investment_floor` (=0.1), `beta` (=0.5),
`target_utilization` (=0.90)**. In particolare `wealth_effect=0.08` è alto vs
MPC-ricchezza empirico ~0.03–0.05. Per il futuro reinnesto del lavoro (punto 11):
κ, `capital_floor`, `benefit_replacement_rate`, `max_tax`, tarati nel branch
Leontief senza ancoraggio.

---

## 9. Vincoli / invarianti — DA RIPORTARE ESPLICITAMENTE IN OGNI BRIEF

Claude Code non conosce la storia del progetto e non vede queste conversazioni.
Ogni brief deve elencare gli invarianti pertinenti come non negoziabili.

- **Stock-flow consistency:** nessuna creazione/distruzione di moneta nel
  settlement. Con il finanziamento a utili trattenuti, la ritenzione **non deve**
  rompere la conservazione (profitti trattenuti = posta monetaria d'impresa, da
  aggiungere alla grandezza conservata).
- **Sequenza del periodo** in `model.py`, esplicita e motivata: domanda → piani
  di investimento → produzione/razionamento → contabilità imprese → settlement
  famiglie → settlement investimenti. Ogni deviazione va dichiarata e giustificata.
- **Determinismo per seed** e **test verdi** dopo ogni modifica.
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

- `src/agents.py` — Firm, Household, Capitalist
- `src/model.py` — MacroModel: sequenza del periodo, settlement, metriche
- `src/experiment.py` — runner Monte-Carlo, bande di confidenza, sweep
- `notebooks/01_Endogenous_Investment.ipynb` — baseline vs esteso + sweep
- `tests/test_model.py`, `tests/conftest.py` — SFC, determinismo, risultato headline
- `performance/engine.cpp` — aggregato di confronto (approssimazione, non port)
