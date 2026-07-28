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

MISSING DOCUMENTS (brief 19 §3).  ``RESULTS.md`` is untracked by explicit
decision (Mattia, 2026-07-28), so on a clean checkout it is absent.  In the
registry its targets are marked ``required: false``.  When an OPTIONAL target is
absent the script prints

    DOCUMENT MISSING: RESULTS.md (untracked by design -- declared debt)

and CONTINUES: it does not crash and it does not silently pass.  Cross-checking
proceeds over the documents that DO exist; a claim that a missing document leaves
with fewer than two present documents can no longer be cross-checked and is
counted apart (``reduced by a missing document``).  A REQUIRED document that is
absent is still a divergence, not a declared debt.

Outcomes, one per claim:

  COHERENT       value present in every required, EXISTING document (>= 2 present)
  DIVERGENT      value missing from a required, existing document (a diverged copy),
                 or a required document is itself absent
  SINGLE DOC     fewer than two EXISTING documents -> nothing to cross-check
  SKIP (null)    the claim is a deliberately-missing cell (no value to compare)

Exit code is non-zero on any DIVERGENT.  A missing OPTIONAL document does NOT
fail the build.

DECLARED LIMITATION: the match is a normalised substring, so it cannot tell two
different quantities that share a printed string apart.  It reliably catches a
divergence in a required document (that document loses the string); it can miss
one masked by an unrelated occurrence of the same string in the same document.
This is the same class of limitation the symbol->parameter map guards against in
the registry, and it is why the ``appears_in`` map is built by real grep with
context, not assumed.

As with ``verify_paper.py`` this is a DETECTOR and is run against known-bad input
before it is trusted: the missing-document branch is exercised by temporarily
renaming ``RESULTS.md`` and re-running (brief 19 §3); a divergent copy injected
into one document exercises the DIVERGENT branch (brief-18 report).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

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


def _abs(rel_path: str) -> str:
    return rel_path if os.path.isabs(rel_path) else os.path.join(ROOT, rel_path)


def _doc_exists(rel_path: str) -> bool:
    return os.path.exists(_abs(rel_path))


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
        path = _abs(rel_path)
        if path.endswith(".ipynb"):
            text = _notebook_text(path)
        else:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        _DOC_CACHE[rel_path] = _norm(text)
    return _DOC_CACHE[rel_path]


def _fmt(value, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def document_required_map(claims):
    """file -> True if any claim marks it required, plus the set that is absent."""
    required_anywhere: dict[str, bool] = {}
    for claim in claims:
        for tgt in claim.get("appears_in", []):
            f = tgt["file"]
            required_anywhere.setdefault(f, False)
            if tgt.get("required", True):
                required_anywhere[f] = True
    missing = [f for f in required_anywhere if not _doc_exists(f)]
    return required_anywhere, missing


def check_claim(claim: dict):
    """Return (status, needle, present, reduced_by_missing).

    ``present`` maps file -> (exists, has_value, required).
    ``reduced_by_missing`` is True when a missing document is what drops the
    claim below two cross-checkable documents.
    """
    if claim.get("expect_missing") or claim.get("value") is None:
        return SKIP, None, {}, False
    targets = claim["appears_in"]
    needle = _fmt(float(claim["value"]), int(claim["decimals"]))
    present = {}
    for tgt in targets:
        f, req = tgt["file"], tgt.get("required", True)
        exists = _doc_exists(f)
        has = (needle in _doc_text(f)) if exists else False
        present[f] = (exists, has, req)

    n_existing = sum(1 for (e, _, _) in present.values() if e)
    any_missing = any(not e for (e, _, _) in present.values())
    if n_existing < 2:
        reduced = any_missing and len(targets) >= 2
        return SINGLE, needle, present, reduced
    # A required target is a divergence if it is absent OR lacks the value.
    missing_required = [f for f, (e, h, req) in present.items() if req and not (e and h)]
    status = DIVERGENT if missing_required else COHERENT
    return status, needle, present, False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry = argv[0] if argv else REGISTRY
    with open(registry, encoding="utf-8") as fh:
        claims = yaml.safe_load(fh)

    required_anywhere, missing_docs = document_required_map(claims)
    print(f"coherence.py -- {len(claims)} claims from {os.path.relpath(registry, ROOT)}\n")

    # Missing documents, reported once up front and never in silence.
    missing_optional, missing_required_docs = [], []
    for f in sorted(missing_docs):
        (missing_required_docs if required_anywhere[f] else missing_optional).append(f)
    for f in missing_optional:
        reason = ("untracked by design -- declared debt"
                  if os.path.basename(f) == "RESULTS.md"
                  else "optional target absent -- declared debt")
        print(f"DOCUMENT MISSING: {f} ({reason})")
    for f in missing_required_docs:
        print(f"DOCUMENT MISSING: {f} (REQUIRED target absent -- divergence, not a debt)")
    if missing_docs:
        print()

    width = max(len(c["claim_id"]) for c in claims)
    tally = Counter()
    diverged = []
    n_reduced = 0
    for claim in claims:
        status, needle, present, reduced = check_claim(claim)
        tally[status] += 1
        if reduced:
            n_reduced += 1
        if status == DIVERGENT:
            missing = [f for f, (e, h, req) in present.items() if req and not (e and h)]
            diverged.append((claim["claim_id"], needle, missing))

        line = f"  {status:11s} {claim['claim_id']:{width}s}"
        if needle is not None:
            n_exist = sum(1 for (e, _, _) in present.values() if e)
            hits = sum(1 for (e, h, _) in present.values() if e and h)
            line += f"  '{needle}' in {hits}/{n_exist} present docs"
            if reduced:
                line += "  (reduced by a missing document)"
        if status == DIVERGENT:
            miss = [f for f, (e, h, req) in present.items() if req and not (e and h)]
            line += f"  -- MISSING from {', '.join(miss)}"
        print(line)

    print(f"\n{tally[COHERENT]} coherent, {tally[DIVERGENT]} DIVERGENT, "
          f"{tally[SINGLE]} single-doc, {tally[SKIP]} null.")
    print(f"{len(missing_optional)} optional document(s) missing (declared debt); "
          f"{n_reduced} claim(s) reduced below cross-check by a missing document.")
    if diverged:
        print("\nDIVERGENCES:")
        for cid, needle, missing in diverged:
            print(f"  - {cid}: '{needle}' missing from {', '.join(missing)}")
    return 1 if tally[DIVERGENT] else 0


if __name__ == "__main__":
    sys.exit(main())
