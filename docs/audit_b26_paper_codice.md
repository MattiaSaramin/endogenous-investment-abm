# Brief 26 — Audit di coerenza paper ↔ codice ↔ artifact (referto)

> **Referto di sola VERIFICA.** Nessuna riga sotto `paper/` o `src/` è stata
> toccata da questo brief (`git diff --stat -- paper/ src/` per la parte *mia* =
> 0; vedi §0.1 per lo stato ereditato di `paper/`). Le divergenze sono
> **descritte e classificate**, non corrette: la riparazione è un brief
> successivo, deciso da Mattia (gerarchia §6 di `METHODOLOGY.md`: paper vs codice
> **non è normato** ⇒ è un finding da arbitrare, non un bug da chiudere).

Numerazione: l'ultimo brief registrato in `METHODOLOGY.md` §8 è **b25** (commit
`91ba41a`, benché il file `brief_25_*.md` resti untracked). Questo brief è quindi
**b26**, senza rinumerazione.

---

## 1. Sommario esecutivo

Il sito a rischio massimo — la **FOC dell'impresa** (`af27915`, salario reale
`w_t/P`) — è **PULITO**: il paper dichiara `MPL = w`, il codice usa `w_t` nel path
di default (numerario 1, dove reale = nominale) e `w_t/P` solo col probe prezzi,
dichiarato in `07_stress`. Nessuna delle 49 cifre del registro è sbagliata; i 19
parametri di `tab:params` coincidono coi default del codice (0 MISMATCH).

**Finding, in ordine di severità:**

1. **[MEDIA — stato di lavorazione, non un difetto committato] `paper/` ha modifiche
   non committate (WIP) che io NON devo toccare, e una di esse è una regressione:**
   `eq:investment` ha **perso l'operatore `\clip`** nel working tree (HEAD:
   `\clip(\rho\Pi_{t-1}\phi_t,\underline I,\Pi_t)` corretto → worktree:
   `(\rho\Pi_{t-1}\phi_t,\underline I,\Pi_t)`, una tupla senza operatore). Vedi §0.1
   e Fase 2, sito 8.
2. **[BASSA — `NON_DICHIARATO`, inerte] Sito 7 (acceleratore).** Il paper scrive
   l'utilizzo **realizzato** `u_{t-1}`; il codice legge l'**aspettativa** `u^e`
   (b17) con gain `λ_u`. Coincidono a `λ_u=1` (default, mai sweepato nel paper):
   corretto come-eseguito, ma il meccanismo `u^e/λ_u` è assente dal paper.
3. **[BASSA — `NON_DICHIARATO`] Sito 2 (quarto regime).** Il paper nomina **tre**
   vincoli/regimi; il codice ne ha un **quarto**, `"capital"` (soffitto `Y_max(K)`
   per σ<1, `ces_capital_ceiling`, lineare in K), senza referente nel paper.
4. **[BASSA — pedice, immateriale] Sito 8 (cap investimento).** Il paper cappa a
   `Π_t`; il codice cappa a `Π_{t-1}` (`profit_last_period`, l'investimento si
   pianifica prima del profitto corrente). Uguale in steady state.
5. **[TRIVIALE — `NON_DICHIARATO`] Siti 4 e 6.** Il `floor` (headcount intero) su
   `L` e la guardia `max{·,0}` sul consumo sono nel codice, non nell'equazione.

