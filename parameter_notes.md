# Note bibliografiche — ancoraggio dei parametri (core CES normalizzato)

> Roadmap punto 4. Per ogni parametro: valore nel modello, stima empirica e
> range, fonte, come entra nel modello, e verdetto di ancoraggio. Da mantenere e
> estendere a ogni nuova estensione. Primo blocco: 2026-07.
>
> **Regola:** un valore è "ancorato" solo con fonte citabile. Dove il valore è
> una scelta di modellazione o di regime, va dichiarato tale — non spacciato per
> stima empirica. Diversi parametri di questo core sono scelte, non stime.
>
> **⚠️ Allineamento al codice (brief 05 §7, 2026-07-17).** Questo file dichiarava
> `c0 = 1.0` e `wealth_effect = 0.08` mentre il codice girava `c0 = 2.0` e
> `wealth_effect = 0.05`. Non erano "note stale ereditate": erano note
> bibliografiche che descrivevano **un modello diverso da quello che produce i
> numeri**. È lo stesso disallineamento README/codice che il progetto ha già
> pagato una volta (la spec "Fase 2" fantasma), solo spostato in un altro file.
> Corretto qui. **I valori qui sotto sono ora quelli dei default di `MacroModel`;
> verificarlo contro il codice a ogni brief, non fidarsi di questa riga.**

## Sintesi (tiers di ancoraggio)

| Parametro | Valore modello | Ancoraggio | Nota |
|---|---|---|---|
| `sigma` (σ) | **sweep**, default 1.0 | **Buono — e rigetta il default** | 0.40–0.60 (Chirinko 2008); ~0.40 (Chirinko & Mallick 2017); 0.45–0.87 meta-regressione che **rigetta Cobb-Douglas** (Knoblach et al. 2020); Fed SIGMA 0.5. Puzzle σ>1: Karabarbounis & Neiman (2014). **Da sweepare, non scegliere.** |
| `pi0` (π0) | 1/3 | **Buono** | = il vecchio `alpha` rinominato: unica nozione di quota del capitale nel codice |
| `K0`, `L0` | 41.87, 7.395 (per impresa) | **Scelta di modellazione** | ancora di normalizzazione CES; misurata una volta a σ=1, ρ=0.40, poi congelata |
| `K0`, `L0` @ρ=0.50 | 52.566, 6.320 (per impresa) | **Scelta di modellazione — ancora alternativa** | brief 05 §4: misurata a σ=1, **ρ=0.50**, seed {0,1,2}, 2000 step, `c0`=2.0, altri default; congelata in `model.ANCHOR_*_RHO050`. Serve **solo** al test di sensibilità all'ancora (Temple 2012), non è il default |
| `Y0` | derivato | **Non libero** | `A·K0^π0·L0^(1−π0)`, calcolato — mai misurato |
| `alpha` | 1/3 | **Buono** | standard growth accounting; ma quota del capitale in aumento nel XXI sec. → ora `pi0` |
| `markup` | ~~0.5 (derivato)~~ | **RIMOSSO al punto 11** | sostituito dal salario fisso `w̄`; sezione sotto marcata STALE |
| `delta` | 0.05 | **Buono (congiunto)** | implicato da K/Y e I/Y; non ancorabile in isolamento |
| `retention_ratio` | 0.40 | **Buono (via I/Y)** | ρ fissa il tasso di investimento, non è un payout |
| `wealth_effect` (λ) | **0.05** | **BUONO — ancorato** | Slacalek (2009): ≈5 cent, media su 16 paesi. Corretto da 0.08 (fuori range) → 0.05 centra la media cross-country |
| `c0` | **2.0** | **NON ancorabile — e attivamente sospetto** | cerotto compensativo; la sua giustificazione originaria è **falsificata** (vedi voce) |
| `c1` | ~0.9 | **Struttura sì, livello no** | forma da Teglio; MPC lavoratori |
| `w_bar` (salario / punto di normalizzazione) | 0.9 | **Declassato a normalizzazione (brief 07)** | non più il parametro distributivo libero: è il salario a `U = U_REF` e il livello a ogni `U` quando `eta=0`. Il parametro con contenuto empirico ora è `eta` |
| `eta` (η, elasticità wage curve) | **sweep**, default 0.0 | **Buono — ancorato (Blanchflower–Oswald)** | ≈0.10 (Blanchflower & Oswald 1994); ≈0.07 meta-analisi (Nijkamp & Poot 2005); range sweep 0–0.15. `eta=0` = modello fisso annidato |
| `U_REF` | 0.2604666667 | **Scelta di modellazione — misurata** | punto di normalizzazione della wage curve; misurato una volta (σ=1, ρ=0.40, seed {0,1,2}, tail-50), congelato in `model.U_REF`. **NON è una stima del NAIRU** |
| `U_min` | 1/N = 0.01 | **Convenzione dichiarata** | sotto la risoluzione della forza lavoro U non è osservabile; guardia contro w→∞ a U=0 |
| `w_min` (wage_floor) | 0.45 = 0.5·w̄ | **Target di design — non ancorabile** | floor di sussistenza contro la spirale deflattiva a η alto; le celle dove morde stabilmente sono mappate |
| `N` (forza lavoro) | 100 | **Scelta di modellazione** | scala del modello |
| `beta` (acceleratore) | 0.5 | **Debole** | esiste letteratura sull'acceleratore, ma nessun numero canonico |
| `investment_floor` | 0.1 | **Scelta di modellazione** | guardrail, nessun referente empirico |
| `initial_capital` | 40.0 | **Scelta di modellazione — NON toccare negli sweep** | seleziona il bacino: equilibri multipli e soglia di viability |
| `target_utilization` | 0.90 | **Debole — sopra l'empirico** | utilizzo reale ~0.80 |
| `expectation_gain` (λ_e) | **sweep**, default 1.0 | **Debole — sweep, non stima** | gain delle aspettative adattive sulla domanda (brief 08); nessuna stima puntuale affidabile per un ABM (aspettative adattive, Nerlove 1958; constant-gain learning, Evans & Honkapohja 2001). `λ_e=1` = aspettative statiche annidate bit-for-bit. **Esito misurato: σ\* e regione di collasso λ_e-invarianti entro CI/rumore** |
| `benefit_replacement_rate` (rr) | **sweep**, default 0.0 | **Buono — ancorabile (OECD)** | sussidio di disoccupazione = frazione del salario corrente `w_t`, finanziato da flat tax a bilancio in pareggio (brief 09, punto 15). NRR netto OECD ~58% iniziale, 50–80% low earner; gross RR più bassi ~0.2–0.6. Sweep rr∈{0, 0.25, 0.5, 0.75} bracket-a la banda 0.4–0.6. `rr=0` annida il modello senza governo bit-for-bit. **Esito: crowding-in dove demand-constrained; NON stabilizza il collasso c0=2.0** |
| `max_tax` | 0.6 | **Convenzione dichiarata — non stima** | cap sull'aliquota di bilancio in pareggio; se il sussidio desiderato richiede di più, si scala giù (budget resta in pareggio). Guardrail, non stima. `Tax_Rate` realizzato e `frac_periods_at_cap` sono **esiti misurati** |

Benchmark di validazione (non parametri, ma target): quota salari, K/Y, quota
profitti, I/Y, utilizzo — vedi sotto.

---

## Parametri

### `alpha` = 1/3 — quota del capitale / elasticità del capitale
- **Ruolo:** esponente del capitale in `Y* = A·K^α·L^(1−α)`; determina anche le
  quote fattoriali (via il vincolo sul markup) e la relazione `K/Y = ρα/δ`.
- **Empirico:** ~1/3 è lo standard; range comune 0.25–0.40. Solow (1957) usò 0.35
  per gli USA. La quota della "compensation of employees" USA sta tra ~0.61 e
  0.68 (1960–2017), cioè quota del capitale ~0.32–0.39.
- **Fonti:** Gollin (2002), "Getting Income Shares Right"; Crafts (2021),
  *J. Economic Surveys* (growth accounting, α≈1/3 come buona approssimazione,
  cita Aiyar & Dalgaard 2005); Cottrell (2019), lecture notes Wake Forest
  (compensation share 0.61–0.68).
- **Caveat importante:** la quota del capitale è **cresciuta** nel XXI secolo
  (Karabarbounis & Neiman 2014, "The Global Decline of the Labor Share"); e la
  specificazione Cobb-Douglas a quote costanti è **empiricamente contestata**
  (Antràs 2004; Duffy & Papageorgiou 2000 rigettano Cobb-Douglas). α=1/3 è un
  benchmark difendibile, ma l'assunzione di quote costanti è una semplificazione,
  non un fatto.
- **Verdetto:** ben ancorato come valore standard; dichiarare l'assunzione di
  quote costanti come scelta.

### `sigma` (σ) = sweep, default 1.0 — elasticità di sostituzione K/L
> Introdotto dal brief 04 (branch `ces-production`). **È il parametro che determina
> il segno del risultato headline del progetto**, non un dettaglio tecnico.

