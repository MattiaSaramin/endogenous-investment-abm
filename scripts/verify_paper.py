#!/usr/bin/env python
"""Verify the paper's headline numbers against their committed artifacts.

Reads ``scripts/paper_claims.yaml``.  For every claim whose ``appears_in`` lists
at least one file under ``paper/``, it checks TWO things:

  (a) ARTIFACT:  load the CSV, apply the filter, read the exact cell, and confirm
      ``round(cell, decimals) == value`` -- rounding ONCE from the full value (a
      double rounding is the §5 defect this whole registry exists to pin down);
  (b) TEX:       ``value``, formatted to ``decimals``, appears literally in each
      required ``paper/`` file named in ``appears_in``.

Outcomes, one per claim:

  OK                     both checks pass
  MISMATCH               the artifact does not support ``value`` (round(cell) != value)
  ARTIFACT MISSING       the CSV does not exist
  FILTER MATCHED 0 ROWS  the filter (or row_index) selected nothing -- a FAILURE,
                         never a skip: it is the standard way a fake check reports
                         success
  FILTER MATCHED >1 ROWS  an under-specified filter (no row_index) hit many rows
  CLAIM NOT FOUND IN TEX  the artifact supports ``value`` but the paper does not
                         print it -- this is how a paper-vs-CSV discrepancy shows
  SKIP (non-paper)       no ``appears_in`` file is under ``paper/`` (coherence.py's job)

Exit code is non-zero if any claim FAILS (MISMATCH / ARTIFACT MISSING /
FILTER-ZERO / FILTER->1 / CLAIM-NOT-FOUND).  Intended for CI or a pre-commit hook.

This is a DETECTOR.  Per the project rule -- a check that reports success without
inspecting anything is worse than none -- it is run against known-bad input
(three distinct injections) before it is trusted; see the brief-18 report.
"""
from __future__ import annotations

import math
import os
import sys

import pandas as pd
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
REGISTRY = os.path.join(_HERE, "paper_claims.yaml")

OK = "OK"
MISMATCH = "MISMATCH"
NO_ARTIFACT = "ARTIFACT MISSING"
ZERO_ROWS = "FILTER MATCHED 0 ROWS"
MANY_ROWS = "FILTER MATCHED >1 ROWS"
NOT_IN_TEX = "CLAIM NOT FOUND IN TEX"
SKIP = "SKIP (non-paper)"

FAILURES = {MISMATCH, NO_ARTIFACT, ZERO_ROWS, MANY_ROWS, NOT_IN_TEX}

_TEX_CACHE: dict[str, str] = {}


def _norm_doc(text: str) -> str:
    """Strip LaTeX thousands separators so ``1596`` matches ``1{,}596``."""
    return text.replace("{,}", "")


def _read_doc(rel_path: str) -> str:
    if rel_path not in _TEX_CACHE:
        with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="replace") as fh:
            _TEX_CACHE[rel_path] = _norm_doc(fh.read())
    return _TEX_CACHE[rel_path]


def _fmt(value, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _select_cell(df: pd.DataFrame, claim: dict):
    """Apply the filter (+ optional row_index) and return (cell, status_or_None)."""
    for col, val in claim.get("filter", {}).items():
        if col not in df.columns:
            return None, f"{ZERO_ROWS} (no column '{col}')"
        df = df[df[col] == val]
    if "row_index" in claim:
        df = df.reset_index(drop=True)
        i = int(claim["row_index"])
        if len(df) == 0:
            return None, ZERO_ROWS
        if i >= len(df):
            return None, f"{ZERO_ROWS} (row_index {i} >= {len(df)} rows)"
        return df.iloc[i][claim["column"]], None
    if len(df) == 0:
        return None, ZERO_ROWS
    if len(df) > 1:
        return None, f"{MANY_ROWS} ({len(df)} rows; add row_index or tighten filter)"
    return df.iloc[0][claim["column"]], None


def verify_claim(claim: dict):
    """Return (status, detail) for a single claim."""
    paper_targets = [a for a in claim["appears_in"]
                     if a["file"].replace("\\", "/").startswith("paper/")]
    if not paper_targets:
        return SKIP, "no paper/ target (coherence.py checks this one)"

    artifact = claim["artifact"]
    path = os.path.join(ROOT, artifact)
    if not os.path.exists(path):
        return NO_ARTIFACT, artifact
    df = pd.read_csv(path)

    cell, status = _select_cell(df, claim)
    if status is not None:
        return status, f"{artifact} {claim.get('filter', {})}"

    # (a) artifact check
    if claim.get("expect_missing"):
        if not (cell is None or (isinstance(cell, float) and math.isnan(cell))
                or (isinstance(cell, str) and cell.strip() == "")):
            return MISMATCH, f"expected MISSING, artifact has {cell!r}"
        decimals = None  # nothing to format / search for a null cell
    else:
        try:
            got = round(float(cell), int(claim["decimals"]))
        except (TypeError, ValueError):
            return MISMATCH, f"cell {cell!r} is not numeric"
        want = float(claim["value"])
        if abs(got - want) > 1e-9:
            return MISMATCH, (f"artifact round({float(cell):.6f}, {claim['decimals']}) "
                              f"= {got} != value {want}")
        decimals = int(claim["decimals"])

    # (b) tex check (skipped for expect_missing: the null prints as "---")
    if decimals is not None:
        needle = _fmt(float(claim["value"]), decimals)
        for tgt in paper_targets:
            if not tgt.get("required", True):
                continue
            if needle not in _read_doc(tgt["file"]):
                return NOT_IN_TEX, f"'{needle}' not in {tgt['file']}"

    return OK, ""


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry = argv[0] if argv else REGISTRY
    with open(registry, encoding="utf-8") as fh:
        claims = yaml.safe_load(fh)

    width = max(len(c["claim_id"]) for c in claims)
    n_fail = n_ok = n_skip = 0
    failed = []
    print(f"verify_paper.py -- {len(claims)} claims from {os.path.relpath(registry, ROOT)}\n")
    for claim in claims:
        status, detail = verify_claim(claim)
        if status in FAILURES:
            n_fail += 1
            failed.append((claim["claim_id"], status, detail))
        elif status == SKIP:
            n_skip += 1
        else:
            n_ok += 1
        line = f"  {status:22s} {claim['claim_id']:{width}s}"
        if detail:
            line += f"  -- {detail}"
        print(line)

    print(f"\n{n_ok} OK, {n_fail} FAIL, {n_skip} skipped (non-paper).")
    if failed:
        print("\nFAILURES (open items -- NOT fixed by this brief, see brief-18 sec 5/6):")
        for cid, status, detail in failed:
            print(f"  - {cid}: {status} -- {detail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
