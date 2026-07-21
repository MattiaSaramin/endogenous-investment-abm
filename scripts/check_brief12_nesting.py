#!/usr/bin/env python
"""Brief 12: verify that the ownership fix leaves the DEFAULT model bit-for-bit unchanged.

Brief 12 changes how firm ownership is assigned: by cycling over the FIRMS instead of the
households, so every firm has exactly one owner at any ``pct_capitalists``.  At the
default (100 x 0.10 = 10 capitalists, 10 firms) ``j % 10 == j``, so firm ``j`` is owned by
capitalist ``j`` — **exactly** the old household-indexed assignment.  The claim is
therefore that no committed result moves at all, and this script is what makes that claim
falsifiable instead of asserted.

It is NOT a driver: it produces no new science and regenerates no committed panel.  It
re-runs a **slice** of the committed panels with the current code and compares the
regenerated rows against the committed ones, artifact vs artifact.  A slice, not the whole
panel, because the whole set is ~28 000 cells (hours) while the nesting claim is
mechanical — one representative cell per reference already falsifies it if it is wrong.
The slice is declared in :data:`REFERENCES` and covers, across the four references, both
``c0`` regimes, ``eta`` on and off, the government on and off, and the brief-10 dispersion
dial on and off.

Artifact vs artifact (the brief-07 discipline): both frames are read back from disk and
compared as CSV text, because pandas ``to_csv`` is not perfectly round-trip-lossless.

**The pass criterion changed in brief 14 (task D), and this script is where the new
baseline is fixed.**  Briefs 07-13 required ``max_abs_dev == 0.0``.  Brief 13 §7.3(a) then
measured that exact byte equality is not reproducible across time — the code at
``7c2670f``, whose own check reported *7/7 PASS, dev = 0.0*, deviates by up to 2.1 ULP
from its own committed results when re-run later, cause unidentified, **zero regime
flips**.  A criterion that the unmodified code fails is not a criterion.

It is replaced by :func:`experiment.compare_artifacts`: a declared numerical tolerance
(:data:`experiment.BYTE_CHECK_ULP` = 8 ULP with an absolute floor) on the levels, AND a
regime check at tolerance **exactly zero** — viability, which constraint binds, and the
sign of every resolvable metric must match exactly.  The retired ``byte_equal`` is still
computed and written to the CSV, so the change of standard stays visible rather than
quietly disappearing from the artifacts.  A FINDING on either limb still stops the work.

Determinism: BLAS pinned to one thread before numpy is imported (below); the simulation
path is thread-invariant, and every cell is seeded and shares no state, so the pooling
cannot move a result.

Usage
-----
    python scripts/check_brief12_nesting.py               # ~440 cells
    python scripts/check_brief12_nesting.py --workers 1   # serial (slow)
"""

from __future__ import annotations

import argparse
import os
import sys

# Make ``src/`` importable here AND in the process-pool children (Windows spawns fresh
# interpreters that re-import experiment/model and only inherit sys.path via the env).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported (here via pandas/experiment).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    BYTE_CHECK_ATOL,
    BYTE_CHECK_ULP,
    _PANEL_METRICS,
    compare_artifacts,
    run_grid_panels,
)

RESULTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

#: The committed panels were run at 2000 steps with a 50-period tail and 20 seeds.  These
#: must match the committed convention exactly or the comparison is meaningless.
STEPS, TAIL, SEEDS = 2000, 50, 20

#: The slice.  ``sigma`` = 1.0 (Cobb-Douglas) and 0.5 (the empirical centre and the
#: headline scenario); ``rho`` at both ends of the committed sweep.  brief-10 rows exist
#: only at rho = 0.40 and one sigma per scenario, so they carry their own grid.
SIGMAS, RHOS = [0.5, 1.0], [0.40, 0.65]