- **Ruolo:** produzione **CES normalizzata**
  `Y* = Y0·[π0·(K/K0)^r + (1−π0)·(L/L0)^r]^(1/r)`, con `r = (σ−1)/σ`. Nidifica la
  Cobb-Douglas (σ=1, il core attuale) e la Leontief (σ→0). σ regola la forza della
  sostituzione capitale-lavoro, cioè **il meccanismo stesso** del risultato wage-led:
  più capitale ⇒ meno lavoratori per la stessa domanda ⇒ disoccupazione tecnologica.
- **Empirico:** la letteratura **rigetta esplicitamente σ = 1**.
  - Chirinko (2008), *J. Macroeconomics* 30(2): il peso dell'evidenza colloca σ tra
    **0.40 e 0.60**.
  - Chirinko & Mallick (2017), *AEJ: Macroeconomics* 9(4): stima **≈ 0.40**.
  - Knoblach, Roessler & Zwerschke (2020), *Oxford Bulletin of Economics and
    Statistics* 82(1): meta-regressione su **2.419 stime da 77 studi** → **0.45–0.87**,
    e **rigetta l'ipotesi Cobb-Douglas**.
  - Il modello **SIGMA** della Federal Reserve usa **0.5**.
  - **In controtendenza:** Karabarbounis & Neiman (2014), *QJE* 129(1), e Piketty &
    Zucman stimano **σ > 1**.
- **Il puzzle, dichiarato non nascosto:** la micro-letteratura converge sotto
  l'unità; la macro-letteratura sul declino della quota salari richiede σ>1. È una
  ragione **in più** per fare lo sweep invece di scegliere un valore.
- **Verdetto:** σ=0.5 è il valore centrale difendibile, ed è **più vicino a Leontief
  (σ=0) che alla Cobb-Douglas (σ=1)**: l'headline del branch `labour-market` poggia
  sull'estremo che i dati rigettano. Ma σ resta **uno sweep**, non un punto: il range
  plausibile (≈0.3–1.3, incluso il puzzle σ>1) copre entrambi i segni possibili.
  **Il default resta 1.0** perché deve riprodurre esattamente il branch precedente
  (criterio di identità), non perché 1.0 sia difendibile.

### `pi0` (π0) = 1/3 — quota del capitale nel punto base
- **Ruolo:** sostituisce `alpha` come **unica** nozione di quota del capitale nel
  codice. Con σ=1 è esattamente l'esponente Cobb-Douglas del capitale; per ogni σ è
  la quota del capitale **nel punto base** (proprietà della normalizzazione).
- **Ancoraggio:** identico ad `alpha` sopra (non è un parametro nuovo, è lo stesso
  rinominato). `Y0` è **derivato** (`A·K0^π0·L0^(1−π0)`), non un parametro libero.

### `K0`, `L0` = 41.87, 7.395 (per impresa) — ancora di normalizzazione
- **Ruolo:** punto base della CES normalizzata. **Scelta di modellazione, non una
  stima** — nessun referente empirico, e non ne serve uno.
- **Perché serve:** la CES "da manuale" non è sweepabile. Variando `r` a `(A, a)`
  fissi si muovono anche le quote fattoriali implicite e l'efficienza, quindi `A` e
  `a` **non sono confrontabili tra σ diversi** e il cambio di comportamento è
  **inattribuibile**. La normalizzazione fissa un punto base per cui passano tutte le
  varianti di σ con le stesse quote: solo così due economie differiscono *solo* per σ.
  Fonti: **Klump & de La Grandville (2000)**, *AER* 90(1) (introduce la
  normalizzazione); **Klump & Saam (2008)**, *Economics Letters* 98(3) (calibrazione
  nei modelli dinamici; senza normalizzazione il confronto tra σ è "arbitrario e
  inconsistente"); **Klump, McAdam & Willman (2012)**, *J. Economic Surveys* 26(5)
  (rassegna).
- **Caveat da riportare, non da nascondere:** **Temple (2012)**, *J. Macroeconomics*
  34(2), critica l'idea che la normalizzazione isoli gli effetti "puri" di σ e che σ
  sia un parametro profondo. Qui la normalizzazione è dichiarata per quello che è —
  un **dispositivo di confronto** che rende commensurabili le varianti di σ in un
  punto base — **non** una garanzia di causalità.
- **Come è stata ottenuta:** **misurata una volta** sullo steady state del branch
  `labour-market` (σ=1) a `ρ=0.40`, seed {0,1,2}, 2000 step, media delle ultime 50
  osservazioni, tutti gli altri parametri ai default (`initial_capital=40`,
  `wage_rate=0.9`, `c0=2.0`, N=100, 10 imprese). Aggregati misurati:
  K = 418.7356984217038, L = 73.95333333333333 su 10 imprese. Poi **congelata** in
  `model.ANCHOR_K0` / `model.ANCHOR_L0`: **la stessa per tutta la griglia** (σ, ρ),
  altrimenti la normalizzazione non normalizza niente.
- **Nota:** a σ=1 l'ancora è **irrilevante** (l'identità con la CD vale per qualunque
  `(K0, L0)` purché `Y0` sia calcolato); conta solo per σ≠1, e centra l'esperimento
  sulla regione di interesse. Per rendimenti di scala costanti la CES normalizzata è
  omogenea di grado 1: ancora per-impresa e ancora aggregata danno la stessa funzione.
- **Verdetto:** scelta di modellazione, dichiarata. Da riportare come tale.

### `markup` = 0.5 — derivato da α
> ⚠️ **STALE**: il parametro `markup` è stato **rimosso** dal codice al punto 11
> (branch `labour-market`), dove il salario fisso `w̄` è diventato il parametro
> distributivo e il profitto il residuo. Questa sezione descrive il core
> Cobb-Douglas *precedente*. Non risolto qui: fuori dallo scope del brief 04.
- **Ruolo:** fissa i prezzi e quindi la quota salari (`1/(1+markup)`). Vincolato:
  `markup = α/(1−α)` ⇒ quota salari = 1−α.
- **Empirico:** i markup medi misurati sono ben più alti (De Loecker, Eeckhout &
  Unger 2020 stimano markup in forte crescita, ~1.2–1.6 sul costo marginale), ma
  **non è ciò che questo parametro rappresenta qui**: nel modello il markup è uno
  strumento di coerenza distributiva, non un markup di mercato osservato.
- **Verdetto:** per costruzione, non da ancorare a markup empirici. Da
  ri-discutere solo quando (roadmap punto 9) il markup diventerà endogeno — a
  quel punto si scollega dalla quota salari e va ricalibrato con dati sui markup.

### `delta` = 0.05 — tasso di deprezzamento
- **Ruolo:** legge del moto del capitale `K(t+1) = (1−δ)K(t) + I`; entra in
  `K/Y = ρα/δ`.
- **Empirico:** il deprezzamento aggregato dipende dal mix di asset. BEA/BLS
  stimano i tassi per asset (Hulten–Wykoff come base) via perpetual inventory
  method; equipaggiamento deprezza più veloce delle strutture. Calibrazioni macro
  tipiche: 0.04–0.10 annuo. Manuali (es. problema Mankiw) usano ~0.04; Angeletos
  (2007) usa 0.08; RBC spesso ~0.10 annuo (0.025 trimestrale).
- **Fonti:** BEA, *Fixed Assets* e "BEA Depreciation Rates"; BLS (2022),
  "Alternative Capital Asset Depreciation Rates"; Angeletos (2007).
