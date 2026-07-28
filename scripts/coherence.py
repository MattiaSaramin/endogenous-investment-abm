#!/usr/bin/env python
"""Cross-check the SAME headline number across the documents that must agree.

Reads ``scripts/paper_claims.yaml``.  For each claim it checks that the value
appears in EVERY required document listed in ``appears_in`` -- so a number edited
in one place but not another is caught.  It does NOT read the CSV artifacts: that
is ``verify_paper.py``'s job (paper vs artifact).  ``coherence.py`` compares
documents to each other only.

Documents handled: ``README.md``, ``RESULTS.md``, ``METHODOLOGY.md``, the paper
``.tex`` files, and ``notebooks/01_Endogenous_Investment.ipynb``.  For the
notebook it searches MARKDOWN cell sources and saved CODE OUTPUTS (stream text
and ``text/plain`` / ``text/html`` data) -- never code source, where a number is
a parameter, not a claim.

Outcomes, one per claim:

  COHERENT       value present in every required document
  DIVERGENT      value missing from a required document (a diverged / edited copy)
  SINGLE DOC     fewer than two documents -> nothing to cross-check
  SKIP (null)    the claim is a deliberately-missing cell (no value to compare)

Exit code is non-zero on any DIVERGENT.

DECLARED LIMITATION: the match is a normalised substring, so it cannot tell two
different quantities that share a printed string apart.  It reliably catches a
divergence in a required document (that document loses the string); it can miss
one masked by an unrelated occurrence of the same string in the same document.
This is the same class of limitation the symbol->parameter map guards against in
the registry, and it is why the ``appears_in`` map is built by real grep with
context, not assumed.

As with ``verify_paper.py`` this is a DETECTOR and is run against known-bad input
(a divergent copy injected into one document) before it is trusted; see the
brief-18 report.
"""
from __future__ import annotations

import json
import os
import sys

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
REGISTRY = os.path.join(_HERE, "paper_claims.yaml")

COHERENT = "COHERENT"
DIVERGENT = "DIVERGENT"
SINGLE = "SINGLE DOC"
SKIP = "SKIP (null)"

_DOC_CACHE: dict[str, str] = {}


def _norm(text: str) -> str:
    return text.replace("{,}", "")


def _notebook_text(path: str) -> str:
    """Markdown cell sources + code cell OUTPUTS (not code source)."""
    nb = json.load(open(path, encoding="utf-8"))
    parts = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            parts.append("".join(cell.get("source", [])))
        for out in cell.get("outputs", []):
            parts.append("".join(out.get("text", [])))
            data = out.get("data", {})
            parts.append("".join(data.get("text/plain", [])))
            parts.append("".join(data.get("text/html", [])))
    return "".join(parts)


def _doc_text(rel_path: str) -> str:
    if rel_path not in _DOC_CACHE:
        path = rel_path if os.path.isabs(rel_path) else os.path.join(ROOT, rel_path)
        if path.endswith(".ipynb"):
            text = _notebook_text(path)
        else:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        _DOC_CACHE[rel_path] = _norm(text)
    return _DOC_CACHE[rel_path]


def _fmt(value, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def check_claim(claim: dict):
    """Return (status, needle, present_map) for a claim."""
    if claim.get("expect_missing") or claim.get("value") is None:
        return SKIP, None, {}
    targets = claim["appears_in"]
    needle = _fmt(float(claim["value"]), int(claim["decimals"]))
    present = {}
    for tgt in targets:
        try:
            present[tgt["file"]] = (needle in _doc_text(tgt["file"]), tgt.get("required", True))
        except FileNotFoundError:
            present[tgt["file"]] = (False, tgt.get("required", True))
    if len(targets) < 2:
        return SINGLE, needle, present
    missing_required = [f for f, (ok, req) in present.items() if req and not ok]
    return (DIVERGENT if missing_required else COHERENT), needle, present


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry = argv[0] if argv else REGISTRY
    with open(registry, encoding="utf-8") as fh:
        claims = yaml.safe_load(fh)

    width = max(len(c["claim_id"]) for c in claims)
    n_div = n_ok = n_single = n_skip = 0
    diverged = []
    print(f"coherence.py -- {len(claims)} claims from {os.path.relpath(registry, ROOT)}\n")
    for claim in claims:
        status, needle, present = check_claim(claim)
        if status == DIVERGENT:
            n_div += 1
            missing = [f for f, (ok, req) in present.items() if req and not ok]
            diverged.append((claim["claim_id"], needle, missing))
        elif status == COHERENT:
            n_ok += 1
        elif status == SINGLE:
            n_single += 1
        else:
            n_skip += 1

        line = f"  {status:11s} {claim['claim_id']:{width}s}"
        if needle is not None:
            docs = len(present)
            hits = sum(1 for ok, _ in present.values() if ok)
            line += f"  '{needle}' in {hits}/{docs} docs"
        if status == DIVERGENT:
            miss = [f for f, (ok, req) in present.items() if req and not ok]
            line += f"  -- MISSING from {', '.join(miss)}"
        print(line)

    print(f"\n{n_ok} coherent, {n_div} DIVERGENT, {n_single} single-doc, {n_skip} null.")
    if diverged:
        print("\nDIVERGENCES:")
        for cid, needle, missing in diverged:
            print(f"  - {cid}: '{needle}' missing from {', '.join(missing)}")
    return 1 if n_div else 0


if __name__ == "__main__":
    sys.exit(main())