#: One entry per regenerated configuration: the committed panel it must reproduce and the
#: (c0, eta, rr, spread) selector that isolates its rows there.
REFERENCES = [
    dict(name="b05_c0=1.0", ref="ces_b05_stage_a_panel.csv",
         sel=dict(c0=1.0), params=dict(c0=1.0),
         sigmas=SIGMAS, rhos=RHOS),
    dict(name="b05_c0=2.0", ref="ces_b05_stage_a_panel.csv",
         sel=dict(c0=2.0), params=dict(c0=2.0),
         sigmas=SIGMAS, rhos=RHOS),
    dict(name="b07_c0=1.0,eta=0.10", ref="ces_b07_stage_a_panel.csv",
         sel=dict(c0=1.0, eta=0.10), params=dict(c0=1.0, eta=0.10),
         sigmas=SIGMAS, rhos=RHOS),
    dict(name="b07_c0=2.0,eta=0.15", ref="ces_b07_stage_a_panel.csv",
         sel=dict(c0=2.0, eta=0.15), params=dict(c0=2.0, eta=0.15),
         sigmas=SIGMAS, rhos=RHOS),
    dict(name="b09_c0=1.0,eta=0.10,rr=0.5", ref="ces_b09_stage_a_panel.csv",
         sel=dict(c0=1.0, eta=0.10, benefit_replacement_rate=0.5),
         params=dict(c0=1.0, eta=0.10, benefit_replacement_rate=0.5),
         sigmas=SIGMAS, rhos=RHOS),
    # brief 10: the dispersion dial ON, i.e. the one path where firms differ and the
    # ownership cycle could in principle interact with which firm dies first.
    dict(name="b10_S2_headline,spread=0.20", ref="ces_b10_panel.csv",
         sel=dict(c0=1.0, eta=0.10, benefit_replacement_rate=0.0, spread=0.20),
         params=dict(c0=1.0, eta=0.10, productivity_spread=0.20),
         sigmas=[0.5], rhos=[0.40]),
    dict(name="b10_S3_benefit,spread=0.125", ref="ces_b10_panel.csv",
         sel=dict(c0=1.0, eta=0.10, benefit_replacement_rate=0.5, spread=0.125),
         params=dict(c0=1.0, eta=0.10, benefit_replacement_rate=0.5,
                     productivity_spread=0.125),
         sigmas=[0.5], rhos=[0.40]),
]

ORDER = ["sigma", "rho", "seed"]


def regenerate(workers):
    """Run every slice with the CURRENT code and write it to disk.

    Grouped by (sigmas, rhos) so configs sharing a grid share one process pool — the
    single-pool discipline of brief 08.  Returns the path of the written artifact.
    """
    frames = []
    groups = {}
    for i, r in enumerate(REFERENCES):
        groups.setdefault((tuple(r["sigmas"]), tuple(r["rhos"])), []).append(i)

    for (sigmas, rhos), idx in groups.items():
        cfgs = [REFERENCES[i]["params"] for i in idx]
        print(f"  pool sigmas={list(sigmas)} rhos={list(rhos)}: {len(cfgs)} configs "
              f"x {len(sigmas) * len(rhos)} cells x {SEEDS} seeds")
        panels = run_grid_panels(cfgs, sigmas=list(sigmas), rhos=list(rhos), seeds=SEEDS,
                                 steps=STEPS, tail=TAIL, workers=workers,
                                 metrics=list(_PANEL_METRICS))
        for i, panel in zip(idx, panels):
            frames.append(panel.assign(config=REFERENCES[i]["name"]))

    out = pd.concat(frames, ignore_index=True).sort_values(
        ["config"] + ORDER, ignore_index=True)
    path = os.path.join(RESULTS, "ces_b12_nesting_slice.csv")
    out.to_csv(path, index=False)
    print(f"  wrote {path}  ({len(out)} rows)")
    return path