- **Verdetto: BUONO — e non è ancorabile in isolamento** (vedi §"Il sistema
  congiunto"). δ non è un parametro libero: dati i target `K/Y ≈ 2.6` e
  `I/Y ≈ 0.13`, l'identità di steady state `I = δK` impone
  `δ = (I/Y)/(K/Y) ≈ 0.05`. Il valore attuale è **esattamente** quello che rende
  i due benchmark reciprocamente coerenti in assenza di crescita di trend (il
  modello non ne ha). Confronto: Mankiw usa δ≈0.04 con K/Y≈2.5; Angeletos (2007)
  usa 0.08 (ma con altri target). **Non alzare δ "verso il centro della fascia
  di letteratura": sfonderebbe il target di I/Y.** Nota: se il "periodo" del
  modello non è un anno, l'interpretazione di δ (e di K/Y, I/Y) cambia —
  chiarire l'unità temporale.

### `retention_ratio` (ρ) = 0.40 — quota di profitto trattenuta/investita
- **Ruolo:** finanziamento interno; `I = clip(ρ·profit·util_effect, floor,
  profit)`; è il parametro headline dello sweep; determina `K/Y = ρα/δ`.
- **ATTENZIONE — errore di categoria da evitare.** ρ nel modello **non è una
  decisione di payout**: è il parametro che fissa il **tasso di investimento**
  (`I/Y = ρα`). Il modello non ha imposte né credito esterno, quindi l'impresa
  deve finanziare *tutto* l'investimento dalla ritenzione. Ancorare ρ al plowback
  ratio della corporate finance è quindi improprio: **va ancorato a I/Y**.
  (Cambierà al punto 14: col credito, ritenzione e investimento si scollegano e
  ρ tornerà a essere una vera decisione di payout, da ancorare ai dati di payout.)
- **Ancoraggio corretto (via I/Y):** con α=1/3, ρ=0.40 ⇒ `I/Y = 0.133`, contro un
  investimento fisso non residenziale/PIL USA di ~0.13–0.14. **Match buono.**
- **Dati aggregati sul payout (per riferimento, non per ancorare ρ qui):** in
  NIPA i profitti al lordo delle imposte (PBT) si scompongono in imposte +
  dividendi netti + **profitti non distribuiti** (= risparmio d'impresa, che
  finanzia gli investimenti di lungo periodo). L'analogo aggregato di un
  "retention ratio" sarebbe `undistributed profits / PBT`, che è **più basso** del
  plowback d'impresa (~0.4–0.6) perché le imposte prelevano una quota e i
  dividendi sono grandi. Indicazione di ordine: nella crescita dei profitti delle
  industrie non finanziarie domestiche post-COVID, ~76% è andato a dividendi, ~15%
  a profitti non distribuiti, ~9% a imposte (scomposizione della *crescita*, non
  dei livelli). I buyback complicano ulteriormente il quadro.
- **Fonti:** BEA, *NIPA Handbook* cap. 13 "Corporate Profits" (struttura
  PBT = imposte + dividendi + undistributed); BEA, "Corporate Profits"; St. Louis
  Fed (2025), "What's Driving the Surge in U.S. Corporate Profits?"; serie FRED
  rilevanti (CP, NFCPATAX). Corporate finance (plowback 0.4–0.6): Corporate
  Finance Institute; Wall Street Prep.
- **Verdetto:** 0.40 è **ben ancorato via I/Y**. Il fatto che coincida anche con
  la fascia bassa del plowback d'impresa è secondario e non va usato come
  giustificazione principale.

### `c0` = 2.0 — consumo autonomo
> ⚠️ **Il codice gira `c0 = 2.0`.** Questo file diceva 1.0 fino al brief 05 (§7).

- **Ruolo:** funzione di consumo `C = c0 + c1·income + λ·wealth`, poi troncata a
  ciò che la famiglia può permettersi (`min(target, wealth + income)`).
- **Perché è **attivamente sospetto**, non solo "non ancorato":**
  1. È un **cerotto compensativo**: introdotto per portare domanda nel regime
     desiderato, non stimato. La regola trasversale del progetto è che un
     parametro introdotto per aggirare un meccanismo va **rimosso quando il
     meccanismo è capito**, non ereditato.
  2. **La sua giustificazione originaria è falsificata.** Si giustificava `c0=2.0`
     col fatto che crea il vincolo di cassa da cui nasce il differenziale di MPC
     fra lavoratori e capitalisti. Ma i lavoratori risultano cash-constrained
     **al 100% anche a `c0 = 1.0`**: la causa è la condizione **`c0 ≥ w̄`**
     (con `w̄ = 0.9`), non il valore 2.0. Il livello 2.0 non fa il lavoro che gli
     si attribuiva.
- **Empirico/struttura:** la forma `c0 + c1·Y` viene direttamente da Teglio
  (2025): consumo = componente costante + componente proporzionale al reddito. Il
  termine `λ·wealth` è l'estensione di questo progetto. La **forma** è ancorata;
  il **livello** di `c0` non lo è e non è ancorabile: è una scala del modello.
- **Fonti:** Teglio (2025) per la struttura c0+c1Y. **Nessuna fonte per il livello,
  e non se ne cerchi una: non è una quantità stimabile in questo modello.**
- **Verdetto:** **NON ancorabile.** Da dichiarare come cerotto compensativo con
  giustificazione falsificata. **Esito misurato (brief 05 §2): vedi la sezione
  "c0 — esito dello stress test" più sotto**, che riporta quanto del risultato
  headline dipende da questo valore.

### `wealth_effect` (λ) = 0.05 — MPC sulla ricchezza
> ✅ **Corretto da 0.08 a 0.05 e ora ANCORATO.** Il codice gira 0.05; questo file
> diceva 0.08 fino al brief 05 (§7). La correzione va nella direzione giusta e va
> registrata come tale: 0.08 era **fuori** dal range centrale empirico.

- **Ruolo:** termine `λ·wealth` nel consumo; leva di domanda.
- **Empirico:** consenso robusto su **0.03–0.05** (3–5 cent per dollaro di
  ricchezza), range complessivo 0.02–0.07. **Slacalek (2009)** — la fonte
  verificata per questo valore — stima l'MPC di lungo periodo sulla ricchezza
  **totale** a ≈ **5 cent** in media su **16 paesi**; **4–6 cent** nelle economie
  market-based; le stime per singolo paese stanno tipicamente fra **0 e 10 cent**.
  Il valore **0.05 centra la media cross-country**. Case, Quigley & Shiller (2005):
  3–4 cent (housing). Carroll, Otsuka & Slacalek (2011): immediato ~0.01–0.02,
  eventuale ~0.09 (housing). Fed FEDS note (2025): ~3.5 cent, in calo a ~2.7 cent.
  Effetto housing > finanziario.
- **Fonti:** **Slacalek, J. (2009), "What Drives Personal Consumption? The Role of
  Housing and Financial Wealth", *The B.E. Journal of Macroeconomics* 9(1)** (anche
  ECB Working Paper 1117) — fonte verificata per λ = 0.05; Case–Quigley–Shiller
  (2005); Carroll–Otsuka–Slacalek (2011); Federal Reserve FEDS note (2025);
  Paiella (2009) per la rassegna.
- **Verdetto:** **BUONO — ancorato.** λ = 0.05 è la media cross-country di
  Slacalek (2009) e sta dentro il range centrale del consenso. Non è più una leva
  di regime dichiarata: è una stima con fonte. (Il vecchio 0.08 era ~2× la stima
  centrale e sopra il tetto empirico.)

### `beta` = 0.5 — sensibilità dell'acceleratore all'utilizzo
- **Ruolo:** `util_effect = max(0, 1 + β·(u_last − target))`; modula
  l'investimento rispetto allo scostamento dell'utilizzo dal target.
- **Empirico:** esiste una lunga letteratura sull'acceleratore e sul
  "flexible accelerator" (Clark 1917; Chenery 1952; Koyck 1954) e su modelli di
  investimento (Jorgenson) e q di Tobin, ma **non c'è un valore canonico** per
  questa specifica elasticità in questa parametrizzazione.
- **Verdetto:** scelta di modellazione ragionevole; nessun ancoraggio numerico
  puntuale. Da esplorare in sensitivity analysis (roadmap punto 5) più che da
  "ancorare" a un singolo numero.

### `investment_floor` = 0.1 — capex minimo
- **Ruolo:** guardrail anti-collasso (con capitale essenziale, I=0 ⇒ K→0 ⇒ Y*→0).
- **Empirico:** nessun referente empirico diretto — è un espediente numerico.
- **Verdetto:** **scelta di modellazione** dichiarata; da testare in sensitivity
  (quanto il baseline a basso capitale dipende da questo valore).

### `target_utilization` = 0.90 — utilizzo di riferimento dell'acceleratore
- **Ruolo:** punto neutro dell'acceleratore; a `u = target`, `util_effect = 1`.
- **Empirico:** l'utilizzo medio USA (Fed) è ~80% (media dal 1967 ~81.6%; media
  1972–2025 ~79–80%); soglia inflazionistica ~82–85%. Quindi 0.90 è **sopra**
  l'utilizzo tipico osservato.
- **Fonti:** Federal Reserve G.17 (Industrial Production and Capacity
  Utilization); voce "Capacity utilization" (media storica ~81.6%).
- **Verdetto:** scelta di regime, sopra l'empirico. Coerente col fatto che il
  core opera a quasi-piena-capacità (vedi benchmark utilizzo).

---

## Blocco salariale — wage curve (brief 07, roadmap punto 9)

> Introdotto dal brief 07. Endogenizza il **livello** del salario con una wage curve
> di Blanchflower–Oswald; il blocco prezzi (numerario = 1) resta fuori scope
> (punto 9-bis). `eta=0` annida il modello a salario fisso bit-for-bit.

### `eta` (η) = sweep, default 0.0 — elasticità della wage curve
- **Ruolo:** salario del periodo, fissato prima del mercato del lavoro sulla
  disoccupazione osservata del periodo precedente:
  `w_t = max(w_min, w_bar·(max(U_{t-1}, U_min)/U_REF)^(-η))`. È il parametro **nuovo
  con contenuto empirico** del brief 07.
- **Perché wage curve e non Phillips:** la Phillips (`Δw = f(U)`) determina la
  *variazione* del salario ⇒ senza inflazione di trend produce deriva perpetua per
  ogni `U ≠ U*`, incompatibile con la statica comparata su steady state. La wage curve
  determina il *livello* e ha steady state ben definito per ogni U.
- **Empirico:** **Blanchflower & Oswald (1994)**, *The Wage Curve* (MIT Press):
  elasticità del salario rispetto alla disoccupazione locale ≈ **−0.10**, notevolmente
  stabile fra paesi. **Nijkamp & Poot (2005)**, meta-analisi su 208 stime da 17 paesi:
  elasticità "corretta" ≈ **−0.07**. Range sweep: **0–0.15**, che copre entrambi i
  valori empirici e uno stress mite.
