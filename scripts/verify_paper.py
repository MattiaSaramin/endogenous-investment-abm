#!/usr/bin/env python
"""Verify the paper's headline numbers against their committed artifacts.

Reads ``scripts/paper_claims.yaml``.  For every claim whose ``appears_in`` lists
at least one file under ``paper/``, it checks TWO things:

  (a) ARTIFACT:  load the CSV, apply the filter, read the exact cell, and confirm
      ``round(cell, decimals) == value`` -- rounding ONCE from the full value (a
      double rounding is the §5 defect this whole registry exists to pin down);
  (b) TEX:       ``value``, formatted to ``decimals``, is COUNTED in each
      required ``paper/`` file named in ``appears_in``.  ``OK`` means it appears
      EXACTLY ONCE; more than one occurrence is ``AMBIGUOUS`` (brief 19 §2) --
      the value alone does not discriminate the claim, so the check cannot vouch
      for it.  Brief 18 measured this on ``0.452``, which occurs in
      ``06_shape.tex`` and ``08_fiscal.tex`` as an unrelated cell.

Outcomes, one per claim:

  OK                     both checks pass and the tex value occurs exactly once
  AMBIGUOUS              the tex value occurs more than once (line numbers listed);
                         NOT a failure -- a non-discriminating claim, counted apart.
                         Add a ``context`` regex to the registry to pin it to its
                         real line (populate ONLY for claims the run flags here).
  MISMATCH               the artifact does not support ``value`` (round(cell) != value)
  ARTIFACT MISSING       the CSV does not exist
  FILTER MATCHED 0 ROWS  the filter (or row_index) selected nothing -- a FAILURE,
                         never a skip: it is the standard way a fake check reports
                         success
  FILTER MATCHED >1 ROWS  an under-specified filter (no row_index) hit many rows
  CLAIM NOT FOUND IN TEX  the artifact supports ``value`` but the paper does not
                         print it -- this is how a paper-vs-CSV discrepancy shows
  SKIP (non-paper)       no ``appears_in`` file is under ``paper/`` (coherence.py's job)

Registry field added by this brief:
  context   (optional) a Python regex.  When the tex value is AMBIGUOUS, only the
            matching lines are counted; if exactly one matches, the claim is OK.

Exit code is non-zero if any claim FAILS (MISMATCH / ARTIFACT MISSING /
FILTER-ZERO / FILTER->1 / CLAIM-NOT-FOUND).  ``AMBIGUOUS`` does NOT fail the
build.  Intended for CI or a pre-commit hook.

This is a DETECTOR.  Per the project rule -- a check that reports success without
inspecting anything is worse than none -- it is run against known-bad input
before it is trusted:  ``python verify_paper.py --selftest`` injects a value that
occurs twice in a scratch .tex, asserts ``AMBIGUOUS`` with both line numbers,
then adds the correct ``context`` and asserts ``OK`` (brief 19 §2).
"""
from __future__ import annotations

import math
import os
import re
import sys
import tempfile
from collections import Counter

import pandas as pd
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
REGISTRY = os.path.join(_HERE, "paper_claims.yaml")

OK = "OK"
AMBIGUOUS = "AMBIGUOUS"
MISMATCH = "MISMATCH"
NO_ARTIFACT = "ARTIFACT MISSING"
ZERO_ROWS = "FILTER MATCHED 0 ROWS"
MANY_ROWS = "FILTER MATCHED >1 ROWS"
NOT_IN_TEX = "CLAIM NOT FOUND IN TEX"
SKIP = "SKIP (non-paper)"

FAILURES = {MISMATCH, NO_ARTIFACT, ZERO_ROWS, MANY_ROWS, NOT_IN_TEX}

_LINES_CACHE: dict[str, list[str]] = {}


def _norm_doc(text: str) -> str:
    """Strip LaTeX thousands separators so ``1596`` matches ``1{,}596``."""
    return text.replace("{,}", "")


def _read_doc_lines(rel_path: str) -> list[str]:
    if rel_path not in _LINES_CACHE:
        with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="replace") as fh:
            _LINES_CACHE[rel_path] = [_norm_doc(line) for line in fh.read().splitlines()]
    return _LINES_CACHE[rel_path]


