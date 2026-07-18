#!/usr/bin/env python
"""Regenerate the brief-04 (sigma, rho) sweep outputs — reproducibly.

Brief 04 generalised the Cobb-Douglas core to a normalised CES and swept the
elasticity of substitution sigma against the retention ratio rho, producing the
*sign frontier* — the locus in (sigma, rho) where dY/drho changes sign. This is the
committed brief-05 companion to ``scripts/run_brief05.py``: it makes the brief-04
``results/ces_*.csv`` reproducible from committed code rather than an ad-hoc session.

It reuses the analysis primitives already in :mod:`experiment` (``sigma_rho_sweep``,
``sweep_derivatives``, ``sign_frontier``) without duplicating them; the driver is only
orchestration + I/O.

Five outputs (all at the brief-04 configuration — SIGMA_SWEEP x RHO_SWEEP, 3 seeds,
2000 steps, mean of the last 50, c0 = 2.0, anchor rho = 0.40, all model defaults):

* ``ces_sigma_rho_grid.csv``               — the raw (sigma, rho) grid (one row per cell)
* ``ces_derivatives.csv``                  — dY/drho, dU/drho, per-sigma viable support
* ``ces_derivatives_common_support.csv``   — the same, on the support viable at EVERY sigma
* ``ces_sign_frontier.csv``                — sigma*(rho) from the per-sigma derivatives
* ``ces_sign_frontier_common_support.csv`` — sigma*(rho) from the common-support derivatives

Two supports are reported deliberately: the per-sigma viable support uses every rho a
given sigma survives (so different sigmas can differ in which rho they span), while the
common support intersects down to the rho values alive for *all* sigma, so the slope
comparison across sigma is not confounded by which cells happened to live.

Determinism: like run_brief05.py, BLAS is pinned to one thread (below, before numpy is
imported) so the float reduction order in the derivatives is fixed and the outputs
reproduce byte-for-byte on any host. The raw grid is thread-invariant (no BLAS in the
simulation path); only the derived tables go through reductions.

NOTE: the sixth brief-04 file, ``ces_decomposition.csv`` (a bespoke labour-displacement
decomposition), is NOT produced here — it is not an output of the three sweep primitives,
and its original per-sigma (K_lo, K_hi, demand) parameters are not recoverable from the
committed CSV. It is left as an archived output pending a decision on its spec.

Usage
-----
    python scripts/run_brief04.py                 # -> results/, threads pinned
    python scripts/run_brief04.py --out results   # explicit output directory
"""

from __future__ import annotations

import argparse
import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Pin BLAS/numpy to one thread BEFORE numpy is imported (here via pandas/experiment), so
# the reduction order in the derivatives is deterministic and machine-independent.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from experiment import (
    DEFAULT_SEEDS,
    DEFAULT_STEPS,
    sigma_rho_sweep,
    sweep_derivatives,
    sign_frontier,
)


def common_viable_rhos(grid):
    """The rho values that are viable (not collapsed) for EVERY sigma in the grid."""
    return [
        rho for rho in sorted(grid["rho"].unique())
        if not grid.loc[grid["rho"] == rho, "collapsed"].any()
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="results", help="output directory (default: results)")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    def write(df, name):
        df.to_csv(os.path.join(out, name), index=False)
        print(f"  wrote {name:38s} {df.shape[0]:>4d} rows")

    print(f"brief-04 sweep: SIGMA_SWEEP x RHO_SWEEP, {args.seeds} seeds, "
          f"{args.steps} steps, c0 = 2.0 (defaults)")

    # Raw (sigma, rho) grid — the simulation output (thread-invariant).
    grid = sigma_rho_sweep(seeds=args.seeds, steps=args.steps)
    write(grid, "ces_sigma_rho_grid.csv")

    # Derivatives on the per-sigma viable support.
    deriv = sweep_derivatives(grid, viable_only=True)
    write(deriv, "ces_derivatives.csv")

    # Derivatives on the common viable support (rhos alive for every sigma).
    common = common_viable_rhos(grid)
    print(f"  common viable support (rho alive at every sigma): {common}")
    deriv_cs = sweep_derivatives(grid[grid["rho"].isin(common)], viable_only=True)
    write(deriv_cs, "ces_derivatives_common_support.csv")

    # Sign frontiers: where dY/drho crosses zero, per rho.
    write(sign_frontier(deriv), "ces_sign_frontier.csv")
    write(sign_frontier(deriv_cs), "ces_sign_frontier_common_support.csv")

    print(f"\nDone. Five ces_*.csv written to {out}")


if __name__ == "__main__":
    main()