- **Verdetto: BUONO — ancorato.** η ha una fonte citabile e un valore centrale
  (0.07–0.10). Resta uno **sweep**, non un punto: il default 0.0 esiste solo per
  annidare il modello precedente (criterio di identità), non perché sia difendibile.

### `w_bar` (w̄) = 0.9 — punto di normalizzazione (ex salario fisso)
- **Declassamento (brief 07):** con la wage curve, `w_bar` **cessa di essere il
  parametro distributivo libero** e diventa (con `U_REF`) il punto di normalizzazione:
  è il salario a `U = U_REF`, e il livello del salario a ogni U quando `eta=0`.
- **Empirico:** nessuna fonte diretta per il livello (è una scala distributiva del
  modello, come lo era prima); il contenuto empirico si sposta su `eta`.
- **Verdetto:** scelta di modellazione dichiarata; non è il grado di libertà
  distributivo — quello è ora `eta` (livello relativo del salario) via la curva.

### `U_REF` = 0.2604666667 — disoccupazione di normalizzazione
- **Ruolo:** denominatore della wage curve; a `U = U_REF` il salario è `w_bar`.
- **Come è stato ottenuto:** **misurato una volta** sul modello **attuale**
  (pre-wage-curve), stessa disciplina degli `ANCHOR_*`: `retention_ratio=0.40`, σ=1,
  seed {0,1,2}, 2000 step, media delle **ultime 50** osservazioni di
  `Unemployment_Rate` (convenzione `df.tail(50)`, quella che riproduce
  `ANCHOR_L0·10 = 73.95333333` esatto), altri parametri ai default (`c0=2.0`,
  `wage_rate=0.9`, `initial_capital=40`, N=100, 10 imprese). Medie per seed:
  0.2570, 0.2680, 0.2564; media = 0.2604666667. Congelato in `model.U_REF`, **uguale
  per ogni η**.
- **Perché misurato e non scelto:** se `U_REF` fosse arbitrario, il livello salariale
  di steady state sarebbe un grado di libertà nascosto della calibrazione. Ancorandolo
  allo scenario degli `ANCHOR_*`, a η=0 il modello con wage curve passa per lo stesso
  punto del modello attuale.
- **Verdetto:** **scelta di modellazione, misurata.** NON è una stima del NAIRU: è solo
  il punto di normalizzazione della curva sul salario pre-modifica.

### `U_min` = 1/N = 0.01 — soglia di osservabilità di U
- **Ruolo:** `max(U_{t-1}, U_min)` nella wage curve; sotto la risoluzione della forza
  lavoro (1 lavoratore su 100) la disoccupazione non è osservabile, e il guard evita
  `w → ∞` a piena occupazione (transiente iniziale a t=0 con U=0).
- **Verdetto:** **convenzione dichiarata**, non una stima.

### `w_min` (wage_floor) = 0.45 = 0.5·w̄ — floor di sussistenza
- **Ruolo:** `max(w_min, …)` nella wage curve; guardrail contro la spirale deflattiva
  a η alto.
- **Empirico:** nessun referente empirico diretto — è un target di design.
- **Verdetto:** **target di design, non ancorabile.** Le celle in cui il floor morde
  stabilmente vanno **mappate e riportate** (come le celle collassate del brief 05),
  non nascoste — vedi `results/ces_b07_support_map.csv`.

---

## Blocco aspettative — aspettative adattive (brief 08, roadmap punto 10)

