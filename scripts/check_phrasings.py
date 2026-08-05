#!/usr/bin/env python
r"""check_phrasings.py -- flag the FORBIDDEN H1/H2 formulations, with declared exemptions.

Brief 28-bis.  ``coherence.py`` reports 0 DIVERGENT and never saw the problem: it
compares the NUMBERS across documents, not the FORMULATIONS.  Meanwhile two retired
formulations survived OUTSIDE ``paper/`` -- in ``METHODOLOGY.md`` -- because the b28
acceptance criterion "forbidden formulations avoided" was checked ONLY on ``paper/``:
correct within its perimeter and false outside it.  This detector inspects the
formulations, over a perimeter it PRINTS rather than assumes.

WHAT IS FORBIDDEN.  Two hypotheses, each with a two-arm reality the single-arm
phrasing hides:

  H2 (numeraire / Pigou bracket).  The outcome is a BRACKET between two pass-through
  conventions, NEITHER anchored.  Forbidden: <<H2 cade>>, <<H2 tiene>>,
  <<H2 e rovesciata>> (EN: ``H2 falls`` / ``H2 holds`` / ``H2 is overturned``) --
  all three are one arm of the bracket passed off as the bracket (METHODOLOGY.md, the
  H2 ban registered with the b22 record).

  H1 (accelerator margin).  Forbidden: <<H1 (esce) piu forte>> (EN: ``H1 comes out
  stronger``) and <<H1 sopravvive alla respecifica del canale che porta il 64% della
  varianza>> (which confuses the b13/b14 conditional index with the marginal one).
  Obligatory instead: the TWO-TEMPO conclusion -- (a) H1 is robust to the specification
  of the accelerator SIGNAL; (b) H1 is load-bearing on the STRENGTH of the accelerator
  (margin resolved only for beta >= 0.5, default 0.5 on the edge; at lambda_u = 0 the
  margin VANISHES, it does not invert).  The H1 ban is registered symmetrically next to
  the H2 ban in METHODOLOGY.md (b28-bis).

HOW IT MATCHES.  Per line, a hit needs BOTH the subject (``H1``/``H2`` as a word) AND
a matching predicate on the SAME line.  A single word is never enough: ``ipotesi
ROVESCIATA`` (a hypothesis reversed by measurement, no H1/H2) and the many innocent
``piu forte`` (``the strongest possible reconnection``) must NOT be flagged, and are
not.  Same-line co-occurrence is a declared LIMITATION: a subject and predicate split
across two lines are not caught (the pre-b28-bis roadmap blockquote at METHODOLOGY.md
had ``H2`` on one line and ``rovesciata`` on the next -- it was corrected by hand in
this brief, not left to the detector).

EXEMPTIONS -- the part that decides whether the tool is usable.  A grep without them
produces, on this repo's documents, a MAJORITY of false positives (the ban itself, its
citations, the pre-registered gate rule).  Each exemption is PRINTED with its reason, so
the output shows WHAT was excluded and WHY; a silent exemption is a hole.

  EXEMPT (frozen record)   whole FILE is exempt: ``scripts/run_brief17.py`` carries the
                           pre-registered gate rule (``H1 comes out STRONGER`` is the
                           hypothetical branch frozen in the source BEFORE the runs --
                           falsifying it is worse than the defect); and this detector,
                           whose patterns and --selftest fixtures ARE the ban.
  EXEMPT (citation)        the forbidden phrase is a QUOTATION, not an assertion: the
                           subject sits inside <<...>> / "..." / ``...'' , or the line
                           carries a negation/ban marker (<<Mai>>, <<vietat->>,
                           ``forbidden``, ``never``, <<non compare>>, <<Nessun->>).
  EXEMPT (licensed)        the licensed process-shorthand of METHODOLOGY.md: the b21
                           record entry in section 8 uses <<rovesciata>> as shorthand
                           for the ON extreme, licensed by the note to the H2/H1 ban
                           (b22 entry); in the paper only the bracket lives.  Listed
                           per occurrence (by a stable content substring, not a line
                           number) with its license.

CLOSURE (brief 28-bis).  Perimeter, exemption policy and final count are all PRINTED,
not asserted in prose.  Exit code != 0 on any surviving violation.

DETECTOR DISCIPLINE.  Run against known-bad input before it is trusted:
``python check_phrasings.py --selftest`` injects <<H1 esce piu forte>> bare (must be
FLAGGED), the SAME phrase inside a citation of the ban (must be EXEMPT), H2 forms, the
licensed shorthand, a frozen-file hit, and innocent look-alikes (``ipotesi rovesciata``,
bare ``piu forte``), and asserts each outcome.  A detector that cannot tell the two
apart measures nothing.
"""
from __future__ import annotations

