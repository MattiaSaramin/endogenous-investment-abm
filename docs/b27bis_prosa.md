# Brief 27-bis — prosa scientifica: re-read umane e mappe di conversione

Referto delle fasi che **nessun detector vede** (famiglia del punto cieco #4):
la rilettura umana degli em-dash→virgola (Fase 2), la mappa `\item`→frase delle
liste (Fase 3), e i siti di enfasi riformulati (Fase 4). Branch `b27-verify`.

---

## Fase 2 — rilettura dei 123 em-dash → virgola (commit `b80a0fe` del b27)

Riletti tutti i **147 siti** di em-dash del paper pre-de-dash (`7d51532`; 147 conta
i due trattini di ogni coppia parentetica separatamente). La grande maggioranza è
**appositiva o parentetica** e legge correttamente come virgola (es. «$\rhostar$, the
argument minimum, inside the swept support»; «a mechanism, trend productivity growth,
not a calibration»): **lasciati intatti**.

**Problemi identificati e corretti — 8 comma splice** (l'em-dash univa due proposizioni
indipendenti senza congiunzione; la virgola produce uno splice). Regola: due punti dove
la seconda proposizione **elabora** la prima, punto e virgola dove è una **coordinata**
indipendente.

| # | file:riga | prima (splice) | dopo | fix |
|---|---|---|---|---|
| 1 | `01_introduction:28` | «shows this directly, holding the numéraire fixed is itself a convention» | «…directly**:** holding…» | due punti (elaborazione) |
| 2 | `02_literature:13` | «rather than asserted, \cref{sec:heterogeneity} shows…» | «…asserted**:** \cref…» | due punti |
| 3 | `03_model:96` | «from retained earnings, there is no credit» | «…earnings**;** there is no credit» | punto e virgola |
| 4 | `07_stress:29` | «result survives, $\sigma=1$ stays above the frontier» | «…survives**;** $\sigma=1$ stays…» | punto e virgola |
| 5 | `08_fiscal:82` | «in 100\% of periods, the instrument saturates…» | «…periods**;** the instrument saturates…» | punto e virgola |
| 6 | `10_discussion:91` | «in any measurement, it was an error in our own prose» | «…measurement**;** it was an error…» | punto e virgola |
| 7 | `a_validation` | «$0.00$ ULP, it reproduces exactly today» | «…ULP**;** it reproduces…» | punto e virgola |
| 8 | `a_validation:147` | «stand in for the measurement, both displacements push the same way» | «…measurement**;** both displacements…» | punto e virgola |

**Casi valutati e LASCIATI** (non splice, contrariamente a una prima impressione):
- `01_introduction:30` «shows that the frontier does not survive marginalization, viability
  is governed…, and … no sampled configuration remains viable» — è una **serie di tre
  that-clause** («shows that A, B, and C»), grammaticale; la virgola A→B è seriale, non
  uno splice.
- I siti dentro le liste `enumerate` (`10_discussion`, `07_stress`, `11_limitations`) sono
  gestiti dalla **Fase 3** (la riscrittura in prosa li assorbe), non qui.

Nessun numero toccato dalle 8 correzioni (solo punteggiatura); `verify_paper.py` invariato.

---

## Fase 3 — liste (8) → prosa. Mappa `\item` → frase (nessuna proposizione persa)

**0 `itemize` / 0 `enumerate`** in `sections/` + `appendices/` dopo la fase; token
decimali **611** invariati; `verify_paper` 0 FAIL. Nessun `\label` era dentro una lista
(nessun `\cref` a un `\item` da rompere). Il `\item` di `04_calibration:90` resta: è una
nota di `tablenotes`, non una lista. Le liste con numerazione **referenziata** conservano
i numeri: `04` (tier), `07` (step).

| lista | file | `\item` (prima) | corrispettivo in prosa | note |
|---|---|---|---|---|
| 1 | `01_introduction` | Supply: … raises output | «On the supply side, … taken alone, this raises output.» | label→frase |
| 1 | `01_introduction` | Demand: … demand falls with it | «On the demand side, … demand falls with it.» | label→frase |
| 2 | `03_model` | \textbf{Nesting.} … any base point | «\textbf{Nesting.} … for any base point.» | run-in, invariato |
| 2 | `03_model` | \textbf{Comparability.} … not an estimate | «\textbf{Comparability.} … not an estimate.» | run-in, invariato |
| 3 | `04_calibration` | (1) Anchored … this tier | «\textbf{(1) Anchored.} … in this tier.» | **numero (1) conservato** (referenza «tier (2)») |
| 3 | `04_calibration` | (2) Declared convention … consequential case | «\textbf{(2) Declared convention.} … consequential case.» | **numero (2) conservato** |
| 3 | `04_calibration` | (3) Non-anchorable … by choosing | «\textbf{(3) Non-anchorable by decision.} … by choosing.» | **numero (3) conservato** |
| 4 | `06_shape` | \textbf{The empirical range sits below…} | «\textbf{The empirical range sits below the frontier.} …» | + `$0.31$-$0.45$`→`--`, `$0.3$-$0.7$`→`--` (range mancati in Fase 1) |
| 4 | `06_shape` | \textbf{Unemployment has a different frontier.} | «\textbf{Unemployment has a different frontier.} …» | run-in |
| 5 | `07_stress` | (1) the wage oscillates… | «(1) the wage \emph{oscillates}, …» | **numero (1) conservato** (referenza «step (2)») |
| 5 | `07_stress` | (2) as σ rises… employment oscillation | «(2) as $\sigma$ rises, … \emph{employment} oscillation;» | **numero (2) conservato** |
| 5 | `07_stress` | (3) each cycle… dies at U=1 | «and (3) each cycle, … dies at $U = 1$.» | **numero (3) conservato** |
| 6 | `10_discussion` | slower demand expectations… they did not | «slower demand expectations …, **but** they did not;» | +`but` (fissa splice) |
| 6 | `10_discussion` | demand floor… it enlarged it | «a balanced-budget demand floor …, **but** it \emph{enlarged} it, …;» | +`but` |
| 6 | `10_discussion` | benefit… it lowered threshold | «and that same benefit …, **but** it \emph{lowered} the viability threshold.» | +`but` |
| 7 | `11_limitations` | No growth… | «\textbf{No growth, …} With $g = 0$, …» | run-in (paragrafo) |
| 7 | `11_limitations` | Unemployment out of scale | «\textbf{Unemployment is out of scale.} … genuine lever here**:** it lowers …» | + `:` (fissa splice site 121) |
| 7 | `11_limitations` | Wage share below range | «\textbf{The wage share sits below its empirical range} ($0.35$--$0.61$ … $0.60$--$0.68$) …» | invariato |
| 7 | `11_limitations` | Multiple equilibria | «\textbf{Multiple equilibria.} … an \emph{outcome}, not an error.» | run-in |
| 7 | `11_limitations` | No reallocation | «\textbf{No reallocation, so no genuine heterogeneity.} …» | run-in |
| 7 | `11_limitations` | No credit / prices / numéraire | «\textbf{No credit, no endogenous prices, …} …» | run-in (invariato) |
| 7 | `11_limitations` | Sampling limits (4.3\%, N=256) | «\textbf{Sampling limits in the global analysis.} … 4.3\% … $N = 256$ …» | invariato |
| 7 | `11_limitations` | Turning point unresolved (37.7\%, 58.7\%) | «\textbf{The turning point is often unresolved marginally.} … $37.7\%$ … $58.7\%$ …» | invariato |
| 7 | `11_limitations` | Two estimates (0.96, σ≈1) | «\textbf{Two estimates of the marginalised frontier, not one.} … $\sigstar \approx 0.96$ … agree in message**:** the marginalised frontier …» | + `:` (fissa splice site 124) |
| 8 | `a_validation` | A contradiction that did not exist | «\textbf{A contradiction that did not exist.} … a reading error**;** its method axis …» | + `;` (fissa splice site 140) |
| 8 | `a_validation` | An inverted label | «\textbf{An inverted label.} … states it correctly.» | run-in |
| 8 | `a_validation` | A stale identity | «\textbf{A stale identity.} … Both are withdrawn.» | run-in |

Nessuna proposizione nuova; ogni numero conservato (611 = 611). I `\textbf`/`\emph`
run-in restano per la **Fase 4** (l'enfasi si rimuove lì, in blocco).

---

## Fase 4 — rimozione dell'enfasi (\textbf 65 / \textit 7 / \emph 133 → 0/0/0)

**Conteggio finale in `sections/` + `appendices/`: 0 `\textbf`, 0 `\textit`, 0 `\emph`**
(+ 0 `\mathbf`, rimosso anch'esso: era grassetto in una tabella, e il gate §1 ha deciso
«niente grassetto, tabelle incluse»).

**Titoli di paragrafo in linea → `\paragraph` (rule 1, 19 conversioni).** I `\textbf`
usati come titolo run-in non si cancellano: diventano `\paragraph{...}` (stile deciso
dalla classe). Convertiti: `03_model` (Nesting, Comparability), `04_calibration` (le 3
tier, numero conservato), `06_shape` (2 letture), `11_limitations` (9 limiti),
`a_validation` (3 correzioni). *Nota:* il pattern «First/Second/Third» di `01_introduction`
era **già** in prosa piana (il WIP del b27 aveva tolto il `\textbf`), quindi non richiede
conversione — la segnaletica (le parole «First/Second/Third») resta.

**Blocco generato (gate §1, Opzione A).** `make_tab_sobol.py` **modificato** per non
emettere `\textbf` (rimosso il set `BOLD` e il ramo in `format_cell`); rigenerato; il blocco
inline di `tab:sobol` (`09_sensitivity`) sostituito con l'output nuovo e **verificato
byte-identico**. `tab:prices` non aveva grassetto. Le 8 celle grassetto a mano
(`tab:repaired`, `tab:delta`, `tab:heterogeneity`, `04_calibration`, `a_validation`) sono
state de-grassettate (unwrap).

**Enfasi che «portava significato» → riformulata nel lessico (rule 2): 0 siti.** Riletti i
133 `\emph` (con attenzione ai contrasti). In **ogni** caso il contrasto è già portato dalle
parole intorno, non dal markup, quindi togliere `\emph` **non indebolisce** la frase:
- «demand is destroyed **rather than** reallocated» (07) — la porta «rather than»;
- «quasi-representative in its aggregates, **not** in its cross-section» (07) — la porta «not»;
- «a turn is resolved **only if** …» (09) — la porta «only if»;
- «**not** the position of the frontier **but** the anchored margin» (10) — la porta «not…but»;
- verbi enfatici di direzione («output falls, from $96.7$ to $86.8$»; «it enlarged it»,
  con il «but» aggiunto in Fase 3) — li portano i numeri e le congiunzioni.
Nessuna riformulazione necessaria: la prosa del paper porta il significato nelle parole.

**Detector dopo la fase:** `verify_paper.py` **0 FAIL, 0 CLAIM NOT FOUND** (togliere
`\textbf{0.718}`→`0.718` ecc. **non** ha scollegato alcun `context`); `make_tab_sobol`/
`make_tab_prices` byte-identici; token decimali **611**; `coherence` 0 DIVERGENT;
`verify_model` 19 MATCH.