> Introdotto dal brief 08. Generalizza l'aspettativa di domanda dell'impresa da
> **statica** (`Ye_t = D_{t-1}`) ad **adattiva** con gain `λ_e` (codice:
> `expectation_gain`). `λ_e=1` annida il modello statico **bit-for-bit** (branch
> esplicito; i 4 byte-check λ_e=1 vs `ces_b05`/`ces_b07` danno dev = 0.0). Nessuna
> aspettativa su salari, prezzi o investimento (fuori scope: l'acceleratore usa
> `utilization_last_period`, un segnale realizzato, non un'aspettativa).

### `expectation_gain` (λ_e) = sweep, default 1.0 — gain delle aspettative adattive
- **Ruolo:** aggiornamento a parziale aggiustamento dell'aspettativa di domanda,
  `Ye_t = Ye_{t-1} + λ_e·(D_{t-1} − Ye_{t-1})`, letta da `plan_employment` via
  `ces_labour_for_demand`. `λ_e=1` ⇒ `Ye_t = D_{t-1}` (statiche, default e branch
  esplicito per l'identità bit-for-bit); `λ_e<1` smorza la reazione all'ultima
  osservazione; `λ_e=0` congela (degenere, ammesso solo nei test unitari, escluso
  dagli sweep). Vincolo del costruttore: `0 ≤ λ_e ≤ 1`.
- **Perché sweep e non scelta:** in steady state `Ye = D` per qualunque gain, quindi
  i livelli di steady state sono attesi **λ_e-invarianti**; il gain conta solo sul
  transiente e sull'eventuale **selezione del bacino**. **Non esiste una stima
  empirica puntuale affidabile** di un gain di aspettative per un ABM di questo tipo:
  la letteratura di riferimento dà la *forma*, non un livello.
  - **Nerlove (1958)**, aspettative adattive: introduce l'aggiornamento a parziale
    aggiustamento `Ye_t = Ye_{t-1} + γ·(D_{t-1} − Ye_{t-1})`; il "coefficient of
    expectation" γ è stimato ad hoc per serie/mercato, **non** è una costante
    universale.
  - **Evans & Honkapohja (2001)**, *Learning and Expectations in Macroeconomics*:
    il **constant-gain learning** è il caso adattivo con gain costante `λ_e`. Nella
    letteratura di apprendimento adattivo i gain costanti usati sono tipicamente
    piccoli, ma sono **scelte di robustezza dell'analisi**, non stime strutturali, e
    riferite a stime econometriche degli *agenti*, non a un'aspettativa di domanda
    d'impresa. Nessun mapping diretto a un valore per questo modello.
- **Esito misurato (brief 08, 20 seed, 2000 step, `results/ces_b08_*`):**
  - **E1 (c0=1.0) — invarianza dell'headline.** σ\*(η; λ_e) sul supporto comune
    across-config (tutti e 7 i ρ) è **λ_e-invariante entro CI**. Su Y: a η=0,
    σ\* = 0.654 [0.616, 0.691] (λ_e=1), 0.686 [0.637, 0.721] (0.5),
    0.674 [0.639, 0.709] (0.25) — CI ampiamente sovrapposte; a η=0.10,
    0.725 [0.697, 0.745] / 0.713 [0.667, 0.752] / 0.721 [0.684, 0.754]. L'empirico σ
    0.40–0.60 resta **sotto** σ\* per ogni λ_e (P(σ\*>0.60) ≈ 1): il wage-led — e la
    sua crescita in η (brief 07) — è **robusto al gain**. Nessun finding di selezione
    del bacino.
  - **E2 (c0=2.0) — ipotesi di stabilizzazione.** La regione di collasso è
    **λ_e-invariante entro il rumore di griglia/seed** (celle con qualche collasso:
    η=0.10 → 16/15/14 a λ_e=1/0.5/0.25, ma celle a collasso pieno piatte a 6;
    η=0.15 non monotono: 16/15/17). La cella di riferimento (σ=1.5, ρ=0.40, η=0.10)
    **collassa a `K=0`, `U=1` a ogni λ_e**. L'ipotesi ("aspettative più lente
    restringono il collasso") è **NON confermata**: il collasso c0=2.0 è guidato dal
    canale salario→U→erosione di capitale (wage curve, meccanismo brief 07), che
    `λ_e` non tocca. Smorzare l'aspettativa di **domanda** non stabilizza
    un'instabilità che non nasce dalla domanda.
- **Verdetto:** **sweep, non stima.** `λ_e=1` (statiche) è il default per l'identità
  col modello precedente, non perché difendibile. Il risultato headline del progetto
  (σ\*, wage-led) è **robusto a λ_e**: brief 08 è un rafforzamento della robustezza,
  non una nuova leva di regime. Verifica λ_e-invarianza contro `ces_b08_sigma_star.csv`
  e la mappa `ces_b08_collapse_map.csv`.

---

## Blocco governo — sussidio a bilancio in pareggio (brief 09, roadmap punto 15)

> Introdotto dal brief 09. Reinnesta il **sussidio di disoccupazione a bilancio in
> pareggio** dal ramo `labour-market-leontief` sul core attuale (CES + mercato del
> lavoro + wage curve + aspettative adattive). Un solo parametro economico nuovo
> (`benefit_replacement_rate`). `rr=0` (default) annida il modello senza governo
> **bit-for-bit** (byte-check rr=0 vs `ces_b05`/`ces_b07`: dev = 0.0 su 4/4 config).
> Fuori scope: spesa in beni/servizi, occupazione pubblica, debito, tassazione
> progressiva, salario di riserva (i disoccupati accettano sempre).

### `benefit_replacement_rate` (rr) = sweep, default 0.0 — replacement rate del sussidio
- **Ruolo:** step di bilancio in pareggio dopo il settlement investimenti e prima del
  settlement famiglie (step 8). Su tutte le famiglie:
  `base = Σ max(0, next_income)`; `desired = rr·w_t·n_disoccupati`;
  `τ = min(max_tax, desired/base)`; `sussidio = τ·base / n_disoccupati`. La tassa
  colpisce **solo la parte positiva** di `next_income` (un dividendo residuo di
  capitalista può essere negativo — misurato fino a −0.007 a σ=1.5/c0=2.0/η=0.10),
  così `Σ prelievi = τ·base = Σ sussidi` **esattamente** (scalare tutto `next_income`
  per `(1−τ)` rimborserebbe i redditi negativi e romperebbe SFC). Sussidio indicizzato
  al salario **corrente** `w_t` (wage curve), non a `w̄`.
- **Empirico — ancorabile (OECD):** il *net replacement rate* (NRR) OECD misura la
  quota di reddito netto da lavoro mantenuta durante la disoccupazione. Media OECD
  **≈58%** nella fase **iniziale** (single, no figli, salario medio), che scende a
  **~37%** per i disoccupati di lungo periodo; per un single low earner la NRR
  iniziale sta fra **50% e 80%**. I *gross* replacement rate sono più bassi
  (~0.2–0.6 a seconda del paese). **Distinzione da dichiarare:** il parametro del
  modello indicizza il sussidio al salario **lordo** corrente (`sussidio = rr·w_t`),
  quindi è un concetto di replacement rate **gross**, mentre la NRR OECD del 58% è
  netta (al netto delle imposte su sussidio e reddito da lavoro). Lo sweep
  rr∈{0, 0.25, 0.5, 0.75} **bracket-a** la banda gross/net-informata 0.4–0.6 (0.5
  dentro; 0.25 e 0.75 la racchiudono). **Sweep, non punto.**
- **Fonti:** OECD (2024), *Society at a Glance 2024*, cap. "Unemployment and social
  safety net benefits" (NRR iniziale 58% media OECD; 50–80% single low earner); OECD
  **Benefits and Wages** database (modelli tax-benefit, calcolatore).
- **Esito misurato (brief 09, 20 seed, 2000 step, `results/ces_b09_*`):**
  - **E1 — dose-risposta fiscale (crowding-in confermato dove demand-constrained).**
    Allo scenario **headline** (c0=1.0, σ=0.5, η=0.10, ρ=0.40) rr 0→0.75 abbassa U
    **0.566→0.373** e — punto teorico chiave — alza sia Y (82→119) sia **K
    (299→436)**: in regime demand-constrained il trasferimento è **crowding-in** (più
    domanda → più profitti → più investimento via `I=ρπ`). Allo scenario **anchor**
    (c0=2.0, σ=1, η=0, ρ=0.40), effetto direzionalmente identico ma più tenue (U
    0.257→0.177, K 418→469). Corrisponde al probe di design (headline K 292→439). La
    **frazione cash-constrained resta 0.90 = tutti i 90 lavoratori, invariante a rr**:
    il sussidio non solleva i lavoratori dal vincolo di liquidità (MPC≈1 mantenuto),
    quindi il **canale del moltiplicatore di bilancio in pareggio resta intatto** — è
    il motivo per cui il crowding-in regge lungo tutta la dose-risposta. Aliquota
    realizzata modesta (τ ≤ 0.10 anchor, ≤ 0.25 headline), cap **mai** al margine qui.
  - **E2 — robustezza della frontiera (σ\* si muove MOLTO con rr, non "poco").** A
    c0=1.0, sul supporto comune across-config, σ\*(Y) a rr=0 è 0.830 (η=0), 0.833
    (η=0.10) [anchor naturale η=0/rr=0: σ\*=0.654, coerente col brief 05]. A **rr=0.5
    σ\* è INDEFINITO** (`frac_undefined`≈1.0): tutte le pendenze `dY/dρ` diventano
    **positive** su tutto il range σ testato (σ=1: +38.7; σ=1.5: +19.3), spingendo σ\*
    **sopra 1.5**. Il sussidio **elimina la regione wage-led**: l'investimento torna
    espansivo a ogni σ perché il pavimento di domanda garantisce che la capacità extra
    trovi domanda. La frontiera su **U** invece **non si muove** (σ\*_U ≈ 0.40→0.43 a
    η=0; ≈0.46 a η=0.10): il sussidio cambia la risposta dell'output alla ritenzione
    molto più di quella della disoccupazione. **Contrariamente all'attesa del brief**
    ("spostamento piccolo"), ma coerente con E1.
  - **E3 — ipotesi di stabilizzazione c0=2.0: FALSIFICATA (il collasso si ALLARGA).**
    Celle con qualche collasso (≥1 seed su 20): η=0.10 **16→26** da rr=0 a rr=0.5;
    η=0.15 **16→29**; frazione media di seed a `U=1` **0.125→0.266** e **0.129→0.333**.
    La cella di riferimento (σ=1.5, ρ=0.40, η=0.10) collassa a `K=0, U=1` **sia a rr=0
    sia a rr=0.5**, ma a rr=0.5 la tassa è **fissata al cap** (τ=0.600,
    `frac_periods_at_cap`=1.0). **Saturazione dello strumento diagnosticata** come
    richiesto: nell'angolo di collasso il cap morde in una frazione crescente di
    periodi (`frac_at_cap` 0.14 e 0.22 in media sulla griglia; `mean_tax` 0.14 e 0.21).
    Meccanismo: (i) dove la base imponibile è quasi tutta salariale (imprese in
    collasso, dividendi ~0), tassare lavoratori per pagare lavoratori è
    **MPC-neutrale** → nessun boost netto di domanda; (ii) il sussidio indicizzato a
    `w_t` è **prociclico** — a U alta la wage curve abbassa `w_t` e quindi il sussidio,
    così il pavimento è più debole proprio quando servirebbe; (iii) la domanda extra
    che il sussidio inietta **amplifica** l'oscillazione salario→occupazione→erosione
    di capitale (meccanismo brief 07) nell'angolo alto-σ. Il collasso c0=2.0 non nasce
    da domanda debole floor-abile: il pavimento di domanda non lo tocca, lo aggrava.
- **Verdetto:** **ancorabile a fonte OECD, ma sweep non punto.** `rr=0` è il default
  per l'identità col modello senza governo. Risultato duplice: il sussidio **funziona**
  come stabilizzatore di domanda dove il regime è demand-constrained (E1 crowding-in;
  E2 elimina il wage-led), ma **non** dove il collasso è guidato dall'offerta/oscillazione
  di capitale (E3, ipotesi falsificata). `max_tax=0.6` è convenzione, non stima; la
  saturazione al cap va **riportata**, non nascosta. Verifica contro
  `ces_b09_dose_response.csv`, `ces_b09_sigma_star.csv`, `ces_b09_collapse_map.csv`,
  `ces_b09_trace.csv`.

### `max_tax` = 0.6 — cap sull'aliquota di bilancio in pareggio
- **Ruolo:** `τ = min(max_tax, desired/base)`; se il sussidio desiderato richiede
  un'aliquota superiore, il sussidio si scala giù a ciò che il cap raccoglie (budget
  in pareggio per costruzione). Guardrail contro aliquote esplosive quando la base
  imponibile crolla (angolo di collasso c0=2.0).
- **Empirico:** nessun referente diretto — è una **convenzione dichiarata**, non una
  stima. Il ramo Leontief usava lo stesso 0.6.
- **Verdetto:** **convenzione.** L'aliquota realizzata `Tax_Rate` e la frazione di
  periodi al cap `frac_periods_at_cap` sono **esiti misurati** da riportare (diagnostica
  di saturazione dello strumento), non parametri da ancorare. Candidato per la
  sensitivity analysis (punto 5), non per l'ancoraggio.

---

## Blocco eterogeneità — probe di viability (brief 10, roadmap punto 8)

> Introdotto dal brief 10. **Non** implementa il punto 8 come feature: aggiunge il
> minimo necessario a **testare** l'assunzione di omogeneità del lato imprese e a
> misurare dove si rompe. `spread=0` (default) annida il modello omogeneo
> **bit-for-bit** (byte-check vs `ces_b05`/`ces_b07`/`ces_b09`: **3/3 PASS, dev = 0.0**).
> Fuori scope: selezione, riallocazione della domanda, rewiring della rete,
> entry/exit (= punto 12, dichiarato future work).

### `productivity_spread` = dial sperimentale, default 0.0 — dispersione della TFP d'impresa
- **Ruolo:** ventaglio lineare mean-preserving alla costruzione,
  `A_i = A·(1 + spread·(2i−(n−1))/(n−1))`, i = 0..n−1, quindi A da `A(1−spread)` a
  `A(1+spread)` con media esattamente `A` (verificato in floating point, non assunto:
  esatto sulla griglia n=10 usata, ≤1e-15 su n dispari/pari testati). Ogni impresa
  riceve la propria A_i, **anche nell'aspettativa iniziale di domanda** (seminare
  un'impresa a bassa A con la capacità dell'impresa media sarebbe uno shock di inizio
  run confuso col probe). Validato ∈ **[0, 1)**: a spread=1 l'impresa più debole ha
  A=0 e non può mai produrre — è un evento di uscita che il modello non sa gestire.
