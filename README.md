# Endogenous Investment and Capital Accumulation

*A normalised-CES agent-based model with an endogenous labour market, extending
the disaggregated Keynesian cross of Teglio (2025).*

[![Build paper](https://github.com/MattiaSaramin/endogenous-investment-abm/actions/workflows/paper.yml/badge.svg)](https://github.com/MattiaSaramin/endogenous-investment-abm/actions/workflows/paper.yml)

## Abstract

We extend Teglio (2025)'s disaggregated Keynesian cross with endogenous
investment and capital accumulation. Production is a *normalised* CES with
elasticity of substitution `sigma`; firms hire endogenously, the wage follows a
Blanchflower–Oswald curve, and the model is stock-flow-consistent throughout.
Whether higher retention `rho` builds capacity (supply) or displaces workers
(demand) is an outcome, not an assumption. Three results, a U-shaped `Y(rho)`
with a sign frontier `sigma* ≈ 0.65`, a wage-led region that fiscal institutions
can remove, and a wage → unemployment → capital-erosion fragility immune to
demand instruments, are separated from what does not generalise by a
sixteen-parameter global sensitivity analysis. It is an exploratory
computational laboratory for *qualitative* macroeconomics, not a calibrated
forecast.

The full write-up is in [`paper/`](paper/). There is no local TeX engine, so the
compiled PDF is built **only in CI**: download it as the `paper-pdf` artifact of
the latest [**Build paper**](https://github.com/MattiaSaramin/endogenous-investment-abm/actions/workflows/paper.yml)
run.

## Install

Python 3.11+ with [Mesa](https://mesa.readthedocs.io/). One command:

```bash
python -m pip install -r requirements.txt
```

## Quickstart

Runs in a few seconds and returns a per-seed pandas `DataFrame` of steady-state
aggregates:

```python
import sys; sys.path.append("src")
from experiment import run_experiment, retention_sweep, sigma_rho_sweep

panel = run_experiment(retention_ratio=0.40, steps=2000, seeds=3)  # multi-seed panel
sweep = retention_sweep([0.35, 0.40, 0.50, 0.60])                  # steady state vs rho (sigma=1)
grid  = sigma_rho_sweep()                                          # the (sigma, rho) sign frontier
```

## Reproducing the results

Every figure and table is regenerated from a committed driver into `results/`.
The drivers pin BLAS threads (`OMP_NUM_THREADS=1` etc.) for reproducibility, so
**do not** re-parallelise them. **Some sweeps take hours**, the ones below are
labelled; the notebook itself reads committed CSVs rather than re-simulating.

| Driver | Regenerates | Cost |
|---|---|---|
| `notebooks/01_Endogenous_Investment.ipynb` | all figures/analysis (reads committed CSVs; two small live sweeps) | ~2 min |
| `scripts/run_brief05.py` | brief-05 robustness stack (`ces_b05_*`) | minutes |
| `scripts/run_brief07.py` | wage-curve sweep (`ces_b07_*`) | minutes |
| `scripts/run_brief08.py` | adaptive-expectations sweep (`ces_b08_*`) | minutes |
| `scripts/run_brief09.py` | government sweep (`ces_b09_*`) | ~1.5–2 h |
| `scripts/run_brief10.py` | heterogeneity probe (`ces_b10_*`) | ~10 min |
| `scripts/compute_anchoring_ratios.py` | brief-11 anchoring ratios (no simulation) | ~1 s |
| `scripts/run_brief13.py --phase {pilot,morris,sobol,wide,report}` | global SA | up to ~2.2 h/phase |
| `scripts/run_brief14.py --phase {bridge,morris,sobol,wide}` | QoI repair + redone SA | up to ~4.7 h/phase |

```bash
python scripts/run_brief05.py                    # example: one live sweep
python scripts/run_brief13.py --phase report     # analysis + figures only, no simulation
```

## Verification

Numbers are not trusted by eye , three committed checkers keep the paper, the
documents and the code in agreement, and are the distinctive feature of this
repository:

```bash
python scripts/verify_paper.py    # every paper number vs its source CSV in results/
python scripts/coherence.py       # the same headline number agrees across README / paper / notebook
python -m pytest tests/ -q        # 569 tests: SFC, money conservation, CES nesting, wage curve, government, ...
```

`verify_paper.py` reads `scripts/paper_claims.yaml` and matches each claim
against its committed artifact; `coherence.py` cross-checks the shared headline
numbers between documents (it tolerates the deliberately-untracked `RESULTS.md`
as a declared debt). Both exit non-zero on a real mismatch.

## Repository structure

```text
src/          CES firm, household, capitalist agents; MacroModel; Monte-Carlo experiment runner
scripts/      reproducible brief drivers (run_brief*.py), the verifiers, table generators
tests/        569 pytest checks (accounting invariants, nesting, behaviour)
results/      committed measured CSVs, one family per brief (ces_b*_*.csv)
paper/        LaTeX source (main.tex + sections/); the PDF is a CI artifact, not tracked
notebooks/    01_Endogenous_Investment.ipynb , the narrative analysis
docs/         project_log.md , a frozen snapshot of the old diary-style README
METHODOLOGY.md   the process: briefs, decisions, debts, lessons
parameter_notes.md   per-parameter source, estimate, range and anchoring verdict
```

The paper PDF is **not** committed: with no local TeX engine it would only drift
behind `paper/`. Get the current PDF from the `paper-pdf` CI artifact (above).
`performance/engine.cpp` is an inherited Phase-1 C++ engine that has **not** been
ported to the CES core and must not be used for results.

## How to cite

See [`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this repository"
button from it).

## License

[MIT](LICENSE) © 2026 Mattia Saramin. Covers the code, data and paper source.

## Further documentation

* **[`METHODOLOGY.md`](METHODOLOGY.md)**, the current source of truth on the
  process: what each brief did, the decisions taken, and the standing debts.
* **[`docs/project_log.md`](docs/project_log.md)**, a frozen historical
  snapshot of the previous, long-form README. Kept for the record; not
  maintained.
