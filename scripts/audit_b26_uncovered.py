#!/usr/bin/env python
"""Classify every numeric token in the paper by REGISTRY COVERAGE (brief 26, Phase 3).

The registry (``scripts/paper_claims.yaml``, 49 claims) is the only place attribution
lives: ``verify_paper.py`` and ``coherence.py`` both read it.  ``sweep_rounding.py`` is
a registry-free trawl over printed digits, but -- as its own docstring says -- proximity
is NOT attribution.  So a number can be printed in the paper and be attributable to
NOTHING: not in the registry, and not matchable to a unique CSV cell.  This script
enumerates those tokens and files each into the blind spot it belongs to, so the gaps
are counted rather than left implicit.

WHAT IT DOES.  Over the same files ``sweep_rounding.py`` scans (``paper/sections/*.tex``
+ ``paper/appendices/*.tex``) it extracts every numeric token -- decimals (the sweep's
regex ``(?<!-)-?\\d+\\.\\d+``) AND integers (``(?<![\\d.])\\d+(?![\\d.])``), because two of
the four blind spots are about integers the sweep never sees.  Each DISTINCT token is
classified:

  COVERED_RESULT     the token is a paper_claims.yaml value (formatted at its decimals)
                     -- verify_paper / coherence own it.
  COVERED_PARAM      the token is a parameter value in verify_model.py's registry
                     (brief 26 closes this axis) -- e.g. 0.05, 0.40, 41.87.
  BLINDSPOT_1_DERIVED   a DERIVED number (count/median/ratio) that exists as no CSV
                     cell; any sweep proximity match is coincidence (brief 19 #1).
  BLINDSPOT_2_TABLE_NO_SOURCE  a token of a table whose source is NOT among the sweep's
                     included artifacts (tab:baseline in primis) -- uncoverable until the
                     table gets a referent (brief 19 #2 / brief 22).
  BLINDSPOT_3_SMALL_INT  a small integer whose row carries the same digit elsewhere, so a
                     substring check cannot discriminate it (brief 22 #3).
  BLINDSPOT_4_MEASURED_NO_CSV  a MEASURED number with no committed CSV to read it from --
                     the test count (brief 24 #4).
  STRUCTURAL         a model-structure integer (n_f=10, N=100, 2000 steps, seed counts):
                     not a result, not an error.
  LITERATURE_OR_DESIGN  the long tail: citation values, empirical ranges, design targets,
                     years.  Uncovered by design -- the sweep's "not an error" bucket.

The blind-spot sets are DECLARED here (from the recorded examples in METHODOLOGY §5), not
inferred by proximity: this script counts and classifies, it does NOT attribute.  The two
KNOWN FALSE POSITIVES that must never be "corrected" (0.771, 59.4; METHODOLOGY §5.3) are
flagged explicitly with their justification.

Output: ``results/audit_b26_uncovered.csv`` (this script is its committed generator).

CAVEAT (brief 26): the paper working tree may carry uncommitted edits; token positions
then reflect the working tree, exactly like ``sweep_rounding.py``.  Counts are printed so
the state is visible.
"""
from __future__ import annotations

import csv
import glob
import os
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
REGISTRY = os.path.join(_HERE, "paper_claims.yaml")
OUT_CSV = os.path.join(ROOT, "results", "audit_b26_uncovered.csv")

DECIMAL_RE = re.compile(r"(?<!-)-?\d+\.\d+")          # sweep_rounding.py's token
INTEGER_RE = re.compile(r"(?<![\d.])\d+(?![\d.\d])")  # standalone integers

# --- declared blind-spot sets (from METHODOLOGY §5, the recorded examples) ------
DERIVED_TOKENS = {"0.771", "538", "0.414", "477"}          # #1 (brief 19)
BASELINE_TOKENS = {"59.4"}                                  # #2 tab:baseline (brief 19/22)
MEASURED_NO_CSV = {"569"}                                   # #4 test count (brief 24)
STRUCTURAL = {"10", "100", "200", "2000", "20", "12", "3", "50", "5", "2", "1",
              "0", "90", "6", "7", "8", "16"}               # model structure / seeds / bins
# The two false positives that must NEVER be "corrected" (the 667003b movement).
FALSE_POSITIVES = {
    "0.771": "1230/1596=0.770677, round-once 0.771: PAPER IS CORRECT; sweep match to "
             "ces_b07_sigma_star_by_rho/ci_hi is coincidence (derived, blind spot #1).",
    "59.4":  "tab:baseline, NOT attributed: its source is not among the 51/56 included "
             "artifacts (blind spot #2); sweep match to ces_sigma_rho_grid is another cell.",
}