- **Convenzione dichiarata:** gli `ANCHOR_*` (K0, L0) e `U_REF` restano **congelati e
  comuni** a tutte le imprese; A_i scala la Y0 della normalizzazione CES della singola
  impresa. I benchmark aggregati (`Potential_Output`, `Wage_Share_Profitmax`) usano la
  **media** del ventaglio (`model.productivity`): convenzione di reporting per una
  diagnostica, nessun effetto sulla dinamica.
- **NON è un parametro calibrato** e non ha un valore "giusto": è un **dial
  sperimentale** il cui unico scopo è localizzare la soglia. Non entra in nessuna
  calibrazione e resta a 0 in ogni altro risultato del repo.
- **Empirico — confronto qualitativo, NON mappatura quantitativa.** La dispersione
  della TFP **intra-settore** è ampia: **Syverson (2004)** riporta un rapporto **90/10
  ≈ 2:1** nel manifatturiero USA (a 4 cifre SIC); vedi anche **Bartelsman & Doms
  (2000)** per la rassegna. La soglia di collasso misurata qui corrisponde a un
  rapporto max/min di **≈1.22–1.29**, molto **sotto** il dato. **Le unità non
  coincidono e nessuna mappatura è pretesa:** la semi-ampiezza di un ventaglio lineare
  non è un rapporto 90/10 di log-TFP, e la `A` del modello entra in una CES
  normalizzata non stimata su dati. Regge solo la lettura qualitativa — ed è
  sufficiente.
- **Esito misurato (brief 10, 20 seed, 2000 step, tail 50, `results/ces_b10_*`):**
  - **È una scogliera, non un gradiente.** Sotto soglia nessuna impresa muore e
    l'economia è sana; **uno step di griglia sopra, tutte e 10 le imprese sono morte**,
    `Y=0`, `U=1`, K che decade geometricamente a `3.5e-34` allo step 2000. Soglia fra
    spread 0.10 e 0.125 (scenario **anchor**, c0=2.0/σ=1/η=0) e fra 0.125 e 0.15
    (**headline**, c0=1.0/σ=0.5/η=0.10).
  - **La claim mean-field, resa precisa.** Sotto soglia nessuna impresa muore, ma
    "identico all'omogeneo" vale **meno lontano** di "sano": Y resta dentro la banda
    inter-seed di `spread=0` solo fino a spread **0.05** (anchor, rr=0.5) o 0.125
    (headline). A spread=0.10 gli aggregati anchor si sono mossi in modo **rilevabile**
    a 20 seed — e **verso l'alto** (Y 132.1→134.7, U 0.258→0.229): la dispersione
    mean-preserving è **lievemente espansiva** fin quando non è fatale. Enunciato
    difendibile: *lato imprese quasi-rappresentativo negli **aggregati** fino a ~±5%,
    viabile ma non più identico fino alla scogliera*. **Non** "l'eterogeneità non
    conta".
  - **Il domino (tracciato, headline, spread=0.20, seed 0).** L'impresa a bassa A serve
    la stessa domanda di rete con più lavoro → profitto più basso → `I < δK` → si
    decapitalizza per prima (K 38→~0 allo step 250). Le quote di spesa restano puntate
    su di lei (**domanda distrutta**) e i suoi licenziati perdono il reddito
    (**esternalità di domanda**), quindi cadono anche le imprese ad alta A: K della più
    forte a zero allo step 500, U a 1. **È esattamente ciò che il macchinario mancante
    avrebbe evitato:** con entry/exit e rerouting quella domanda sarebbe migrata a
    un'impresa viva.
  - **E2 — il sussidio brief 09 attutisce? FALSIFICATO: peggiora.** Ipotesi: mantenere
    reddito ai licenziati alza la soglia. Misurato, la **abbassa**. A spread=0.125
    l'headline ha **0/20** seed con imprese morte; lo stesso scenario a **rr=0.5** ne ha
    **18/20**, con **7/20** in collasso pieno (bacino misto genuino). La soglia di
    collasso pieno resta 0.15. **Meccanismo verificato, non ipotizzato** (seed 8,
    spread=0.125): il sussidio abbassa U (inizio run 0.544→0.445), la wage curve legge
    e **alza il salario** (`w_t` 0.836→0.853), e l'impresa a bassa A — il cui prodotto
    marginale è scalato dalla sua A — è la prima spinta sotto `I=δK`. A rr=0 quella
    impresa è in steady state stabile (K≈28, 6 lavoratori, profitto 3.73 allo step
    1200); a rr=0.5 si decapitalizza monotonicamente a `1.8e-6` allo step 800 e perde
    ogni lavoratore. Il cuscinetto di domanda esiste ma è **dominato dal medesimo canale
    salario→U** dei brief 07 e 09.
- **Reperto collaterale (dai test, non dal brief):** anche a **spread=0** le imprese
  **non** restano identiche. I link di consumo sono estratti a caso, quindi le imprese
  fronteggiano domanda diversa, profitti diversi e accumulano capitale diverso:
  `TopK_Share` (quota di K delle prime 3 su 10) parte da 0.30 esatto a t=0 e si assesta
  a **0.35–0.38** a regime. Il lato imprese è quasi-rappresentativo negli **aggregati,
  non nella sezione trasversale** — e la baseline di `TopK_Share` va letta contro il
  valore misurato a spread=0, mai contro 0.3.
- **Verdetto:** **dial sperimentale, non parametro da ancorare.** Default 0.0 per
  l'identità col modello omogeneo. La decisione sul punto 8 è **presa e documentata**:
  lato imprese dichiarato **quasi-rappresentativo con evidenza misurata**, feature non
  implementata, riallocazione (punto 12) dichiarata future work. **Limite dichiarato:**
  il probe stabilisce che una soglia esiste e dove sta per un ventaglio **lineare**;
  non dice nulla sulla forma distribuzionale (una A lognormale a pari varianza può
  avere soglia diversa). Verifica contro `ces_b10_summary.csv`,
  `ces_b10_thresholds.csv`, `ces_b10_trace.csv`, `ces_b10_nesting_check.csv`.

### `DEAD_FIRM_K` = 0.5, `TOPK_N` = 3 — convenzioni di reporting (brief 10)
- **Ruolo:** `Dead_Firms` conta le imprese con `K < DEAD_FIRM_K`; `TopK_Share` è la
  quota di capitale aggregato delle prime `TOPK_N` imprese. **Nessun effetto sulla
  dinamica:** il modello non ha uscita, quindi un'impresa "morta" conserva clienti,
  quota di domanda e libro paga (vuoto) — che è precisamente il meccanismo misurato.
- **Verdetto:** **convenzioni dichiarate**, non stime. Candidate per la sensitivity
  analysis (punto 5), non per l'ancoraggio.

---

## `c0` — esito dello stress test (brief 05 §2) — **il cerotto non regge, ma non per la ragione attesa**

Misurato: griglia σ×ρ×`c0`, 20 seed, 2000 step, media ultime 50 (Stadio A, 3.080 run);
sonda `c0 = 0.5` (Stadio B, 560 run). Vedi `ces_b05_stage_a_panel.csv`.

**1. La giustificazione di `c0=2.0` è falsificata — per misura, non per argomento.**
La frazione di famiglie cash-constrained è **0.90 a `c0`=2.0, 1.0 E 0.5**. Con 90
lavoratori su 100 famiglie, 0.90 significa **tutti i lavoratori, sempre**. Quindi
`c0=2.0` non compra nulla al meccanismo del gap di MPC.