def byte_check(slice_path):
    """Compare the regenerated slice against the committed panels, artifact vs artifact."""
    mine_all = pd.read_csv(slice_path)

    rows, all_ok = [], True
    print("\n  nesting check (regenerated slice vs committed panels, artifact vs artifact):")
    for r in REFERENCES:
        ref_path = os.path.join(RESULTS, r["ref"])
        if not os.path.exists(ref_path):
            all_ok = False
            rows.append({"config": r["name"], "ref": r["ref"], "byte_equal": False,
                         "max_abs_dev": float("nan"), "n_rows": 0,
                         "note": "reference not found"})
            print(f"    {r['name']}: {r['ref']} NOT FOUND  <-- FINDING")
            continue

        ref = pd.read_csv(ref_path)
        for col, val in r["sel"].items():
            if col not in ref.columns:
                # A reference that predates the column: the committed run had it at its
                # default, so the selector is vacuous there.  Declared, not silent.
                print(f"      note: {r['ref']} has no column '{col}' (pre-dates it)")
                continue
            ref = ref[ref[col] == val]
        ref = ref[ref["sigma"].isin(r["sigmas"]) & ref["rho"].isin(r["rhos"])]

        mine = mine_all[mine_all["config"] == r["name"]]
        shared = [c for c in ref.columns if c in mine.columns]
        a = mine[shared].sort_values(ORDER).reset_index(drop=True)
        b = ref[shared].sort_values(ORDER).reset_index(drop=True)
        if a.shape != b.shape:
            all_ok = False
            rows.append({"config": r["name"], "ref": r["ref"], "byte_equal": False,
                         "max_abs_dev": float("nan"), "n_rows": len(a),
                         "note": f"shape {a.shape} vs {b.shape}"})
            print(f"    {r['name']}: SHAPE MISMATCH {a.shape} vs {b.shape}  <-- FINDING")
            continue

        res = compare_artifacts(a, b)
        ok = res["ok"]
        all_ok = all_ok and ok
        rows.append({"config": r["name"], "ref": r["ref"], "n_rows": len(a),
                     "n_shared_cols": len(shared), **res,
                     "note": "PASS" if ok else "FINDING"})
        print(f"    {r['name']}: {'PASS' if ok else 'FINDING'}  ref={r['ref']}  "
              f"n_rows={len(a)}  cols={len(shared)}  "
              f"max_ulp_sig={res['max_ulp_significant']:.2f}  "
              f"max_abs_dev={res['max_abs_dev']:.1e}  "
              f"n_exceed={res['n_exceed']}/{res['n_compared']}  "
              f"regime_equal={res['regime_equal']}  "
              f"(retired byte_equal={res['byte_equal']})")

    out = pd.DataFrame(rows)
    path = os.path.join(RESULTS, "ces_b12_byte_check.csv")
    out.to_csv(path, index=False)
    print(f"  wrote {path}")
    if not all_ok:
        print("\n  NESTING CHECK: FINDING - a committed result moved.")
    else:
        worst = max(r["max_ulp_significant"] for r in rows)
        n_retired = sum(1 for r in rows if not r["byte_equal"])
        print(f"\n  NESTING CHECK: PASS under the brief-14 criterion "
              f"(<= {BYTE_CHECK_ULP} ULP on levels, regime exact).")
        print(f"    worst significant drift across all configs: {worst:.2f} ULP "
              f"of the {BYTE_CHECK_ULP} allowed - this is the BASELINE brief 14 fixes.")
        if n_retired:
            print(f"    {n_retired}/{len(rows)} configs would have FAILED the retired "
                  f"'dev == 0.0' criterion - which is the measurement that retired it.")
    return all_ok


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default: os.cpu_count())")
    args = ap.parse_args()

    print(f"Brief 12 nesting check: {len(REFERENCES)} configs, {STEPS} steps, "
          f"{SEEDS} seeds, tail {TAIL}")
    print(f"  criterion (brief 14): <= {BYTE_CHECK_ULP} ULP with atol {BYTE_CHECK_ATOL:g} "
          f"on levels, AND exact regime match")
    ok = byte_check(regenerate(args.workers))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
