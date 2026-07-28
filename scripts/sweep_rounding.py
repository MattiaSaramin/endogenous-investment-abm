#!/usr/bin/env python
r"""Detect the double-rounding signature across the whole paper, registry-free.

Brief 18 found three cells of ``tab:sobol`` (the Slope column of
``09_sensitivity.tex``) that reproduce their PRINTED value only with a double
rounding ``round(round(x, 4), 3)`` -- not the round-once rule declared in
``paper_claims.yaml``.  ``verify_paper.py`` pins 26 claims; the paper prints 582
digits.  This script measures the SCOPE of that signature independently of the
registry, so a dedicated correction brief-paper can be sized (one block per
section, per the project instructions).

DIRECTION (brief 19 §1.1): from the ``.tex`` toward the artifacts, never the
reverse -- the printed digits are 582, the CSVs are ~59 MB.  For every numeric
token ``t`` (regex ``(?<!-)-?\d+\.\d+``) in ``paper/sections/*.tex`` and
``paper/appendices/*.tex``, with ``d`` = printed decimals:

  1. find every numeric cell ``x`` in the INCLUDED artifacts with
     ``|x - t| < 10**(-d)`` (candidates that could round to ``t``);
  2. for each candidate, HALF-UP explicitly (``decimal.Decimal`` /
     ``ROUND_HALF_UP`` -- NOT Python ``round()``, which is banker's rounding and
     in brief 18 produced a false "unexplained" diagnosis):
       r1 = round_half_up(x, d)
       r2 = round_half_up(round_half_up(x, d+1), d)
  3. classify the candidate:
       r1 == t                      -> OK                       (round-once)
       r1 != t and r2 == t          -> DOUBLE-ROUND SIGNATURE   (the defect)
       neither                      -> discard (not a match)

A token with NO surviving candidate in any artifact is NOT a failure: many
printed digits are design targets, calibration parameters or numbers cited from
the literature.  They are counted and reported as ``NO ARTIFACT CANDIDATE``.

A token may have several candidates in different artifacts (substring collision:
it happened with ``0.452``).  The detector then reports ALL of them and marks
the token ``AMBIGUOUS CANDIDATE`` -- it does NOT decide.  Disambiguation is human
work: the provenance columns (artifact, row, column) are printed for exactly
that.

ARTIFACT SCOPE (brief §1.2 -- declared, never silent).  The brief names three
exclusion patterns; run against the FULL set they leave, the sweep is
degenerate: the paper's 1- and 2-decimal tokens collide with the per-cell
simulation dumps (``_qoi`` / ``_cells`` / ``_trace`` / ``_recon`` / ``_map`` /
``turning_points`` / ...), which are never printed cell-by-cell, and the report
blows up to 11.8 M candidate rows / 1.5 GB, 11.78 M of them coincidental
round-once OK matches -- a check that inspects nothing (instructions §6).  So,
by the brief's OWN rationale ("dump per-run/per-cella mai stampati cella per
cella nel paper"), this sweep also excludes per-cell/per-run dumps, identified
by structure: any ``results/*.csv`` with more than ``ROW_THRESHOLD`` data rows.
A printed table has a handful of cells; the artifacts that back the paper's
tables (``_indices`` 33 rows, ``_summary`` 2, ``_byproducts`` 16, ...) are all
well under it, while every per-cell dump is well over.  This is a DECLARED
refinement of the brief's exclusion set, not a silent one: every excluded file
is listed in the report with its row count and reason.  ``ces_decomposition.csv``
is archived (instructions §4) and excluded explicitly; JSON side-cars
(environment / verdict / gate) are metadata, not printed cells, and are excluded
by scope.

TOKENIZER GUARD (brief 20 §1).  A ``-`` immediately preceded by another ``-`` is
a LaTeX range dash (e.g. ``\textbf{0.075--0.090}``), not a sign.  The regex now
carries a ``(?<!-)`` look-behind so the second dash of ``--`` is never read as a
minus; without it the sweep invented the token ``-0.090``, which exists nowhere
in the paper and matched an artifact cell (``ces_b14_bridge_by_sigma``) only by
coincidence.  Real negatives are unaffected -- their minus is preceded by ``$``,
``{`` or a space, never by ``-`` (verified: ``-0.030`` at l.97 is still caught).
No other LaTeX normalisation is introduced here (brief 20 §1).

STRUCTURAL BLIND SPOTS (brief 20 §0 -- declared, never silently "improved" by
chasing a cleverer detector).  Two kinds of printed number this sweep cannot
vouch for, by construction:

  1. DERIVED numbers -- counts, medians and ratios computed on the fly (e.g.
     ``0.771``, ``538``, ``0.414``, ``477``) -- exist as no cell in any CSV.
     Proximity can only pair them with something coincidental, so a match here
     is NOT attribution.
  2. Tables whose SOURCE is not among the included artifacts are not covered at
     all (``tab:baseline`` is the example: none of its numbers has an identified
     referent in the sweep).  "Zero signatures in a section" is NOT "the section
     is clean" -- it can equally mean the section's source is out of scope.

A detector that does not declare what it cannot see gets re-read as if it saw
everything -- the same mechanism by which brief 15's "18/18 aligned" became
citable.  The one place the question "is this number right?" has an answer is
where the referent is DECLARED -- the registry (``paper_claims.yaml``).  This
sweep is a trawl over already-registered digits, not a coverage map; the check
is generalised by EXTENDING THE REGISTRY, not by sharpening the sweep.

This is a DETECTOR.  Per the same rule it is run against known-bad input before
it is trusted (brief §1.4): the ``0.040`` already in the paper must be FOUND as
a double-round signature unaided, and the correctly-rounded ``0.966`` control
cell (delta ST slope) must NOT be flagged.  Both outcomes are printed.

The generated CSV is committed alongside this generator (instructions §5
corollary: every committed artifact has a committed generator).  This script
MEASURES; it changes no digit in any document.
"""
from __future__ import annotations