**2. Ma anche la diagnosi del brief ("la causa è `c0 ≥ w̄`") è falsificata.** A
`c0 = 0.5 < w̄ = 0.9` i lavoratori restano cash-constrained al **99.97%**
(media 0.8997). La causa vera è **endogena**: un lavoratore è vincolato se
`wealth < (c0 − 0.09)/0.95`, e all'equilibrio i lavoratori **non accumulano
ricchezza** — spendono tutto, quindi restano senza cuscinetto, quindi restano
vincolati. Abbassare `c0` abbassa anche la soglia *e* la ricchezza: il vincolo non
si allenta. **Il gap di MPC è strutturale, non un prodotto di `c0`.**
> Conseguenza per il brief: la sonda §6.2 **non poteva** eseguire il test che si
> proponeva ("testare se il motore sopravvive quando i lavoratori NON sono
> cash-constrained al 100%"), perché `c0 < w̄` **non li libera**. Per liberarli
> servirebbe un altro intervento (es. dare ricchezza iniziale ai lavoratori, o
> `c1 < 1` con reddito più alto): proposta, non implementata.

**3. `c0` NON è neutrale sui risultati** (è una leva di regime vera):
| | `c0`=0.5 | `c0`=1.0 | `c0`=2.0 |
|---|---|---|---|
| Y (σ=0.5, ρ=0.40) | 68.2 | 88.7 | 129.5 |
| disoccupazione | 63.0% | 52.4% | 31.1% |
| quota salari | 0.488 | 0.482 | 0.479 |

`c0=0.5` produce un'economia con **63% di disoccupazione**: sonda di meccanismo, non
un'economia plausibile. La **quota salari è invece quasi invariante a `c0`** (0.479–0.488).

**4. Verdetto.** `c0` resta **non ancorabile** e va dichiarato come scelta di scala.
La sua rimozione non è però una decisione tecnica indolore: cambia i livelli di tutto
(Y, U) anche se non la quota salari. **Non ricalibrare senza decidere prima quale
regime di disoccupazione si vuole dichiarare** — a `c0=1.0` il modello gira al ~52% di
disoccupazione, che è esso stesso fuori scala rispetto a qualunque benchmark.
**Questa è la tensione aperta più grande del progetto, e il brief 05 non la chiude:
la registra.**

---

## Il sistema congiunto (α, ρ, δ, K/Y, I/Y) — leggere prima di ricalibrare

**Questi parametri NON sono ancorabili in isolamento.** A steady state il modello
impone due sole relazioni indipendenti (dato α):

```
I/Y = ρ·α                    (l'investimento è la ritenzione, a util_effect≈1)
K/Y = ρ·α/δ                  (steady state: I = δK, nessuna crescita di trend)
  ⇒ I/Y = δ · (K/Y)          (identità)
```

Quindi: **ρ fissa I/Y; δ fissa K/Y dato I/Y.** Due gradi di libertà, non quattro.
Non si può scegliere δ "guardando la letteratura su δ" senza spostare I/Y o K/Y.

**La calibrazione attuale centra entrambi i benchmark simultaneamente:**

| | modello (α=1/3, ρ=0.40, δ=0.05) | empirico | esito |
|---|---|---|---|
| I/Y | 0.133 | ~0.13–0.14 (inv. fisso non res./PIL) | ✓ |
| K/Y | 2.67 analitico / 2.58 misurato | ~2.5–3 | ✓ |

E δ ≈ 0.05 **è implicato** dai due target: `δ = (I/Y)/(K/Y) = 0.133/2.6 ≈ 0.05`.

**Errore da non ripetere (commesso e corretto in fase di ricerca):** si era
proposto di alzare δ verso 0.06–0.07 "perché più centrale nella letteratura di
calibrazione", compensando con ρ→0.47–0.55 per tenere K/Y in banda. Sbagliato:
avrebbe portato **I/Y a 0.157–0.183**, sfondando il target di investimento.
δ=0.05 non è "fascia bassa da correggere": è il valore congiuntamente coerente.
Per confronto, Mankiw usa δ≈0.04 con K/Y≈2.5 — *più basso* del valore attuale.

**Conseguenza per la scrittura:** il match congiunto di K/Y *e* I/Y è un
risultato di calibrazione genuino e va rivendicato come tale — ma va detto che è
un sistema a due gradi di libertà, non due validazioni indipendenti.

---

## Benchmark di validazione (target, non parametri liberi)

> ⚠️ **I benchmark di questa sezione sono in gran parte STALE.** Descrivono il core
> Cobb-Douglas **senza mercato del lavoro**, rimosso al punto 11. Marcati uno per
> uno qui sotto (brief 05 §7). Non citarli come risultati del modello attuale.

### ~~Quota salari / quota profitti — 0.667 / 0.333~~ — **STALE**
> ⚠️ **STALE dal punto 11.** "Esatte per costruzione (markup = α/(1−α))" non ha più
> referente: `markup` è stato **rimosso** e il salario fisso `w̄` è il parametro
> distributivo. **La quota salari è ora un ESITO MISURATO, non un'identità** — e
> un'identità vera per costruzione non validava comunque nulla.
> Limite strutturale nuovo: l'impresa non assume dove `MPL < w̄`, quindi la quota
> salari è **strutturalmente limitata dall'alto** dalla quota salari al profit-max
> — che vale `1−π0` **solo a σ=1** e dipende da σ altrove
> (`(1−π0)·z^(1−σ)`, vedi `agents.ces_wage_share_profitmax`).
> Il target giusto non è 0.667: è il **range empirico 0.60–0.68**.
> **Misurato (brief 05, celle viable, 20 seed): 0.351–0.606 a `c0`=1.0; 0.387–0.603
> a `c0`=2.0.** Quasi tutto **sotto** il range empirico 0.60–0.68, e il massimo lo
> tocca solo a σ=1.5 e ρ basso. Tensione aperta da riportare, non da ricalibrare via.
> Nota: la quota salari è **quasi invariante a `c0`** (0.479–0.488 a σ=0.5, ρ=0.40
> per `c0` ∈ {0.5, 1.0, 2.0}) — è σ e ρ a muoverla, non la leva di domanda.
- Testo storico: nel modello esatte per costruzione (markup = α/(1−α));
  empiricamente la quota salari USA è ~0.60–0.68 (compensation share).
  Fonte: Cottrell (2019); Gollin (2002).

### K/Y — 2.58 (target 2.5–3)
- Nel modello: `K/Y = ρα/δ`. Empiricamente il rapporto capitale-prodotto
  *produttivo* è ~2.5–3 (manuali: ~2.5; misure variano col perimetro di
  capitale). Fonte: calibrazione standard (Mankiw). **Match buono**, ma dipende
  da δ (fascia bassa) e ρ.

### I/Y — 0.133
- Nel modello: `I/Y = ρα`. Da confrontare con l'investimento fisso non
  residenziale/PIL USA (~0.13–0.14) — **coincidenza incoraggiante, DA VERIFICARE**
  con dato primario (BEA NIPA); attenzione a gross vs net e al perimetro.

### ~~Utilizzo della capacità — 0.99 (modello)~~ vs ~0.80 (empirico) — **STALE**
> ⚠️ **STALE dal punto 11.** Il "0.99" apparteneva al core Cobb-Douglas **senza
> mercato del lavoro**, che era capacity-constrained ovunque. Quel regime **non
> esiste più**: con l'occupazione endogena il modello è **demand-constrained**
> quasi ovunque (brief 05: 76 celle viable su 77 a `c0`=1.0), e l'utilizzo misurato
> sta fra **0.222 e 0.870** a seconda di (σ, ρ) — vedi `ces_b05_stage_a_cells.csv`.
> Anche la *definizione* è cambiata: `u` è ora misurato contro la capacità al
> **profit-max**, non contro `Y*(K, L)` (che degenererebbe a `u ≡ 1` con L
> endogeno).
- **Cautela sulla lettura di `u` (brief 05).** La capacità profit-max usata dal
  denominatore **non è vincolata dalla forza lavoro**: a `w̄ = 0.9` le imprese
  vorrebbero collettivamente ~170 lavoratori, ma ne esistono `N = 100`. Quindi `u`
  misura la distanza da una scala **irraggiungibile**, e siede strutturalmente
  sotto `target_utilization = 0.90` → l'acceleratore è **permanentemente in
  frenata**. Non è un bug del brief 05 (che non tocca il modello): è una proposta
  di revisione, registrata e non implementata.
- Confronto empirico invariato: l'economia reale opera ~80% con slack persistente.
  Fonte: Federal Reserve G.17.

---

## Tensioni aperte / cose da fare

1. ~~Rafforzare `retention_ratio` con una fonte aggregata di payout~~ **RISOLTO
   diversamente:** ρ va ancorato a I/Y, non al payout (vedi voce `retention_ratio`
   e §"Il sistema congiunto"). Nessuna ricalibrazione δ/ρ: la coppia attuale è
   congiuntamente coerente.
2. ~~**`wealth_effect=0.08`**~~ **RISOLTO (brief 05):** il codice gira **0.05**, che
   è la media cross-country di **Slacalek (2009)** → **ancorato**. Restava
   `target_utilization = 0.90`, sopra l'empirico (~0.80): tuttora una **leva di
   regime dichiarata**, non una stima.
   > **Nota di discrepanza (brief 05).** Il brief 05 §2.1 elenca
   > `target_utilization = 0.70` fra i cerotti compensativi. **Il codice gira
   > 0.90** (`model.MacroModel`), e questo file diceva 0.90 già prima. Il valore
   > 0.70 non ha referente nel codice: registrato come discrepanza del brief, non
   > "corretto" nel codice — il modello non si tocca in un task di validazione.
3. **`c0 = 2.0` è il debito aperto più grande.** Non ancorabile e con
   giustificazione falsificata (vedi voce). L'esito dello stress test del brief 05
   è nella sezione dedicata più sotto: è quello che decide se il parametro va
   rimosso, e con quali conseguenze sull'headline.
3. **Unità temporale del periodo:** chiarirla, perché δ, K/Y, I/Y sono
   annualizzati implicitamente.
3bis. **⚠️ La disoccupazione è fuori scala a ogni `c0` (misurato, brief 05).** Alla
   ρ calibrata (0.40) e nel range empirico di σ, il modello gira a **U ≈ 52%**
   (`c0`=1.0) o **U ≈ 31%** (`c0`=2.0); la sonda `c0`=0.5 dà **63%**. Nessuno di
   questi è un'economia plausibile (USA: ~4–10%). **Non è un benchmark che si
   aggiusta con `c0`**: nessun `c0` testato porta U in banda. È una tensione
   strutturale del punto 11 (salario fisso `w̄=0.9` + `L=min(...)`), da affrontare
   come questione di design — non da nascondere scegliendo il `c0` meno imbarazzante.
3ter. **`σ*` non è un numero — è una frontiera `σ*(ρ)` (misurato, brief 05).**
   `Y(ρ)` è a **U** (curvatura significativa in 20 celle su 22, |t| fino a 20.5;
   punto di svolta **dentro** il supporto in 19 su 22), quindi il segno di `dY/dρ`
   dipende da **ρ** oltre che da σ. Una pendenza OLS su tutto il supporto è
   **precisa e sbagliata**: adatta una retta a una curva. Riportare `σ*(ρ)`, mai un
   `σ*` unico. Vedi `ces_b05_curvature.csv`, `ces_b05_support_sensitivity.csv`.
4. **Assunzione Cobb-Douglas a quote costanti:** dichiararla come scelta, citando
   la critica empirica (Karabarbounis–Neiman; Antràs).
5. **Verificare I/Y** con dato BEA primario (serie NIPA investimento fisso non
   residenziale/PIL): il match a 0.133 regge su una cifra di ordine di grandezza,
   non ancora su una serie estratta. Attenzione a gross vs net e al perimetro di
   capitale (il modello ha solo capitale produttivo d'impresa, niente residenziale).
6. **Ancoraggio delle leve di domanda: rimandato al punto 11.** λ e
   `target_utilization` non vanno ancorati in questo core: l'empirico
   (λ≈0.05, u≈0.80) implica un regime **demand-constrained**, in cui il capitale
   non morde — cioè il regime che questo core esiste per superare. La tensione si
   scioglie con il mercato del lavoro, dove lo slack diventa disoccupazione e un
   regime demand-constrained realistico può convivere con un canale di offerta
   vivo. Fino ad allora: leve di regime **dichiarate**, non stime.
6. **Prossimo:** al punto 9 (markup endogeno) il legame markup↔quota salari salta
   e serviranno dati sui markup (De Loecker et al.).

---

## Riferimenti

- Teglio, A. (2025). Rationality, inequality, and the output gap: evidence from a
  disaggregated Keynesian cross diagram. *Journal of Economic Interaction and
  Coordination*, 20(1), 107–139. (online-first 2024)
  <https://link.springer.com/article/10.1007/s11403-024-00412-4>
- Gollin, D. (2002). Getting Income Shares Right. *Journal of Political Economy*.
- Crafts, N. (2021). Growth accounting in economic history. *Journal of Economic
  Surveys*. <https://onlinelibrary.wiley.com/doi/10.1111/joes.12348>
- Karabarbounis, L. & Neiman, B. (2014). The Global Decline of the Labor Share.
  *Quarterly Journal of Economics*, 129(1), 61–103.

### Elasticità di sostituzione σ (brief 04)
- Chirinko, R. S. (2008). σ: The long and short of it. *Journal of Macroeconomics*,
  30(2), 671–686.
- Chirinko, R. S. & Mallick, D. (2017). The Substitution Elasticity, Factor Shares,
  and the Low-Frequency Panel Model. *American Economic Journal: Macroeconomics*,
  9(4), 225–253.
- Knoblach, M., Roessler, M. & Zwerschke, P. (2020). The Elasticity of Substitution
  Between Capital and Labour in the US Economy: A Meta-Regression Analysis. *Oxford
  Bulletin of Economics and Statistics*, 82(1), 62–82.

### CES normalizzata (brief 04)
- Klump, R. & de La Grandville, O. (2000). Economic Growth and the Elasticity of
  Substitution: Two Theorems and Some Suggestions. *American Economic Review*,
  90(1), 282–291.
- Klump, R. & Saam, M. (2008). Calibration of normalised CES production functions in
  dynamic models. *Economics Letters*, 98(3), 256–259.
- Klump, R., McAdam, P. & Willman, A. (2012). The Normalized CES Production Function:
  Theory and Empirics. *Journal of Economic Surveys*, 26(5), 769–799.
- Temple, J. (2012). The calibration of CES production functions. *Journal of
  Macroeconomics*, 34(2), 294–303. (**critica**: la normalizzazione non isola effetti
  "puri" di σ; σ non è un parametro profondo — da riportare, non nascondere.)
- Antràs, P. (2004). Is the U.S. Aggregate Production Function Cobb-Douglas?
- Solow, R. (1957). Technical change and the aggregate production function.
- BEA, Fixed Assets Accounts & Depreciation Rates. <https://www.bea.gov/itable/fixed-assets>
- BLS (2022). Alternative Capital Asset Depreciation Rates for U.S. Capital.
  <https://www.bls.gov/opub/mlr/2022/article/alternative-capital-asset-depreciation-rates-for-us-capital-and-total-factor-productivity-measures.htm>
- Angeletos, G.-M. (2007). Uninsured idiosyncratic investment risk. (δ=0.08, α=0.36)
- **Slacalek, J. (2009). What Drives Personal Consumption? The Role of Housing and
  Financial Wealth. *The B.E. Journal of Macroeconomics* 9(1)** (anche ECB Working
  Paper 1117). — **fonte verificata di `wealth_effect` = 0.05**: MPC di lungo periodo
  sulla ricchezza totale ≈ 5 cent, media su 16 paesi; 4–6 cent nelle economie
  market-based; stime per paese tipicamente 0–10 cent.
- Case, K., Quigley, J. & Shiller, R. (2005/2013). Comparing Wealth Effects.
- Carroll, C., Otsuka, M. & Slacalek, J. (2011). How Large Are Housing and
  Financial Wealth Effects? *Journal of Money, Credit and Banking*.
- Federal Reserve (2025). Wealth Heterogeneity and Consumer Spending. FEDS Notes.
  <https://www.federalreserve.gov/econres/notes/feds-notes/wealth-heterogeneity-and-consumer-spending-20250805.html>
- Paiella, M. (2009). The stock market, housing and consumer spending: a survey.
- Federal Reserve. G.17 Industrial Production and Capacity Utilization.
  <https://www.federalreserve.gov/releases/g17/current/>
- De Loecker, J., Eeckhout, J. & Unger, G. (2020). The Rise of Market Power.
  *Quarterly Journal of Economics*.
- Cottrell, A. (2019). The Cobb–Douglas Production Function. Lecture notes.

### Wage curve (brief 07)
- **Blanchflower, D. G. & Oswald, A. J. (1994). *The Wage Curve*. MIT Press.** —
  fonte primaria dell'elasticità salario-disoccupazione ≈ −0.10 (relazione di
  *livello*, non di variazione: salario locale funzione decrescente della
  disoccupazione locale).
- **Nijkamp, P. & Poot, J. (2005). The Last Word on the Wage Curve? *Journal of
  Economic Surveys* 19(3), 421–450.** — meta-analisi su 208 stime da 17 paesi;
  elasticità "corretta" ≈ −0.07.

### Aspettative adattive (brief 08)
- **Nerlove, M. (1958). Adaptive Expectations and Cobweb Phenomena. *Quarterly
  Journal of Economics* 72(2), 227–240.** — forma delle aspettative adattive a
  parziale aggiustamento; il coefficiente di aspettativa è stimato per serie, non
  universale.
- **Evans, G. W. & Honkapohja, S. (2001). *Learning and Expectations in
  Macroeconomics*. Princeton University Press.** — constant-gain learning; il gain
  costante come caso adattivo. Nessuna stima strutturale di un gain di domanda
  d'impresa: `λ_e` è uno sweep.

### Governo / sussidio di disoccupazione (brief 09)
- **OECD (2024). *Society at a Glance 2024*, "Unemployment and social safety net
  benefits".** — net replacement rate iniziale ≈58% (media OECD, single al salario
  medio), ~37% per la disoccupazione di lungo periodo; 50–80% per un single low
  earner. Fonte primaria di `benefit_replacement_rate`.
  <https://www.oecd.org/en/publications/society-at-a-glance-2024_918d8db3-en/full-report/unemployment-and-social-safety-net-benefits_ddfedfa8.html>