def _fmt(value, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _tex_occurrence_status(needle: str, lines: list[str], where: str, context):
    """Count ``needle`` (substring) across ``lines`` and classify.

    Returns (status, detail).  ``lines`` is the file (or an injected scratch
    file); ``where`` is a label for messages; ``context`` is an optional regex
    used to disambiguate when the raw count exceeds one.
    """
    hits = [(i, line.count(needle)) for i, line in enumerate(lines, 1)
            if needle in line]
    total = sum(c for _, c in hits)
    if total == 0:
        return NOT_IN_TEX, f"'{needle}' not in {where}"
    if total == 1:
        return OK, ""
    line_list = ",".join(str(i) for i, _ in hits)
    if context:
        rx = re.compile(context)
        ctx_hits = [(i, c) for (i, c) in hits if rx.search(lines[i - 1])]
        ctx_total = sum(c for _, c in ctx_hits)
        if ctx_total == 1:
            return OK, ""
        ctx_lines = ",".join(str(i) for i, _ in ctx_hits) or "none"
        return AMBIGUOUS, (f"'{needle}' x{total} in {where} at lines {line_list}; "
                           f"context /{context}/ still matches {ctx_total} "
                           f"(lines {ctx_lines})")
    return AMBIGUOUS, (f"'{needle}' x{total} in {where} at lines {line_list} "
                       f"(add a context regex to disambiguate)")


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

    # (b) tex check (skipped for expect_missing: the null prints as "---").
    # Count occurrences per required paper target; a real absence (NOT IN TEX)
    # outranks an ambiguity, so it is reported first.
    if decimals is None:
        return OK, ""
    needle = _fmt(float(claim["value"]), decimals)
    context = claim.get("context")
    tex_results = []
    for tgt in paper_targets:
        if not tgt.get("required", True):
            continue
        st, detail = _tex_occurrence_status(
            needle, _read_doc_lines(tgt["file"]), tgt["file"], context)
        tex_results.append((st, detail))
    for st, detail in tex_results:
        if st == NOT_IN_TEX:
            return NOT_IN_TEX, detail
    for st, detail in tex_results:
        if st == AMBIGUOUS:
            return AMBIGUOUS, detail
    return OK, ""


def selftest() -> int:
    """Injection test (brief 19 §2): value twice -> AMBIGUOUS; +context -> OK."""
    print("verify_paper.py --selftest -- injected known-bad tex\n")
    lines = [
        r"\begin{table}\label{tab:demo}",
        r"Demo row & 0.123 & other\\",     # the real occurrence (line 2)
        r"Unrelated prose mentioning 0.123 elsewhere.",  # a collision (line 3)
        r"\end{table}",
    ]
    needle = "0.123"

    st1, d1 = _tex_occurrence_status(needle, lines, "<scratch.tex>", None)
    ok1 = (st1 == AMBIGUOUS and "2" in d1 and "3" in d1)
    print(f"  [1] no context   -> {st1:9s} {d1}")
    print(f"        expected AMBIGUOUS listing lines 2 and 3   => "
          f"{'PASS' if ok1 else 'FAIL'}")

    st2, d2 = _tex_occurrence_status(needle, lines, "<scratch.tex>", r"tab:demo|Demo row")
    ok2 = (st2 == OK)
    print(f"  [2] context 'Demo row' -> {st2:9s} {d2 or '(exactly one match)'}")
    print(f"        expected OK after context               => "
          f"{'PASS' if ok2 else 'FAIL'}")

    # also prove the same logic writes/reads a real file on disk
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        tmp = fh.name
    try:
        disk_lines = [_norm_doc(l) for l in open(tmp, encoding="utf-8").read().splitlines()]
        st3, _ = _tex_occurrence_status(needle, disk_lines, tmp, None)
        ok3 = (st3 == AMBIGUOUS)
    finally:
        os.unlink(tmp)
    print(f"  [3] same via on-disk file -> {st3:9s}  => "
          f"{'PASS' if ok3 else 'FAIL'}")

    both = ok1 and ok2 and ok3
    print(f"\n  SELFTEST VERDICT: "
          f"{'ALL PASS -- OK/AMBIGUOUS discrimination trusted' if both else 'FAIL'}")
    return 0 if both else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return selftest()
    registry = argv[0] if argv else REGISTRY
    with open(registry, encoding="utf-8") as fh:
        claims = yaml.safe_load(fh)

    width = max(len(c["claim_id"]) for c in claims)
    tally = Counter()
    failed, ambiguous = [], []
    print(f"verify_paper.py -- {len(claims)} claims from {os.path.relpath(registry, ROOT)}\n")
    for claim in claims:
        status, detail = verify_claim(claim)
        tally[status] += 1
        if status in FAILURES:
            failed.append((claim["claim_id"], status, detail))
        elif status == AMBIGUOUS:
            ambiguous.append((claim["claim_id"], detail))
        line = f"  {status:22s} {claim['claim_id']:{width}s}"
        if detail:
            line += f"  -- {detail}"
        print(line)

    n_fail = sum(tally[s] for s in FAILURES)
    print("\nSummary:")
    for status in (OK, AMBIGUOUS, MISMATCH, NO_ARTIFACT, ZERO_ROWS, MANY_ROWS,
                   NOT_IN_TEX, SKIP):
        print(f"  {tally[status]:3d}  {status}")
    print(f"  ---\n  {n_fail} FAIL (AMBIGUOUS excluded), {tally[AMBIGUOUS]} ambiguous, "
          f"{tally[SKIP]} skipped.")

    if ambiguous:
        print("\nAMBIGUOUS (non-discriminating -- add a context regex to pin the line):")
        for cid, detail in ambiguous:
            print(f"  - {cid}: {detail}")
    if failed:
        print("\nFAILURES (open items -- NOT fixed by this brief, see brief-18 sec 5/6):")
        for cid, status, detail in failed:
            print(f"  - {cid}: {status} -- {detail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