import bisect
import csv
import glob
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT_CSV = os.path.join(ROOT, "results", "paper_rounding_sweep.csv")

TOKEN_RE = re.compile(r"(?<!-)-?\d+\.\d+")   # brief 20 §1: '-' after '-' is a range dash, not a sign
RUN_DUMP_RE = re.compile(r"_runs|_panel|_design")   # brief §1.2, by name
ARCHIVED = {"ces_decomposition.csv"}                # instructions §4
ROW_THRESHOLD = 100   # > this many data rows => per-cell/per-run dump (declared)

OK = "OK"
DOUBLE = "DOUBLE-ROUND SIGNATURE"
NO_CAND = "NO ARTIFACT CANDIDATE"
SINGLE = "SINGLE CANDIDATE"
AMBIG = "AMBIGUOUS CANDIDATE"


def round_half_up(x, d: int) -> Decimal:
    """Half-up rounding to ``d`` decimals, as an explicit Decimal.

    ``str(float(x))`` gives the shortest round-tripping repr; the difference
    from the exact stored double is far below any rounding boundary we test.
    """
    q = Decimal(1).scaleb(-d)  # 10**(-d) as an exact Decimal
    return Decimal(str(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def scan_tex_tokens():
    """Every numeric token in the paper body, with its file, line and decimals."""
    files = sorted(
        glob.glob(os.path.join(ROOT, "paper", "sections", "*.tex"))
        + glob.glob(os.path.join(ROOT, "paper", "appendices", "*.tex"))
    )
    tokens = []
    for path in files:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.replace("{,}", "")  # LaTeX thousands sep; keeps line no.
                for m in TOKEN_RE.finditer(line):
                    ts = m.group()
                    d = len(ts.split(".")[1])
                    tokens.append(
                        {"file": rel, "line": lineno, "token": ts,
                         "d": d, "t": Decimal(ts)}
                    )
    return files, tokens


def _data_rows(path: str) -> int:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def partition_artifacts():
    """Split ``results/*.csv`` into included / excluded, every bucket declared.

    Returns (included, excluded), where excluded is a list of
    (basename, rows_or_None, reason) so the report can print all of them.
    """
    files = sorted(glob.glob(os.path.join(ROOT, "results", "*.csv")))
    included, excluded = [], []
    for path in files:
        base = os.path.basename(path)
        if base == os.path.basename(OUT_CSV):
            continue  # our own output, if a stale copy is lying around
        if base in ARCHIVED:
            excluded.append((base, None, "archived (instructions §4, no generator)"))
            continue
        if RUN_DUMP_RE.search(base):
            excluded.append((base, None, "per-run dump by name (_runs/_panel/_design)"))
            continue
        n = _data_rows(path)
        if n > ROW_THRESHOLD:
            excluded.append((base, n, f"per-cell/per-run dump (>{ROW_THRESHOLD} rows)"))
        else:
            included.append(path)
    excl_json = [(os.path.basename(p), None, "JSON side-car (metadata, not printed cells)")
                 for p in sorted(glob.glob(os.path.join(ROOT, "results", "*.json")))]
    excluded.extend(excl_json)
    return included, excluded


def load_cells(included):
    """Flatten every finite numeric cell of the included CSVs.

    Returns a list of (value, artifact_rel, row_index, column) sorted by value,
    plus a parallel value array for bisect windowing.
    """
    cells = []
    for path in included:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        df = pd.read_csv(path)
        for col in df.columns:
            arr = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype="float64")
            for i in np.nonzero(np.isfinite(arr))[0]:
                cells.append((float(arr[i]), rel, int(i), str(col)))
    cells.sort(key=lambda c: c[0])
    values = [c[0] for c in cells]
    return cells, values


def classify_token(tok, cells, values):
    """Return (candidate_rows, token_class) for one token."""
    t, d = tok["t"], tok["d"]
    tf = float(t)
    tol = 10.0 ** (-d)
    lo = bisect.bisect_left(values, tf - tol)
    hi = bisect.bisect_right(values, tf + tol)
    cands = []
    for x, art, ridx, col in cells[lo:hi]:
        if abs(x - tf) >= tol:      # strict |x - t| < 10**(-d)
            continue
        r1 = round_half_up(x, d)
        r2 = round_half_up(round_half_up(x, d + 1), d)
        if r1 == t:
            cls = OK
        elif r2 == t:
            cls = DOUBLE
        else:
            continue                # in window but rounds to neither: discard
        cands.append({
            "artifact": art, "cell_row": ridx, "cell_col": col,
            "x": repr(x), "r1": str(r1), "r2": str(r2), "candidate_class": cls,
        })
    if not cands:
        token_class = NO_CAND
    elif len(cands) == 1:
        token_class = SINGLE
    else:
        token_class = AMBIG
    return cands, token_class


def run():
    tex_files, tokens = scan_tex_tokens()
    included, excluded = partition_artifacts()
    cells, values = load_cells(included)

    rows = []
    per_section_double_cand = Counter()             # DOUBLE candidate rows / section
    per_section_double_tokens = defaultdict(set)    # distinct (line,token) / section
    per_section_double_clean = defaultdict(set)     # DOUBLE and NOT ambiguous
    double_by_artifact = Counter()
    n_no_cand = n_single = n_ambig = 0

    for tok in tokens:
        cands, token_class = classify_token(tok, cells, values)
        key = (tok["line"], tok["token"])
        if token_class == NO_CAND:
            n_no_cand += 1
            rows.append(_row(tok, None, "", token_class))
            continue
        if token_class == SINGLE:
            n_single += 1
        else:
            n_ambig += 1
        has_double = any(c["candidate_class"] == DOUBLE for c in cands)
        for c in cands:
            rows.append(_row(tok, c, c["candidate_class"], token_class))
            if c["candidate_class"] == DOUBLE:
                per_section_double_cand[tok["file"]] += 1
                per_section_double_tokens[tok["file"]].add(key)
                double_by_artifact[c["artifact"]] += 1
        if has_double and token_class == SINGLE:
            per_section_double_clean[tok["file"]].add(key)

    _write_csv(rows)
    probes = _probes(cells)
    _report(tex_files, included, excluded, len(tokens), len(cells),
            n_no_cand, n_single, n_ambig,
            per_section_double_cand, per_section_double_tokens,
            per_section_double_clean, double_by_artifact, probes)
    return rows


def _row(tok, c, cand_class, token_class):
    base = {"tex_file": tok["file"], "tex_line": tok["line"],
            "token": tok["token"], "decimals": tok["d"]}
    if c is None:
        base.update({"artifact": "", "cell_row": "", "cell_col": "",
                     "x": "", "r1": "", "r2": ""})
    else:
        base.update({"artifact": c["artifact"], "cell_row": c["cell_row"],
                     "cell_col": c["cell_col"], "x": c["x"],
                     "r1": c["r1"], "r2": c["r2"]})
    base["candidate_class"] = cand_class
    base["token_class"] = token_class
    return base


def _write_csv(rows):
    cols = ["tex_file", "tex_line", "token", "decimals", "artifact",
            "cell_row", "cell_col", "x", "r1", "r2",
            "candidate_class", "token_class"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def _find_cell(cells, artifact_suffix, column, target, tol=1e-9):
    for x, art, ridx, col in cells:
        if art.endswith(artifact_suffix) and col == column and abs(x - target) < tol:
            r1 = round_half_up(x, 3)
            r2 = round_half_up(round_half_up(x, 4), 3)
            return x, ridx, col, r1, r2
    return None


def _probes(cells):
    """Brief §1.4: two opposite-outcome tests on specific known cells."""
    out = {}
    # Probe 1 (must FIND): wealth_effect S1 slope = 0.0394677, printed 0.040.
    hit = _find_cell(cells, "ces_b13_sobol_indices.csv", "S1", 0.03946774297098501)
    if hit:
        x, ridx, col, r1, r2 = hit
        t = Decimal("0.040")
        flagged = (r1 != t and r2 == t)
        out["find_0040"] = {"x": x, "row": ridx, "r1": str(r1), "r2": str(r2),
                            "is_double_round": bool(flagged), "pass": bool(flagged)}
    else:
        out["find_0040"] = {"pass": False, "note": "cell not located in included scope"}

    # Probe 2 (must NOT flag): delta ST slope = 0.9656325, printed 0.966 (round-once).
    hit = _find_cell(cells, "ces_b13_sobol_indices.csv", "ST", 0.9656325250362902)
    if hit:
        x, ridx, col, r1, r2 = hit
        t = Decimal("0.966")
        flagged = (r1 != t and r2 == t)
        out["control_0966"] = {"x": x, "row": ridx, "r1": str(r1), "r2": str(r2),
                               "is_double_round": bool(flagged),
                               "pass": bool(not flagged and r1 == t)}
    else:
        out["control_0966"] = {"pass": False, "note": "cell not located in included scope"}
    return out


def _report(tex_files, included, excluded, n_tokens, n_cells,
            n_no_cand, n_single, n_ambig,
            per_section_double_cand, per_section_double_tokens,
            per_section_double_clean, double_by_artifact, probes):
    bar = "=" * 74
    print(bar)
    print("sweep_rounding.py -- double-rounding signature across the paper")
    print(bar)
    print(f"\nScanned {len(tex_files)} .tex files, {n_tokens} numeric tokens "
          r"(regex (?<!-)-?\d+\.\d+; a '-' after '-' is a range dash, not a sign).")
    print(f"Included {len(included)} table-scale artifacts, {n_cells} finite "
          "numeric cells.")
    print(f"Token classes: {n_single} SINGLE, {n_ambig} AMBIGUOUS, "
          f"{n_no_cand} NO ARTIFACT CANDIDATE.")

    print(f"\n-- EXCLUDED ARTIFACTS ({len(excluded)}; declared, never silent) --")
    for base, nrows, reason in excluded:
        rr = f"{nrows:>6d} rows  " if nrows is not None else " " * 12
        print(f"  {rr}{base:34s}  {reason}")

    print("\n-- DOUBLE-ROUND SIGNATURE per section --")
    secs = sorted(set(per_section_double_cand) | set(per_section_double_tokens))
    if not secs:
        print("  (none)")
    for sec in secs:
        ncand = per_section_double_cand.get(sec, 0)
        ntok = len(per_section_double_tokens.get(sec, set()))
        nclean = len(per_section_double_clean.get(sec, set()))
        print(f"  {sec:38s}  {ncand:3d} candidate(s) / {ntok:2d} token(s) "
              f"({nclean} unambiguous)")
    print(f"  TOTAL: {sum(per_section_double_cand.values())} double-round "
          f"candidate rows across "
          f"{sum(len(v) for v in per_section_double_tokens.values())} token-occurrence(s).")

    print("\n-- DOUBLE-ROUND candidates grouped by SOURCE artifact "
          "(disambiguation aid) --")
    for art, n in double_by_artifact.most_common():
        print(f"  {n:3d}  {art}")

    print(f"\n-- NO ARTIFACT CANDIDATE: {n_no_cand} token(s) "
          "(design targets / calibration / literature -- not errors) --")

    print("\n-- STRUCTURAL BLIND SPOTS (brief 20 §0 -- declared, not repaired here) --")
    print("  1. DERIVED numbers (counts/medians/ratios: 0.771, 538, 0.414, 477)")
    print("     exist as no CSV cell; any proximity match is coincidence, not")
    print("     attribution.")
    print("  2. Tables whose source is NOT an included artifact are uncovered")
    print("     (e.g. tab:baseline). 'Zero signatures' != 'section verified clean'.")
    print("  Attribution lives only where the referent is declared -- the registry")
    print("  (paper_claims.yaml). This sweep is a trawl over registered digits, not")
    print("  a coverage map; it is generalised by extending the registry.")

    print("\n-- §1.4 DETECTOR PROBES (run against known-bad input) --")
    p1 = probes["find_0040"]
    print("  [1] KNOWN-BAD, must FIND    printed 0.040 <- ces_b13_sobol_indices.csv "
          "S1 (wealth_effect)")
    print(f"        x={p1.get('x')} r1={p1.get('r1')} r2={p1.get('r2')} "
          f"double_round={p1.get('is_double_round')}  "
          f"=> {'PASS' if p1['pass'] else 'FAIL'}")
    p2 = probes["control_0966"]
    print("  [2] CONTROL, must NOT flag  printed 0.966 <- ces_b13_sobol_indices.csv "
          "ST (delta slope)")
    print(f"        x={p2.get('x')} r1={p2.get('r1')} r2={p2.get('r2')} "
          f"double_round={p2.get('is_double_round')}  "
          f"=> {'PASS' if p2['pass'] else 'FAIL'}")
    both = p1["pass"] and p2["pass"]
    print("\n  PROBE VERDICT: " + ("BOTH PASS -- detector trusted"
          if both else "FAIL -- detector is broken, stop (brief §1.4)"))

    print(f"\nReport written to {os.path.relpath(OUT_CSV, ROOT)}.")
    print(bar)
    return both


if __name__ == "__main__":
    run()