- **OECD, Benefits and Wages database** (Tax-Benefit models, web calculator) — regole
  tax-benefit per età-lavorativa; base dei net/gross replacement rate.
  <https://www.oecd.org/social/benefits-and-wages/data>

### Eterogeneità di impresa / dispersione della TFP (brief 10)
- **Syverson, C. (2004). Product Substitutability and Productivity Dispersion.
  *Review of Economics and Statistics* 86(2), 534–550.** — dispersione della TFP
  **intra-settore** nel manifatturiero USA (industrie SIC a 4 cifre): rapporto
  **90/10 ≈ 2:1**. Referente empirico del confronto qualitativo del brief 10.
- **Bartelsman, E. J. & Doms, M. (2000). Understanding Productivity: Lessons from
  Longitudinal Microdata. *Journal of Economic Literature* 38(3), 569–594.** —
  rassegna della dispersione e della persistenza della produttività a livello di
  stabilimento; conferma l'ordine di grandezza.
- **Nota sull'uso:** entrambe servono **solo** a collocare qualitativamente la soglia
  misurata (max/min ≈1.22–1.29) rispetto al dato (90/10 ≈2:1). **Nessuna mappatura
  quantitativa** fra `productivity_spread` e una dispersione di TFP stimata: unità e
  costrutti diversi (vedi la voce del parametro).
