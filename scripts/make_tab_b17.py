#!/usr/bin/env python
r"""Generate the body of tab:b17 (the anchored-margin resolution map) from
``results/ces_b17_margin.csv``.  Brief 28, Voice A.

The b17 experiment (adaptive expectation of utilization: the accelerator reads
``u^e_t = u^e_{t-1} + lambda_u (u_{t-1} - u^e_{t-1})`` instead of ``u_{t-1}``)
records, for each (beta, lambda_u), whether the anchored retention rate resolves
on the falling branch of the turning point.  The point of the TABLE, and the
reason it is a table and not prose, is that ``unresolved'' has TWO distinct
causes that prose collapses:

  resolved                        margin_resolved == True
                                  (falling branch, negative anchored margin)
  unresolved, anchor in CI        margin_resolved == False, CI present,
                                  anchor_in_ci == True (the margin vanishes)
  unresolved, CI not estimable    margin_resolved == False, ci_lo/ci_hi empty
                                  (rho* itself not resolved -- a DIFFERENT reason)

The two empty-CI cells (beta=0.15, lambda_u in {0.25, 0.50}) carry
``anchor_in_ci = False`` because there is no interval to contain the anchor;
that is NOT ``resolved''.  ``margin_resolved`` is the authoritative column.
This is the exact ``empty != False'' trap brief 27-quinquies caught on
``anchored_left_of_turn`` (1058 empty cells read as False gave 0.299 for 0.887).

The generator ASSERTS the three states partition all 30 rows disjointly, so the
symbol grid cannot silently merge the two ``unresolved'' kinds.  Output is the
six body rows in beta order, printed to stdout; the paper carries them verbatim
between the ``do not hand-edit'' marker and ``\bottomrule'' (byte-identical, like
tab:sobol and tab:prices).  This script MEASURES; it changes no document.

Symbols (legend lives in the caption):
  \downarrow  resolved (falling, negative margin)
  \sim        unresolved, anchor inside the rho* CI (margin vanishes)
  \emptyset   unresolved, rho* CI not estimable
"""
from __future__ import annotations

import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
ARTIFACT = os.path.join(ROOT, "results", "ces_b17_margin.csv")

RESOLVED = "resolved"
ANCHOR_IN_CI = "unresolved_anchor_in_ci"
CI_EMPTY = "unresolved_ci_empty"

SYMBOL = {RESOLVED: r"$\downarrow$", ANCHOR_IN_CI: r"$\sim$", CI_EMPTY: r"$\emptyset$"}

LAMBDAS = [0.00, 0.25, 0.50, 0.75, 1.00]


def classify(row) -> str:
    """Map one artifact row to exactly one of the three states.

    ``margin_resolved`` is authoritative; the empty-CI case is distinguished by a
    missing interval, NOT by ``anchor_in_ci`` (which is False there for want of an
    interval, and must never be read as ``resolved'').
    """
    if bool(row["margin_resolved"]):
        return RESOLVED
    if pd.isna(row["ci_lo"]) or pd.isna(row["ci_hi"]):
        return CI_EMPTY
    return ANCHOR_IN_CI


def load_states():
    df = pd.read_csv(ARTIFACT)
    df["state"] = df.apply(classify, axis=1)

    # --- assert the partition: disjoint, exhaustive, and self-consistent -------
    n = len(df)
    counts = df["state"].value_counts().to_dict()
    assert n == 30, f"expected 30 rows, got {n}"
    assert set(df["state"]) <= {RESOLVED, ANCHOR_IN_CI, CI_EMPTY}, "unknown state"
    assert sum(counts.values()) == n, "states do not cover every row"
    # each state's defining predicate must hold for exactly its members
    res = df[df["state"] == RESOLVED]
    anc = df[df["state"] == ANCHOR_IN_CI]
    emp = df[df["state"] == CI_EMPTY]
    assert res["margin_resolved"].all(), "resolved rows must have margin_resolved"
    assert (~anc["margin_resolved"]).all() and anc["ci_lo"].notna().all() \
        and bool(anc["anchor_in_ci"].all()), "anchor-in-CI predicate violated"
    assert (~emp["margin_resolved"]).all() \
        and (emp["ci_lo"].isna() | emp["ci_hi"].isna()).all(), "CI-empty predicate violated"
    # the counts this table's prose depends on
    assert len(res) == 13, f"resolved count {len(res)} != 13"
    assert len(emp) == 2, f"CI-empty count {len(emp)} != 2"
    assert len(anc) == 15, f"anchor-in-CI count {len(anc)} != 15"
    return df


def body_rows(df) -> list[str]:
    lut = {(round(float(r["beta"]), 2), round(float(r["lambda_u"]), 2)): r["state"]
           for _, r in df.iterrows()}
    betas = sorted({round(float(b), 2) for b in df["beta"]})
    rows = []
    for b in betas:
        cells = " & ".join(SYMBOL[lut[(b, round(l, 2))]] for l in LAMBDAS)
        rows.append(f"${b:.2f}$ & {cells}\\\\")
    return rows


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    df = load_states()
    if argv and argv[0] == "--summary":
        print(df[["beta", "lambda_u", "rho_star", "state"]].to_string(index=False))
        print("\ncounts:", df["state"].value_counts().to_dict())
        return 0
    for line in body_rows(df):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