import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))


# --------------------------------------------------------------------------- #
# Perimeter -- PRINTED, not assumed (brief 28-bis).  The forbidden-formulation
# criterion applies to the sources of truth, NOT to the working briefs at the
# repo root (brief_*.md, istruzioni_progetto.md, ...), which are out of scope by
# construction -- and that is exactly why the perimeter is printed.
# --------------------------------------------------------------------------- #
PERIMETER_ROOTS = [
    "paper/ (*.tex, *.md)",
    "METHODOLOGY.md",
    "README.md",
    "docs/ (*.md)",
    "parameter_notes.md",
    "scripts/ (*.py, *.yaml)",
]


def _target_files():
    """Resolve the declared perimeter to a concrete, sorted, de-duplicated list."""
    paths = []
    for name in ("METHODOLOGY.md", "README.md", "parameter_notes.md"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            paths.append(p)
    paths += glob.glob(os.path.join(ROOT, "paper", "**", "*.tex"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "paper", "**", "*.md"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "scripts", "**", "*.py"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "scripts", "**", "*.yaml"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "scripts", "**", "*.yml"), recursive=True)
    return sorted(set(paths))


def _rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Forbidden formulations: (id, subject-regex, predicate-regex, human label).
# A LINE is a hit when subject AND predicate both match on it.  All case-insensitive.
# --------------------------------------------------------------------------- #
BANNED = [
    # -- H2, Italian --
    ("h2-cade",        r"\bH2\b", r"\bcade\b",                          "<<H2 cade>> (IT)"),
    ("h2-tiene",       r"\bH2\b", r"\btiene\b",                         "<<H2 tiene>> (IT)"),
    ("h2-rovesciata",  r"\bH2\b", r"rovesciat\w*",                      "<<H2 e rovesciata>> (IT)"),
    # -- H2, English (the paper is in English) --
    ("h2-falls",       r"\bH2\b", r"\bfalls?\b",                        "<<H2 falls>> (EN)"),
    ("h2-holds",       r"\bH2\b", r"\bholds?\b",                        "<<H2 holds>> (EN)"),
    ("h2-overturned",  r"\bH2\b", r"overturn\w*",                       "<<H2 is overturned>> (EN)"),
    # -- H1, Italian --
    ("h1-piu-forte",   r"\bH1\b", r"più\s+forte",                  "<<H1 (esce) piu forte>> (IT)"),
    ("h1-canale",      r"\bH1\b", r"sopravvive\w*[^.\n]{0,60}canale",   "<<H1 sopravvive al canale...>> (confusione condizionale/marginale)"),
    # -- H1, English --
    ("h1-stronger",    r"\bH1\b", r"comes?\s+out\s+stronger",          "<<H1 comes out stronger>> (EN)"),
    ("h1-respec",      r"\bH1\b", r"survives?[^.\n]{0,60}respecification", "<<H1 survives the respecification...>> (EN)"),
]
_BANNED_RES = [(bid, re.compile(subj, re.I), re.compile(pred, re.I), label)
               for bid, subj, pred, label in BANNED]


# --------------------------------------------------------------------------- #
# Exemptions -- DECLARED and PRINTED.
# --------------------------------------------------------------------------- #

# (1) Frozen records: exempt by FILE, with the reason in the source.
FROZEN_FILES = {
    "scripts/run_brief17.py": (
        "regola del gate PRE-REGISTRATA (brief 17 sec.4/sec.5): il ramo ipotetico "
        "<<H1 comes out STRONGER>> e congelato nel sorgente PRIMA dei run; falsificarlo "
        "sarebbe peggio del difetto che si corregge"),
    "scripts/check_phrasings.py": (
        "questo detector: i pattern e le fixture di --selftest SONO il divieto"),
}

# (2) Citation of the ban -- by negation/ban marker on the line.  Quotation is
#     handled separately via delimiter spans (see _QUOTE_RES).
NEGATION_MARKERS = re.compile(
    r"\bMai\b|vietat|forbidden|\bnever\b|non\s+compar|\b[Nn]essun", re.I)

# Quotation delimiters used to MENTION (not assert) a formulation.  ASCII "..." and
# LaTeX ``...'' are balanced same-line spans.  Guillemets <<...>> are handled by a
# prefix-balance count instead of a regex, so a guillemet quotation that SPANS TWO
# LINES (as in the ``NON <<H1 sopravvive al canale che\n porta il 64%>>`` citation)
# is caught too, without carrying state that a stray guillemet elsewhere could poison.
_QUOTE_RES = [
    re.compile(r'"[^"\n]*"'),                    # " ... "
    re.compile(r"``[^'\n]*''"),                  # `` ... ''
]


def _pos_quoted(line: str, pos: int, ascii_latex_spans) -> bool:
    """Is the character at ``pos`` inside a quotation (a MENTION, not an assertion)?"""
    if _in_any_span(pos, ascii_latex_spans):
        return True
    # Inside a guillemet region iff the prefix has more openings than closings
    # (works for same-line <<...>> and for a quotation that opens here and closes
    # on a later line).
    prefix = line[:pos]
    return prefix.count("«") > prefix.count("»")

# (3) Licensed process-shorthand: keyed by a STABLE content substring (robust to
#     line-number drift), each listed with its license.  This is the b21 record
#     entry in METHODOLOGY.md section 8, licensed by the note to the H2/H1 ban.
LICENSED_SHORTHAND = [
    {
        "file": "METHODOLOGY.md",
        "contains": "il MECCANISMO è UCCISO e la CONCLUSIONE è ROVESCIATA",
        "license": (
            "voce b21 in sec.8: <<rovesciata>> = shorthand di processo per l'estremo ON, "
            "licenziato dalla nota al divieto H2/H1 (voce b22); nel paper vive solo il bracket"),
    },
]

FLAGGED = "FLAGGED"
EXEMPT_FROZEN = "EXEMPT (frozen record)"
EXEMPT_QUOTE = "EXEMPT (citation: quotation)"
EXEMPT_NEGATION = "EXEMPT (citation: negation marker)"
EXEMPT_LICENSE = "EXEMPT (licensed shorthand)"
_EXEMPT = (EXEMPT_FROZEN, EXEMPT_QUOTE, EXEMPT_NEGATION, EXEMPT_LICENSE)


def _quote_spans(line: str):
    spans = []
    for rx in _QUOTE_RES:
        spans.extend((m.start(), m.end()) for m in rx.finditer(line))
    return spans


def _in_any_span(pos: int, spans) -> bool:
    return any(a <= pos < b for a, b in spans)


def _license_for(source: str, line: str):
    for entry in LICENSED_SHORTHAND:
        if entry["file"] == source and entry["contains"] in line:
            return entry["license"]
    return None


def scan_lines(lines, source: str):
    """Classify every subject+predicate co-occurrence in ``lines``.

    Returns a list of hit dicts: {source, line, id, label, match, status, reason}.
    Exemptions are attached (with reason) rather than dropped, so the output is
    auditable.
    """
    hits = []
    frozen_reason = FROZEN_FILES.get(source)
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        spans = None  # computed lazily, once per line that has a hit
        for bid, subj_re, pred_re, label in _BANNED_RES:
            msubj = subj_re.search(line)
            if not msubj:
                continue
            mpred = pred_re.search(line)
            if not mpred:
                continue
            snippet = line[min(msubj.start(), mpred.start()):
                           max(msubj.end(), mpred.end())].strip()
            if frozen_reason is not None:
                status, reason = EXEMPT_FROZEN, frozen_reason
            else:
                lic = _license_for(source, line)
                if lic is not None:
                    status, reason = EXEMPT_LICENSE, lic
                else:
                    if spans is None:
                        spans = _quote_spans(line)
                    # A citation iff the operative word (the predicate) OR the subject
                    # sits inside a quotation.  Checking the predicate matters when the
                    # line also carries an unquoted H1/H2 earlier (e.g. "H1 no -- «H1
                    # piu forte»"): the banned word is what is being mentioned.
                    if (_pos_quoted(line, mpred.start(), spans)
                            or _pos_quoted(line, msubj.start(), spans)):
                        status, reason = EXEMPT_QUOTE, "formulazione entro virgolette/guillemet (citazione, non asserzione)"
                    elif NEGATION_MARKERS.search(line):
                        status, reason = EXEMPT_NEGATION, "riga con marcatore di negazione/divieto"
                    else:
                        status, reason = FLAGGED, ""
            hits.append({"source": source, "line": lineno, "id": bid, "label": label,
                         "match": snippet, "status": status, "reason": reason})
    return hits


def run() -> int:
    files = _target_files()
    all_hits = []
    for path in files:
        rel = _rel(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            all_hits.extend(scan_lines(fh.read().splitlines(), rel))

    flagged = [h for h in all_hits if h["status"] == FLAGGED]
    exempt = [h for h in all_hits if h["status"] in _EXEMPT]

    print("=" * 78)
    print("check_phrasings.py -- forbidden H1/H2 formulations (brief 28-bis)")
    print("=" * 78)
    print("PERIMETER (printed, not assumed):")
    for r in PERIMETER_ROOTS:
        print(f"  - {r}")
    print(f"Scanned {len(files)} file(s):")
    for path in files:
        print(f"    {_rel(path)}")

    print(f"\n-- FLAGGED forbidden formulations: {len(flagged)} --")
    for h in flagged:
        print(f"  {h['source']}:{h['line']}  {h['label']}  ->  '{h['match']}'")
    if not flagged:
        print("  (none)")

    # Exemptions, grouped so it is visible WHAT was excluded and WHY.
    for status in _EXEMPT:
        group = [h for h in exempt if h["status"] == status]
        print(f"\n-- {status}: {len(group)} --")
        if not group:
            print("  (none)")
            continue
        for h in group:
            print(f"  {h['source']}:{h['line']}  {h['label']}  ->  '{h['match']}'")
            print(f"        reason: {h['reason']}")

    # The declared exemption POLICY, printed in full (auditable even when unused).
    print("\n" + "-" * 78)
    print("DECLARED EXEMPTION POLICY")
    print("-" * 78)
    print("Frozen files (whole-file exemption):")
    for f, reason in FROZEN_FILES.items():
        print(f"  {f}\n      {reason}")
    print("Quotation treated as citation (subject inside a mention):")
    print("  «...» (guillemets, incl. cross-line via prefix balance), "
          "\"...\" (ASCII), ``...'' (LaTeX)")
    print(f"Negation/ban markers (line-level citation): {NEGATION_MARKERS.pattern}")
    print("Licensed process-shorthand (by stable content substring):")
    for entry in LICENSED_SHORTHAND:
        print(f"  {entry['file']}  contains: '{entry['contains']}'")
        print(f"      license: {entry['license']}")

    print("\n" + "-" * 78)
    print(f"FINAL COUNT: {len(flagged)} forbidden formulation(s) outside the exemptions.")
    print("-" * 78)
    return 1 if flagged else 0


def selftest() -> int:
    """Known-bad + known-good injection (detector discipline, brief 28-bis)."""
    print("check_phrasings.py --selftest -- injected known-bad/known-good\n")

    # Pass A: the core lines, scanned AS IF they were METHODOLOGY.md (so the
    # licensed-shorthand registry, which is keyed to that file, is in play).
    lines = [
        # [1] bare IT H1 violation                                   -> FLAGGED
        "Risultato del brief: H1 esce più forte, e basta.",
        # [2] bare IT H2 violation                                   -> FLAGGED
        r"In sintesi: H2 rovesciata via Pigou.",
        # [3] bare EN violation                                      -> FLAGGED
        r"The upshot is that H1 comes out stronger than before.",
        # [4] SAME H1 phrase inside a citation of the ban (guillemet + Mai) -> EXEMPT
        "Mai scrivere «H1 esce più forte»: è un capo del bracket.",
        # [5] ASCII-quoted ban citation with 'never'                 -> EXEMPT
        r'The report never writes "H2 falls" or "H2 holds".',
        # [6] the licensed shorthand line (matches the registry substring) -> EXEMPT
        "- H2, forma a due tempi (b17): il MECCANISMO è UCCISO e la CONCLUSIONE è ROVESCIATA -- due",
        # [7] innocent 'piu forte' with NO H1                        -> not a hit
        "E il ricongiungimento più forte possibile con Teglio.",
        # [8] 'ipotesi rovesciata' with NO H1/H2                     -> not a hit
        "Punto 10-bis: ipotesi ROVESCIATA -- a beta<0.1 zero punti wage-led.",
        # [9] neutral EN 'holds' with no H2                          -> not a hit
        r"The committee holds a meeting; H3 is irrelevant.",
        # [10] ban citation by NEGATION MARKER, not quoted (<<vietato>>) -> EXEMPT
        "Vietato asserire che H1 esce più forte senza qualificarlo.",
    ]
    hits = scan_lines(lines, "METHODOLOGY.md")
    by_line = {}
    for h in hits:
        by_line.setdefault(h["line"], []).append(h)

    def status_on(n):
        return {h["status"] for h in by_line.get(n, [])}

    # Pass B: a real violation inside the frozen file -> EXEMPT (frozen record).
    frozen_hits = scan_lines(
        [r"    * ... -> H1 comes out STRONGER: it survives the respecification"],
        "scripts/run_brief17.py")
    frozen_ok = bool(frozen_hits) and all(h["status"] == EXEMPT_FROZEN
                                          for h in frozen_hits)

    checks = [
        ("[1] bare IT <<H1 esce piu forte>> is FLAGGED",
         status_on(1) == {FLAGGED}),
        ("[2] bare IT <<H2 rovesciata>> is FLAGGED",
         FLAGGED in status_on(2)),
        ("[3] bare EN <<H1 comes out stronger>> is FLAGGED",
         status_on(3) == {FLAGGED}),
        ("[4] SAME phrase inside a ban citation is EXEMPT (not flagged)",
         bool(status_on(4)) and FLAGGED not in status_on(4)
         and status_on(4) <= set(_EXEMPT)),
        ("[5] ASCII-quoted <<H2 falls/holds>> citation is EXEMPT",
         bool(status_on(5)) and FLAGGED not in status_on(5)),
        ("[6] licensed shorthand is EXEMPT (licensed)",
         EXEMPT_LICENSE in status_on(6) and FLAGGED not in status_on(6)),
        ("[7] innocent 'piu forte' without H1 is NOT a hit",
         status_on(7) == set()),
        ("[8] 'ipotesi rovesciata' without H1/H2 is NOT a hit",
         status_on(8) == set()),
        ("[9] neutral 'holds' without H2 is NOT a hit",
         status_on(9) == set()),
        ("[10] ban citation by negation marker (unquoted) is EXEMPT",
         EXEMPT_NEGATION in status_on(10) and FLAGGED not in status_on(10)),
        ("[B] a violation inside run_brief17.py is EXEMPT (frozen record)",
         frozen_ok),
    ]
    ok = True
    for label, passed in checks:
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
    print(f"\n  SELFTEST VERDICT: "
          f"{'ALL PASS -- detector trusted' if ok else 'FAIL -- stop'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return selftest()
    return run()


if __name__ == "__main__":
    sys.exit(main())
