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
