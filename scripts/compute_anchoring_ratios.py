#!/usr/bin/env python
"""Compute the investment and capital ratios quoted in the brief-11 anchoring notes.

Brief 11 closes three anchoring debts (time unit, I/Y against BEA, ``c0``).  Two of them
quote MODEL ratios -- I/Y and K/Y at the two reference cells -- which until now existed
only inside prose.  Rule 5 of ``CLAUDE.md`` says every number in a document is either
measured with a reproducible generator or declared a design target; this script is the
generator for those two, so the ratios stop being hand-transcribed.

**No simulation is run.**  It reads the committed 20-seed panels and reduces them:

* ``results/ces_b05_stage_a_panel.csv``  -> **anchor**   cell (c0 = 2.0, sigma = 1, eta = 0)
* ``results/ces_b07_stage_a_panel.csv``  -> **headline** cell (c0 = 1.0, sigma = 0.5,
  eta = 0.10)

Declared reduction (stated because other conventions are defensible and would give
slightly different numbers): the panel row is already a per-seed tail-50 steady-state
average, so the ratio is formed **per seed and then averaged over the 20 seeds** --
``mean_s(Investment_s / Output_s)``, ``mean_s(Total_Capital_s / Output_s)``.  This is a
mean of ratios, not a ratio of means; at these cells the two agree to ~1e-3, but the
convention is fixed here rather than left implicit.  Collapsed seeds (Output = 0) would
make the ratio undefined; they are counted in ``n_dropped`` and excluded, and neither
reference cell has any.

The rho sweep is emitted alongside rho = 0.40 because the empirical match of I/Y is
rho-dependent -- that dependence is the finding, not a footnote, and the brief-11 note in
``parameter_notes.md`` cites the rho that centres the BEA band from this table.

Deterministic by construction: it is a groupby over committed CSVs, with no RNG, no
simulation and no parallelism.  It is therefore NOT covered by the pytest suite (438
tests, unchanged by brief 11) -- there is no model behaviour here to pin.

Usage
-----
    python scripts/compute_anchoring_ratios.py        # -> results/ces_b11_anchoring_ratios.csv
    python scripts/compute_anchoring_ratios.py --print-only   # stdout, write nothing
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_RESULTS = os.path.join(_ROOT, "results")

OUT_CSV = os.path.join(_RESULTS, "ces_b11_anchoring_ratios.csv")

# Reference cells.  Both are the scenarios every brief since 07 reports against: the
# "anchor" is the normalisation scenario the ANCHOR_* / U_REF constants were measured at,
# the "headline" is the empirically-motivated cell (sigma in the Chirinko band, eta at the
# Blanchflower-Oswald elasticity).
SCENARIOS = (
    # label, panel file, filter on the panel columns
    ("anchor", "ces_b05_stage_a_panel.csv", {"c0": 2.0, "sigma": 1.0}),
    ("headline", "ces_b07_stage_a_panel.csv", {"c0": 1.0, "sigma": 0.5, "eta": 0.10}),
)

RHO_REFERENCE = 0.40  # the retention every brief since 09 reports its reference cell at


def _load(panel_file: str) -> pd.DataFrame:
    path = os.path.join(_RESULTS, panel_file)
    if not os.path.exists(path):
        raise SystemExit(
            f"missing panel {path!r} -- regenerate it with the brief driver that owns it "
            "(scripts/run_brief05.py or scripts/run_brief07.py)"
        )
    return pd.read_csv(path)


def _ratios(df: pd.DataFrame, label: str, where: dict) -> pd.DataFrame:
    sel = df
    for col, val in where.items():
        if col not in sel.columns:
            raise SystemExit(f"panel for {label!r} has no column {col!r}")
        sel = sel[sel[col] == val]
    if sel.empty:
        raise SystemExit(f"no rows for scenario {label!r} with {where}")

    rows = []
    for rho, grp in sel.groupby("rho", sort=True):
        n_total = len(grp)
        live = grp[grp["Output"] > 0.0]  # a collapsed seed leaves I/Y and K/Y undefined
        if live.empty:
            continue
        iy = live["Investment"] / live["Output"]
        ky = live["Total_Capital"] / live["Output"]
        rows.append(
            {
                "scenario": label,
                **where,
                "rho": rho,
                "n_seeds": n_total,
                "n_dropped": n_total - len(live),
                "I_over_Y": iy.mean(),
                "I_over_Y_sd": iy.std(ddof=1),
                "K_over_Y": ky.mean(),
                "K_over_Y_sd": ky.std(ddof=1),
                # closure of the model's steady state: with no trend growth, I = delta*K,
                # so I/K should sit at delta = 0.05.  Reported, not assumed: it is the
                # quantity that makes K/Y = (I/Y)/delta a mechanical consequence.
                "I_over_K": (live["Investment"] / live["Total_Capital"]).mean(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print-only", action="store_true", help="print, do not write the CSV")
    args = ap.parse_args()

    tables = []
    for label, panel_file, where in SCENARIOS:
        tables.append(_ratios(_load(panel_file), label, where))
    out = pd.concat(tables, ignore_index=True)

    # Columns differ across scenarios (only the b07 panel carries eta); make the union
    # explicit so the CSV has a stable, readable schema.
    lead = ["scenario", "c0", "sigma", "eta", "rho", "n_seeds", "n_dropped"]
    cols = [c for c in lead if c in out.columns] + [c for c in out.columns if c not in lead]
    out = out[cols]

    pd.set_option("display.width", 200)
    print("Anchoring ratios (mean over seeds of the per-seed tail-50 ratio)\n")
    for label, _, _ in SCENARIOS:
        ref = out[(out["scenario"] == label) & (out["rho"] == RHO_REFERENCE)]
        if not ref.empty:
            r = ref.iloc[0]
            print(
                f"  {label:>8s}  rho={RHO_REFERENCE:.2f}   "
                f"I/Y = {r['I_over_Y']:.3f}   K/Y = {r['K_over_Y']:.2f}   "
                f"I/K = {r['I_over_K']:.4f}"
            )
    print("\nFull rho sweep:\n")
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    if args.print_only:
        return
    out.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {os.path.relpath(OUT_CSV, _ROOT)}")


if __name__ == "__main__":
    main()