def round_half_up(x: float, decimals: int) -> str:
    q = Decimal(1).scaleb(-decimals)
    return str(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def tex_files() -> list[str]:
    files = sorted(glob.glob(os.path.join(ROOT, "paper", "sections", "*.tex")))
    files += sorted(glob.glob(os.path.join(ROOT, "paper", "appendices", "*.tex")))
    return files


def load_registry_tokens() -> set[str]:
    """Formatted value strings the registry covers (value @ its decimals)."""
    covered = set()
    for c in yaml.safe_load(open(REGISTRY, encoding="utf-8")):
        v = c.get("value")
        if v is None:
            continue
        d = int(c.get("decimals", 0))
        covered.add(round_half_up(float(v), d))
        covered.add(f"{float(v):.{d}f}")
    return covered


def load_param_tokens() -> set[str]:
    """Parameter needles from verify_model.py's registry (the b26 axis)."""
    import sys
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import verify_model as VM
    toks = set()
    for e in VM.REGISTRY:
        for n in e.get("needles", [e.get("needle")]):
            if n and n != "swept":
                toks.add(n)
    return toks


def classify(token: str, covered_result: set[str], covered_param: set[str]) -> str:
    if token in covered_result:
        return "COVERED_RESULT"
    if token in covered_param:
        return "COVERED_PARAM"
    if token in DERIVED_TOKENS:
        return "BLINDSPOT_1_DERIVED"
    if token in BASELINE_TOKENS:
        return "BLINDSPOT_2_TABLE_NO_SOURCE"
    if token in MEASURED_NO_CSV:
        return "BLINDSPOT_4_MEASURED_NO_CSV"
    if "." not in token:
        # an integer the registry does not carry
        if token in STRUCTURAL:
            return "STRUCTURAL"
        return "BLINDSPOT_3_SMALL_INT"
    return "LITERATURE_OR_DESIGN"


def main() -> int:
    covered_result = load_registry_tokens()
    covered_param = load_param_tokens()

    # distinct token -> {files}, count
    occ_files: dict[str, set[str]] = defaultdict(set)
    occ_count: dict[str, int] = defaultdict(int)
    n_decimal = n_integer = 0
    for path in tex_files():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        text = open(path, encoding="utf-8", errors="replace").read().replace("{,}", "")
        for m in DECIMAL_RE.findall(text):
            occ_files[m].add(rel)
            occ_count[m] += 1
            n_decimal += 1
        for m in INTEGER_RE.findall(text):
            occ_files[m].add(rel)
            occ_count[m] += 1
            n_integer += 1

    rows = []
    for tok in sorted(occ_files, key=lambda t: (("." not in t), t)):
        cat = classify(tok, covered_result, covered_param)
        rows.append({
            "token": tok,
            "kind": "int" if "." not in tok else "decimal",
            "occurrences": occ_count[tok],
            "files": ";".join(sorted(occ_files[tok])),
            "category": cat,
            "false_positive_note": FALSE_POSITIVES.get(tok, ""),
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    cols = ["token", "kind", "occurrences", "files", "category", "false_positive_note"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # --- summary ---------------------------------------------------------
    by_cat = defaultdict(int)
    for r in rows:
        by_cat[r["category"]] += 1
    print("audit_b26_uncovered.py -- paper numeric-token coverage classification\n")
    print(f"Scanned {len(tex_files())} .tex files: "
          f"{n_decimal} decimal + {n_integer} integer token occurrences; "
          f"{len(occ_files)} DISTINCT tokens.")
    print(f"Registry (paper_claims.yaml): 49 claims.\n")
    print(f"{'category':32s} distinct-tokens")
    print("-" * 50)
    for cat in ("COVERED_RESULT", "COVERED_PARAM", "BLINDSPOT_1_DERIVED",
                "BLINDSPOT_2_TABLE_NO_SOURCE", "BLINDSPOT_3_SMALL_INT",
                "BLINDSPOT_4_MEASURED_NO_CSV", "STRUCTURAL", "LITERATURE_OR_DESIGN"):
        print(f"{cat:32s} {by_cat.get(cat, 0)}")
    print("\nKnown false positives (NEVER correct -- METHODOLOGY §5.3):")
    for t, note in FALSE_POSITIVES.items():
        present = t in occ_files
        print(f"  {t:8s} present={present}  {note}")
    print(f"\nReport written to {os.path.relpath(OUT_CSV, ROOT)} "
          f"({len(rows)} distinct tokens).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
