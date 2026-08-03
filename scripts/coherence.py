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

UNTRACKED / MISSING DOCUMENTS (brief 19 §3; detector repaired in brief 27).
``RESULTS.md`` is untracked by explicit decision (Mattia, 2026-07-28).  The check
is on the GIT TRACKING STATE (``git ls-files --error-unmatch``), NOT on the file's
existence on disk -- because the two disagree exactly on the machine where the
document lives.  On a fresh clone ``RESULTS.md`` is absent; on the author's machine
it is present but untracked.  An existence check therefore fired on the clone and
went SILENT on the author's machine -- the failure mode of a detector that stops
being read (the 8-ULP pin).  Basing it on tracking makes it fire IDENTICALLY in
both places::

    DOCUMENT UNTRACKED: RESULTS.md (untracked by design -- declared debt; git does
                        not track it whether or not it is on disk)

An UNTRACKED optional document is a declared debt and does NOT fail the build; a
TRACKED document that is absent from disk is a ``DOCUMENT MISSING`` (a real problem,
a divergence if the target is required).  Cross-checking proceeds over the
documents that exist on disk; a claim left with fewer than two present documents is
counted apart (``reduced by a missing document``).

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
before it is trusted: ``python coherence.py --selftest`` creates a present-but-
UNTRACKED scratch file and asserts the tracking check FIRES on it (and does not on
a tracked file), which is the exact condition that used to pass in silence.  A
divergent copy injected into one document exercises the DIVERGENT branch (brief-18
report).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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


_TRACKED_CACHE: dict[str, bool] = {}


def _doc_tracked(rel_path: str) -> bool:
    """True iff git tracks the file -- the check that is machine-independent.

    ``git ls-files --error-unmatch <path>`` exits 0 iff the path is tracked, and
    non-zero (with a message on stderr) iff it is not.  This is deliberately NOT
    ``os.path.exists``: an untracked file present on the author's disk is absent on
    a fresh clone, so an existence check disagrees between the two -- exactly the
    silence this detector must not have (brief 27, §E).
    """
    if rel_path not in _TRACKED_CACHE:
        try:
            r = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", _abs(rel_path)],
                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            _TRACKED_CACHE[rel_path] = (r.returncode == 0)
        except FileNotFoundError:
            # git not on PATH: cannot prove tracking -- fail LOUD, not silent.
            _TRACKED_CACHE[rel_path] = False
    return _TRACKED_CACHE[rel_path]


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
    """file -> required?, plus the untracked set and the tracked-but-absent set.

    ``untracked`` (git does not track it, on disk or not) is the declared-debt branch,
    machine-independent by construction.  ``tracked_absent`` (git tracks it yet it is
    gone from disk) is a real problem -- a divergence if the target is required.
    """
    required_anywhere: dict[str, bool] = {}
    for claim in claims:
        for tgt in claim.get("appears_in", []):
            f = tgt["file"]
            required_anywhere.setdefault(f, False)
            if tgt.get("required", True):
                required_anywhere[f] = True
    untracked = [f for f in required_anywhere if not _doc_tracked(f)]
    tracked_absent = [f for f in required_anywhere
                      if _doc_tracked(f) and not _doc_exists(f)]
    return required_anywhere, untracked, tracked_absent


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


def selftest() -> int:
    """Prove the tracking check FIRES on a present-but-UNTRACKED file.

    This is the exact condition the old existence check passed in silence: a file
    that is on disk yet not tracked by git.  Model of ``verify_paper.py --selftest``.
    """
    print("coherence.py --selftest -- known-bad input: a present-but-untracked file\n")
    ok = True

    # A freshly written scratch file in the repo: present on disk, NOT tracked.
    fd, abspath = tempfile.mkstemp(prefix="_coherence_selftest_untracked_",
                                   suffix=".tmp", dir=ROOT)
    os.close(fd)
    rel = os.path.relpath(abspath, ROOT).replace(os.sep, "/")
    _TRACKED_CACHE.clear()
    try:
        present = _doc_exists(rel)
        tracked = _doc_tracked(rel)
        print(f"  [1] scratch file present={present} tracked={tracked}")
        if present and not tracked:
            print("        expected present & UNTRACKED (detector must fire) => PASS")
        else:
            print("        expected present & untracked                     => FAIL")
            ok = False

        # The report path must list it as untracked (not silent), via a mini registry.
        fake = [{"claim_id": "x", "value": 1.0, "decimals": 1,
                 "appears_in": [{"file": rel, "required": False}]}]
        _, untracked, missing = document_required_map(fake)
        print(f"  [2] document_required_map -> untracked={untracked} missing={missing}")
        if rel in untracked and rel not in missing:
            print("        expected in UNTRACKED, not in missing            => PASS")
        else:
            print("        expected the untracked file to be flagged        => FAIL")
            ok = False

        # A control: a genuinely tracked file must NOT be flagged untracked.
        ctrl = "scripts/coherence.py"
        ctrl_tracked = _doc_tracked(ctrl)
        print(f"  [3] control '{ctrl}' tracked={ctrl_tracked}")
        if ctrl_tracked:
            print("        expected TRACKED (no false positive)             => PASS")
        else:
            print("        expected the tracked control to read tracked     => FAIL")
            ok = False
    finally:
        os.remove(abspath)
        _TRACKED_CACHE.clear()

    print("\n  SELFTEST VERDICT:", "ALL PASS -- untracked detector trusted"
          if ok else "FAILED -- do not trust this run")
    return 0 if ok else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return selftest()
    registry = argv[0] if argv else REGISTRY
    with open(registry, encoding="utf-8") as fh:
        claims = yaml.safe_load(fh)

    required_anywhere, untracked_docs, missing_docs = document_required_map(claims)
    print(f"coherence.py -- {len(claims)} claims from {os.path.relpath(registry, ROOT)}\n")

    # Untracked / missing documents, reported once up front and never in silence.
    # The gate is git tracking, not disk existence (brief 27 §E), so it fires
    # identically on the author's machine (present, untracked) and a fresh clone
    # (absent, untracked).
    for f in sorted(untracked_docs):
        on_disk = "present on disk" if _doc_exists(f) else "absent on disk"
        if required_anywhere[f]:
            print(f"DOCUMENT UNTRACKED: {f} (REQUIRED target not tracked by git, "
                  f"{on_disk} -- not part of the reproducible repo)")
        else:
            print(f"DOCUMENT UNTRACKED: {f} (untracked by design -- declared debt; "
                  f"{on_disk}; git does not track it either way)")
    for f in sorted(missing_docs):
        kind = ("REQUIRED target absent -- divergence, not a debt"
                if required_anywhere[f] else "optional target absent -- declared debt")
        print(f"DOCUMENT MISSING: {f} ({kind})")
    if untracked_docs or missing_docs:
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
    n_untracked_debt = sum(1 for f in untracked_docs if not required_anywhere[f])
    print(f"{len(untracked_docs)} untracked document(s) ({n_untracked_debt} declared "
          f"debt), {len(missing_docs)} tracked-but-absent; "
          f"{n_reduced} claim(s) reduced below cross-check.")
    if diverged:
        print("\nDIVERGENCES:")
        for cid, needle, missing in diverged:
            print(f"  - {cid}: '{needle}' missing from {', '.join(missing)}")
    return 1 if tally[DIVERGENT] else 0


if __name__ == "__main__":
    sys.exit(main())