**Falsi positivi noti (§5.3), verificati ANCORA falsi positivi e NON corretti:**
`0.771` (=1230/1596, derivato #1) e `59.4` (`tab:baseline`, sorgente non inclusa
#2). Vedi Fase 3.

Sono **0 divergenze di cifra** e **0 default di parametro errati**. Le divergenze
sono tutte fra un'equazione *stampata* e una *generalizzazione del codice inerte
nei risultati riportati*, oppure guardie/pedici immateriali.

---

## 0.1 Nota di stato ereditato: `paper/` in WIP non committato (NON mio)

All'inizio della sessione l'albero di lavoro portava **modifiche `paper/` già non
committate**, che io **non ho prodotto e non ho toccato**:

```
git diff --stat -- paper/  →  7 file, 71 inserzioni, 341 cancellazioni
 D paper/.gitignore
 M paper/README.md  frontmatter.tex  main.tex  b_notation.tex
 M paper/sections/{01_introduction,02_literature,03_model,08_fiscal,11_limitations}.tex
```

Natura misurata delle modifiche (diff HEAD→worktree): un passaggio editoriale di
**anglicizzazione** (`normalised`→`normalized`, `labour`→`labor`, `realised`→
`realized`, `\Cref`→`\cref`) e una ristrutturazione di intro/letteratura, **più una
regressione**: `03_model.tex` `eq:investment` ha perso `\clip` (finding #1).

**Conseguenze operative dichiarate:**

- L'audit legge la versione **on-disk (working tree)**, esattamente come fanno
  `verify_paper.py`/`coherence.py`/`sweep_rounding.py`. Per le **equazioni** (Fase 2)
  ho classificato contro la versione **committata (HEAD)** come referente canonico e
  coerente, e ho segnalato a parte ogni delta introdotto dal WIP (solo `eq:investment`
  ne ha uno sostanziale; il resto è ortografia/reflow).
- Il **conteggio token dello sweep (611)** coincide col numero dichiarato nel brief,
  ma riflette il working tree; la classificazione di Fase 3 eredita lo stesso caveat.
- **Il commit di questo brief stagea SOLO i miei deliverable** (`scripts/verify_model.py`,
  `scripts/audit_b26_uncovered.py`, `results/audit_b26_*.csv`, questo file,
  `METHODOLOGY.md`). `paper/` resta con il suo WIP intatto; `git add -A`/`git add paper`
  sono **vietati**. Quando il WIP verrà committato, la Fase 1 e la Fase 2 vanno
  **rieseguite** contro la nuova base.

---

## 2. Fase 0 — baseline della toolchain (misurata, non attesa)

| check | esito misurato | atteso (brief) | note |
|---|---|---|---|
| `pytest -q` | **569 passed** (190.83 s) | 569 | = numero in `a_validation.tex`. Punto cieco #4 (b24): misurato senza CSV. |
| `verify_paper.py` | **0 FAIL** — 47 OK, 1 AMBIGUOUS, 1 SKIP | 0 FAIL | `sobol_sigma_ST_viable` AMBIGUOUS **per costruzione** (`0.008` ×2 in `09_sensitivity.tex:99`). |
| `verify_paper.py --selftest` | ALL PASS (exit 0) | PASS | discrimina OK/AMBIGUOUS su input iniettato. |
| `coherence.py` | **0 DIVERGENT** — 10 coherent, 38 single-doc, 1 null; **0 missing** | 0 DIVERGENT + `RESULTS.md` MISSING | **DRIFT dal brief**: `RESULTS.md` ora è **presente su disco** (untracked), quindi coherence non lo segnala più mancante. Debito = untracked in git, non assente. |
| `sweep_rounding.py` | 0 firme double-round; **56 inclusi**, 611 token | 0 firme; ~51 inclusi | vedi §2.1 (inclusione + byte-identità). |
| `sweep_rounding.py --selftest` (`§1.4 probe`) | BOTH PASS (find/control) | PASS | detector fidato. |
| `make_tab_sobol.py` | **byte-identico** al blocco inline | identico | `09_sensitivity.tex:95–99` (marcatore `do not hand-edit`:94). |
| `make_tab_prices.py` | **byte-identico** al blocco inline | identico | `07_stress.tex:113–119` (marcatore:112). |

**Contatori (i quattro assi della toolchain):** `verify_paper` 0 FAIL · `coherence`
0 DIVERGENT · `sweep_rounding` 0 firme · `pytest` 569. **b26 aggiunge:**
`verify_model` 0 FAIL (Fase 1).

**Conteggio pagine — NON citabile come misurato.** Il workflow `.github/workflows/paper.yml`
compila il PDF ed emette solo `::notice::Overfull hbox count` / `Underfull hbox count`
(righe 72–73) + lo stato di compilazione. **Non esiste una riga `::notice::Pages:`.**
Finché non c'è, i conteggi di pagine non si riportano come misurati (debito dichiarato).

### 2.1 Controllo mai fatto: regola di inclusione dello sweep sui 99 CSV

- `results/` contiene **99 CSV**. Lo sweep dichiara **56 artifact inclusi** (era 51 a
  b19: **drift atteso** dai CSV aggiunti dopo b19) e 48 esclusi (dump >100 righe,
  archivi, side-car JSON).
- **La frattura regge, netta.** Row-count massimo fra gli **inclusi** = **88**
  (`ces_b07_slopes.csv`); minimo fra gli **esclusi per soglia** = **154**
  (`ces_b05_stage_a_cells.csv`). Nessun file nell'intervallo 89–153: la soglia
  `ROW_THRESHOLD=100` separa ancora in modo pulito. I valori 88/154 sono **esattamente**
  quelli dichiarati nel brief.
- **Byte-identità del CSV committato** `results/paper_rounding_sweep.csv`: la
  rigenerazione **differisce** dal committato — ma la differenza è **interamente
  spiegata dal WIP di `paper/`** (§0.1), NON è la classe di drift b22-bis. Prova
  misurata: il committato referenzia `01_introduction.tex` **riga 46** per il token
  `0.42`; la rigenerazione referenzia **riga 23**, perché il WIP ha spostato quel token.
  Il committato è coerente con `HEAD:paper/`, quindi **NON è stale**. (Ho rigenerato per
  il test e poi **ripristinato** `git checkout -- results/paper_rounding_sweep.csv`; ora è
  clean.)

---

## 3. Fase 1 — `scripts/verify_model.py`: parametri paper ↔ default codice

**Deliverable nuovo committato.** Legge i default reali via
`inspect.signature(MacroModel.__init__)` e gli attributi di modulo (`U_REF`,
`ANCHOR_*`) — **importa il modello ma NON esegue nulla** (nessun `.step()`);
confronta round-once **ROUND_HALF_UP** al `decimals` dichiarato; verifica che il
valore stampato compaia **una sola volta** sulla riga di `tab:params` che porta
il simbolo (regex `context`, come `verify_paper.py`).

`--selftest` **FALLISCE netto** su default alterato — dimostrazione (output reale):

```
[1] delta as coded        -> MATCH      (round(0.05,2)=0.05 vs 0.05)   => PASS
[2] delta injected = 0.09 -> MISMATCH   (round(0.09,2)=0.09 vs 0.05)   => PASS
[3] forged needle '0.123456' -> NOT_IN_TEX                              => PASS
SELFTEST VERDICT: ALL PASS
```

**Esito main: 19/19 MATCH, 0 MISMATCH, 0 AMBIGUOUS** (`results/audit_b26_params.csv`).

| simbolo | referente codice | default letto | dec | stampato | riga `.tex` | esito |
|---|---|---|---|---|---|---|
| σ | `sigma` | `1.0` | — | swept | 04_calibration:45 | MATCH (annida a 1.0) |
| π₀ | `pi0` | `0.3333…` | 4 | `1/3` | 04_calibration:48 | MATCH |
| η | `eta` | `0.0` | — | swept | 04_calibration:50 | MATCH (annida a 0.0) |
| λ | `wealth_effect` | `0.05` | 2 | `0.05` | 04_calibration:52 | MATCH |
| ρ | `retention_ratio` | `0.40` | 2 | `0.40` | 04_calibration:55 | MATCH |
| rr | `benefit_replacement_rate` | `0.0` | — | swept | 04_calibration:57 | MATCH (annida a 0.0) |
| δ | `delta` | `0.05` | 2 | `0.05` | 04_calibration:62 | MATCH |
| U_min | `u_min=None`→`1/N` | `0.01` | 2 | `0.01` | 04_calibration:65 | MATCH (derivato: 1/100) |
| w_min | `wage_floor` | `0.45` | 2 | `0.45` | 04_calibration:65 | MATCH |
| max τ | `max_tax` | `0.6` | 1 | `0.6` | 04_calibration:67 | MATCH |
| I̲ | `investment_floor` | `0.1` | 1 | `0.1` | 04_calibration:69 | MATCH |
| ū | `target_utilization` | `0.90` | 2 | `0.90` | 04_calibration:70 | MATCH |
| K₀ | `K0=ANCHOR_K0` | `41.8735…` | 2 | `41.87` | 04_calibration:75 | MATCH |
| L₀ | `L0=ANCHOR_L0` | `7.39533…` | 3 | `7.395` | 04_calibration:75 | MATCH |
| U_REF | `U_REF` (modulo) | `0.260466…` | 5 | `0.26047` | 04_calibration:77 | MATCH |
| w̄ | `wage_rate` | `0.9` | 1 | `0.9` | 04_calibration:79 | MATCH |
| K_init | `initial_capital` | `40.0` | 1 | `40.0` | 04_calibration:80 | MATCH |
| β | `beta` | `0.5` | 1 | `0.5` | 04_calibration:82 | MATCH |
| c₀ | `c0` | `2.0` | 1 | `{1.0, 2.0}` | 04_calibration:87 | MATCH (default ∈ set) |

`04_calibration.tex` è **clean (HEAD)**, quindi questa tabella non risente del WIP.

**Parametri del codice NON in `tab:params`** (fuori dal registro, per completezza):
`c1=0.9`, `capitalist_mpc=0.4`, `expectation_gain (λ_e)=1.0`,
`utilization_expectation_gain (λ_u)=1.0`, `productivity (A)=1.0`,
`productivity_spread=0.0`, `enable_prices=False`, `num_firms=10`,
`num_households=100`, `pct_capitalists=0.10`. Sono descritti in prosa/notazione
(es. `n_f=10`, `N=100`, `π_c=0.10` in `03_model:9`; `c1` "workers' above capitalists'"
in `03_model:122`); `λ_u` è il sito 7 (non dichiarato). Non hanno un valore numerico
in `tab:params` e quindi non entrano nel confronto tabellare.

---

## 4. Fase 2 — audit manuale delle 13 equazioni/sequenza

Classificazione: `OK` / `DIVERGENTE` / `DICHIARATO_ALTROVE` / `NON_DICHIARATO`.
Riferimento equazioni = **HEAD** (referente canonico); delta WIP segnalati.

| # | sito | `.tex` (HEAD) | codice | classe |
|---|---|---|---|---|
| 1 | CES normalizzata | `03_model:22–28` (eq:ces), `:31–34` | `agents.py:108–145` (`ces_capacity`), `:96–105` (`_Y0`), `:121–126` (ramo CD) | **OK** |
| 2 | soffitto `Y_max(K)` σ<1 / AK | `03_model:57–65` (AK), `:53–55` (3 regimi) | `agents.py:148–163` (`ces_capital_ceiling`), `model.py:612–614` (`Bound_Capital`) | **NON_DICHIARATO** (ceiling+4° regime) / OK (AK) |
| 3 | **FOC impresa** | `03_model:52–53`; probe `07_stress:72–77,149–153` | `agents.py:430` (`w=wage_rate/price if enable_prices else wage_rate`), `:442–444` | **OK** |
| 4 | `L=min{L_d,L_pm,N}` | `03_model:44–50` (eq:labour) | `agents.py:457` (`min`), `:458` (`int()`) | OK (min, cap N) / **NON_DICHIARATO** (floor intero) |
| 5 | wage curve | `03_model:76–81` (eq:wagecurve), `:82–87` | `model.py:300–317` (`wage_from_curve`), `:157` (U_REF), `:1239–1245` | **OK** |
| 6 | consumo `C_h=min{c0+c1y+λa, a+y}` | `03_model:118–121` (eq:consumption), `:122` | `agents.py:706–715`, `:683–684`, `:775–776` | OK / **NON_DICHIARATO** (guardia `max{·,0}`, `:715`) |
| 7 | acceleratore su `u^e` | `03_model:99–101` (eq:accelerator, **`u_{t-1}`**) | `agents.py:472–473` (legge `u^e`), `:560–562` (update `λ_u`), `model.py:880` (`λ_u=1`) | **NON_DICHIARATO** |
| 8 | `K'=(1-δ)K+I`, cap `I≤Π`, floor | `03_model:102–106` (eq:investment/eq:capital) | `agents.py:478–482` (`min(max(desired,floor),profit_last)`), `:644` (K') | **OK** (HEAD) + 2 note ↓ |
| 9 | governo | `08_fiscal:12–16,71`; `03_model:122–126` | `model.py:1163–1223` (`government`), `:1288–1293` (step 8) | **OK** |
| 10 | sequenza del periodo | `03_model:152–177` (alg:sequence) | `model.py:1226–1299` (`step`) | **OK** (nessuno step nuovo) |
| 11 | `productivity_spread` | `07_stress:214–284` | `model.py:276–297` (`productivity_fan`), `:943–945` | **OK** |
| 12 | `enable_prices` | `07_stress:72–108,149–160` | `model.py:563–572` (`compute_price`), `:821–830`, `:1253–1254` | **OK / DICHIARATO** |
| 13 | inventari (assenti) | `02_literature:20` (riga «Inventories»); `03_model:128–134` | assenti; `agents.py:648` (buffer→0) | **OK / DICHIARATO** |

### Dettaglio dei siti non-OK

**Sito 3 — FOC (rischio massimo): OK.** Il paper (`03_model:52–53`) dice
«`L_profitmax` is the point at which the marginal product of labour equals the
wage». Nel modello di default (numerario 1, `enable_prices=False`) il codice usa
`w = model.wage_rate = w_t` (`agents.py:430`, ramo `else`), che a `P=1` è **insieme**
il salario nominale e reale: `MPL = w_t` è la FOC al salario reale. La correzione
`af27915` (`w_t/P`) vive nel ramo `enable_prices=True`, ossia il **probe**,
esplicitamente descritto in `07_stress:72–77` («the real wage `w_t/P` stays at `w̄`»)
e `:149–153`. Il paper **non** afferma `w_t/P` nella sezione del modello, e non deve:
lì il modello è a `P=1`. **Nessuna divergenza.**

**Sito 7 — acceleratore: NON_DICHIARATO (inerte).** `eq:accelerator` scrive
`φ_t = max{0, 1+β(u_{t-1}−ū)}` con l'utilizzo **realizzato** `u_{t-1}`. Il codice
(`agents.py:472–473`) legge invece l'**aspettativa** `expected_utilization` (`u^e`),
aggiornata per aggiustamento parziale con gain `λ_u` (`agents.py:560–562`, b17).
A `λ_u=1` (default, `model.py:880`) `u^e = u_{t-1}` **bit-for-bit**; e **`λ_u` non è
sweepato in nessun risultato del paper** (la SA di `tab:sobol` sweepa δ,π₀,c₀,λ,σ — non
`λ_u`; grep: nessuna menzione di «expected utilisation»/`λ_u` in `paper/`). Quindi
l'equazione è **corretta come-eseguita**, ma la generalizzazione ad aspettativa con gain
è una **capacità del codice non dichiarata**. Non tocca nessun numero riportato.

**Sito 2 — quarto regime / ceiling: NON_DICHIARATO.** `eq:labour` elenca **3**
limiti (`L_demand`, `L_profitmax`, `N`) → 3 regimi (keynesiano, classico, piena
occupazione; `03_model:53–55`). Il codice ha un **quarto** `binding_constraint`,
`"capital"` (`agents.py:446–451`, `model.py:612–614`): per σ<1, quando la domanda
supera il soffitto `Y_max(K)` (`ces_capital_ceiling`, `agents.py:148–163`, **lineare
in K**), nessun `L` finito la raggiunge. Grep in `paper/`: nessuna menzione di
«capital ceiling»/`Y_max`/regime «capital». *Precisazione:* l'argomento **AK** del
`modelassumption` (`03_model:57–65`) poggia su `L_profitmax ∝ K` (σ≥1), che il codice
realizza in `ces_labour_profitmax`; è **dichiarato e OK**. Il ceiling σ<1 è un oggetto
distinto, non dichiarato.

**Sito 8 — investimento: OK su HEAD, con due note.**
- *(a) Regressione WIP (finding #1).* HEAD: `I^p_t = \clip(\rho\Pi_{t-1}\phi_t,
  \underline I, \Pi_t)` — `\clip` = `\DeclareMathOperator` in `preamble.tex:108`,
  rende «clip(...)», che è `min(max(·,floor),cap)` = il codice `agents.py:479–481`.
  **Working tree**: `\clip` rimosso ⇒ `(\rho\Pi_{t-1}\phi_t, \underline I, \Pi_t)`,
  una tupla senza operatore (matematicamente vuota). `preamble.tex` non è modificato,
  quindi non è un errore di build ma un **rendering silenziosamente sbagliato**.
- *(b) Pedice del cap.* Il paper cappa a `Π_t` (profitto **corrente**); il codice cappa
  a `self.profit_last_period = Π_{t-1}` (`agents.py:481`), perché `plan_investment` gira
  allo step 3, **prima** che il profitto corrente esista (accounting = step 6).
  **Immateriale**: in steady state `Π_t=Π_{t-1}` e ogni risultato è statica comparata.
- Il `floor` `I̲` è **DICHIARATO** («numerical guardrail», `04_calibration:69`).

**Sito 4 — floor intero: NON_DICHIARATO (immateriale).** `eq:labour` è a valori
reali; il codice prende `int(min(...))` (`agents.py:458`), cioè `floor` dell'headcount.
L'occupazione è un intero per natura; economicamente trascurabile. Il **cap N** è invece
**DICHIARATO** e prominente (`modelassumption`, `03_model:57–65`; asserito nei test).

**Sito 6 — guardia `max{·,0}`: NON_DICHIARATO (triviale).** `eq:consumption` scrive
`min{c0+c1y+λa, a+y}`; il codice antepone `max(target,0)` (`agents.py:715`) prima del
`min`. Guardia di non-negatività, mai un vero errore. Il vincolo di liquidità `min{·}`
(ereditato da Teglio) è **OK e dichiarato** («subject to a liquidity constraint»).

**Siti 1, 5, 9, 10, 11, 12, 13 — OK/DICHIARATO** (nessuna divergenza):
- **1** — nesting CD a σ=1 e `Y0` derivato dichiarati (`03_model:31–34`); il ramo
  byte-identico (`R_EPS=1e-6`, `agents.py:79`) è dettaglio di codice, non richiesto nel paper.
- **5** — wage curve, lag su `U_{t-1}`, `U_REF` congelato, `w_min`/`U_min` convenzioni,
  annidamento η=0: tutto dichiarato.
- **9** — governo a bilancio in pareggio *per costruzione* (base su `max(0,·)`,
  `model.py:1208`), cap `max_tax`, sussidio indicizzato a `w_t`: dichiarati (`08_fiscal`).
- **10** — la sequenza `alg:sequence` mappa 1:1 gli step 0–9 di `MacroModel.step`;
  lo step prezzo `0b` è il probe (off di default), correttamente **fuori** dalla sequenza
  core: **nessuno step nuovo**.
- **11** — ventaglio mean-preserving nelle **produttività** (=A), «no selection, no
  reallocation, no entry/exit»: dichiarato come *probe* (`07_stress:214–284`).
- **12** — `P_t=w_t/w̄`, salario reale, Pigou, «probe/upper bound/bracket»: dichiarato;
  numerario 1 = baseline; `enable_prices` assente dalla SA (`tab:sobol`), coerente con
  «fuori dalla SA».
- **13** — inventari **assenti**: dichiarato esplicitamente come semplificazione rispetto
  a Teglio nella tabella di confronto (`02_literature:20`, riga «Inventories»).

---

## 5. Fase 3 — copertura del registro, quantificata

**Copertura misurata adesso** (generatore committato `scripts/audit_b26_uncovered.py`,
CSV `results/audit_b26_uncovered.csv`):

- Registro `paper_claims.yaml`: **49 claim** (48 con referente in `paper/`; 1 solo-METHODOLOGY).
- Token del paper: **611 occorrenze decimali** (= sweep) + **415 intere** su 14 file;
  **423 token distinti**.
- Classificazione dei distinti:

| categoria | token distinti |
|---|---|
| COVERED_RESULT (registro) | 46 |
| COVERED_PARAM (b26, `verify_model`) | 15 |
| BLINDSPOT_1_DERIVED | 4 (`0.771, 538, 0.414, 477`) |
| BLINDSPOT_2_TABLE_NO_SOURCE | 1 (`59.4`, `tab:baseline`) |
| BLINDSPOT_3_SMALL_INT | 67 |
| BLINDSPOT_4_MEASURED_NO_CSV | 1 (`569`) |
| STRUCTURAL (n_f, N, step, seed…) | 16 |
| LITERATURE_OR_DESIGN (coda lunga: citazioni, range, anni) | 273 |

*Nota sui bucket coarse:* `BLINDSPOT_3_SMALL_INT` (67) è un **over-count** deliberato —
vi cade **ogni** intero non-strutturale non nel registro (molti sono prosa innocua); è
una classificazione di «non coperto dal registro», **non** un'affermazione che siano
errori. `LITERATURE_OR_DESIGN` (273) è il bucket «non è un errore» dello sweep
(valori bibliografici, range empirici, target di design). L'attribuzione vive **solo**
nel registro; la prossimità non è attribuzione (regola §5 / brief 19).

### 5.1 Falsi positivi noti — verificati ANCORA tali, NON corretti

- **`0.771`** (§9, `tab:marginalturn`) = **1230/1596 = 0.770677**, round-once 0.771:
  **il paper è corretto**; l'abbinamento a `ces_b07_sigma_star_by_rho/ci_hi` è
  coincidenza (numero **derivato**, punto cieco #1). Classificato `BLINDSPOT_1_DERIVED`.
- **`59.4`** ×2 (§6, `tab:baseline`): **non attribuito** — la sorgente di `tab:baseline`
  non è fra gli artifact inclusi (punto cieco #2). Classificato `BLINDSPOT_2_TABLE_NO_SOURCE`.

Entrambi presenti nel paper e lasciati **intatti** (correggerli sarebbe il movimento di
`667003b`).

### 5.2 Retrofit a generatore — PROPOSTI, non eseguiti (ordine di costo)

1. **`tab:wagecurve`** — referente **identificato** (`ces_b07_sigma_star.csv`,
   `target=Y`, `across_eta`, `n_crossings=2` a η=0.10 **e** 0.15): candidato ovvio a
   basso costo (regola §5, raffinamento b22).
2. **`tab:delta`** — chord-vintage, **blocco coerente** (821/843, 0.992/0.758/0.183,
   P(wl) 0.044/0.111/0.313 + figura `ces_b13` + prosa OLS): tabella, figura e prosa si
   aggiornano **insieme** o non si toccano.
3. **`tab:marginalturn`** — dopo `tab:wagecurve`.
4. **`tab:baseline`** — va **prima dotata di un referente** (oggi `59.4` è senza
   sorgente inclusa): altrimenti non c'è niente da generare.

**Non fatto** (vietato dal brief): non ho affinato `sweep_rounding.py` per catturare i
derivati; la copertura si estende **col registro**, non con un detector più furbo.

---

## 6. Debiti che questo audit NON chiude (riportati per intero)

- **Pin 8 ULP** — `ok=False` su b05/b07/b09 per solo drift d'ambiente (max dev
  7.6e-11 su `Total_Capital`): non toccato.
- **Notebook** — b14 + i due aperti da b17 e b21: non toccati.
- **Generatori tabelle** — `tab:delta`, `tab:baseline`, `tab:marginalturn` restano
  **senza** generatore (proposte in §5.2, non eseguite).
- **`RESULTS.md` untracked** — presente su disco (coherence lo legge), non tracciato in
  git: debito dichiarato, invariato.
- **Controllo off di σ\*(η)** — non risolto a 12 seed, 2 crossing a η≥0.10
  (`tab:prices`, colonna *off*): resta un bracket, non un verdetto.
- **Inconsistenza di rounding nella toolchain (osservazione b26, non un difetto da
  chiudere qui):** `verify_paper.py` usa `round()` builtin (banker's/half-even);
  `sweep_rounding.py` e il nuovo `verify_model.py` usano `Decimal`+`ROUND_HALF_UP`.
  **Immateriale** sui valori attuali (nessun caso half-way fra i parametri/claim), ma
  latente. Segnalato, non riparato.
- **WIP `paper/` non committato (§0.1)** — inclusa la regressione `\clip` di
  `eq:investment`: **fuori scope** (paper intoccabile), da risolvere quando Mattia
  committa il WIP; Fase 1 e Fase 2 vanno rieseguite allora.

---

## 7. Deliverable e verifica dei criteri di accettazione

- [x] `scripts/verify_model.py` committato; `--selftest` **FALLISCE netto** su default
  alterato (output in §3).
- [x] `results/audit_b26_params.csv` (gen. `verify_model.py`) e
  `results/audit_b26_uncovered.csv` (gen. `scripts/audit_b26_uncovered.py`) committati,
  **ognuno col proprio generatore**.
- [x] `docs/audit_b26_paper_codice.md` (questo file): 13 siti di Fase 2 **tutti
  classificati** (nessuno vuoto).
- [x] `git diff --stat -- paper/ src/` per la parte **mia** = **0** (l'unico contenuto
  sotto `paper/` è il WIP ereditato §0.1, che NON ho toccato; `src/` = clean).
- [x] `pytest -q` invariato: **569** (nessun test aggiunto; `src/` non toccato).
- [x] Record in `METHODOLOGY.md` §8 (invariante b22-ter): registrato con questo brief.
- [x] **Commit locale, STOP pre-push.** Nessun push senza conferma esplicita di Mattia.
