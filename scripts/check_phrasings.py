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

HOW IT MATCHES.  A hit needs BOTH the subject (``H1``/``H2`` as a word) AND a matching
predicate WITHIN A PROXIMITY WINDOW of each other in the same paragraph.  A single word
is never enough: ``ipotesi ROVESCIATA`` (a hypothesis reversed by measurement, no
H1/H2) and the many innocent ``piu forte`` (``the strongest possible reconnection``)
must NOT be flagged, and are not.  Each paragraph is DEWRAPPED (its lines joined with a
space) before searching, so a formulation split across two wrapped lines IS caught --
the pre-b28-bis roadmap blockquote at METHODOLOGY.md had ``H2`` on one line and
``rovesciata`` on the next, and that is exactly the class this closes (Step 0 of the
merge brief).  Paragraphs are delimited by blank lines AND by list-item starts, so text
from different blocks is never joined; the proximity window (MAX_GAP chars) keeps a
distant, unrelated co-occurrence inside one long bullet from matching.

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
# A PARAGRAPH is a hit when subject and predicate both match within MAX_GAP chars of
# each other in its dewrapped text (see scan_lines).  All case-insensitive.
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


# Subject and predicate may sit on ADJACENT wrapped lines of the same paragraph
# (the b28-bis motivating case: the blockquote at METHODOLOGY.md:1722 had <<H2>> on
# one line and <<rovesciata>> on the next, so the same-line scan would have missed the
# very defect the brief was written for).  We therefore DEWRAP each paragraph (join
# its lines with a space) before searching -- the technique the b27-bis em-dash pass
# used -- delimiting paragraphs by blank lines AND by list-item starts, so wrapping is
# repaired WITHIN a logical block but text from different blocks is never joined (no
# cross-block false positives).  A PROXIMITY window then bounds how far apart the
# subject and predicate may be, so a giant bullet that merely mentions <<H2>> early and
# an unrelated <<cade>> 300 chars later is not a hit.
MAX_GAP = 90  # chars between subject and predicate: > a wrapped line, << a paragraph

# A markdown list item starts a new logical block even without a blank line before it.
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s|\d+\.\s)")


def _split_paragraphs(numbered):
    """``numbered``: list of (lineno, text).  Yield paragraphs (lists of the same),
    split on blank lines AND on list-item starts (each bullet is its own block)."""
    para = []
    for lineno, text in numbered:
        if text.strip() == "":
            if para:
                yield para
                para = []
            continue
        if para and _LIST_ITEM.match(text):
            yield para
            para = []
        para.append((lineno, text))
    if para:
        yield para


def _dewrap(para):
    """Join a paragraph's lines with single spaces; return (text, offsets) where
    offsets = [(char_start, lineno), ...] maps a char offset back to its source line."""
    parts, offsets, pos = [], [], 0
    for i, (lineno, text) in enumerate(para):
        if i:
            parts.append(" ")
            pos += 1
        offsets.append((pos, lineno))
        parts.append(text)
        pos += len(text)
    return "".join(parts), offsets


def _lineno_at(offset, offsets):
    ln = offsets[0][1]
    for start, lineno in offsets:
        if start <= offset:
            ln = lineno
        else:
            break
    return ln


def _proximity_pairs(text, subj_re, pred_re, gap):
    """All (subj_start, subj_end, pred_start, pred_end) pairs within ``gap`` chars
    (either order), earliest subject first."""
    subs = [m.span() for m in subj_re.finditer(text)]
    preds = [m.span() for m in pred_re.finditer(text)] if subs else []
    pairs = []
    for ss, se in subs:
        for ps, pe in preds:
            if ps >= se:
                dist = ps - se
            elif ss >= pe:
                dist = ss - pe
            else:
                dist = 0
            if dist <= gap:
                pairs.append((ss, se, ps, pe))
    pairs.sort(key=lambda p: p[0])
    return pairs


def _classify(source, text, frozen_reason, spans, subj_start, pred_start):
    """Status + reason for one (subject, predicate) pair in the dewrapped ``text``."""
    if frozen_reason is not None:
        return EXEMPT_FROZEN, frozen_reason
    lic = _license_for(source, text)
    if lic is not None:
        return EXEMPT_LICENSE, lic
    # A citation iff the operative word (the predicate) OR the subject sits inside a
    # quotation.  Checking the predicate matters when the paragraph also carries an
    # unquoted H1/H2 (e.g. "H1 no -- «H1 piu forte»"): the banned word is the mention.
    if _pos_quoted(text, pred_start, spans) or _pos_quoted(text, subj_start, spans):
        return EXEMPT_QUOTE, "formulazione entro virgolette/guillemet (citazione, non asserzione)"
    if NEGATION_MARKERS.search(text):
        return EXEMPT_NEGATION, "riga con marcatore di negazione/divieto"
    return FLAGGED, ""


def scan_lines(lines, source: str):
    """Classify every subject+predicate co-occurrence in ``lines``.

    Works per paragraph (dewrapped, so a formulation wrapped across adjacent lines is
    caught) with a proximity bound.  Returns hit dicts: {source, line, id, label,
    match, status, reason}; exemptions are attached (with reason), not dropped.  When a
    paragraph holds several pairs of one id, a genuine violation is surfaced even if a
    citation of the same phrase sits elsewhere in the block (a real FLAGGED wins).
    """
    hits = []
    frozen_reason = FROZEN_FILES.get(source)
    numbered = [(i, raw.rstrip("\n")) for i, raw in enumerate(lines, 1)]
    for para in _split_paragraphs(numbered):
        text, offsets = _dewrap(para)
        spans = _quote_spans(text)
        for bid, subj_re, pred_re, label in _BANNED_RES:
            pairs = _proximity_pairs(text, subj_re, pred_re, MAX_GAP)
            if not pairs:
                continue
            classified = [(p, _classify(source, text, frozen_reason, spans, p[0], p[2]))
                          for p in pairs]
            flagged = [c for c in classified if c[1][0] == FLAGGED]
            (ss, se, ps, pe), (status, reason) = flagged[0] if flagged else classified[0]
            snippet = text[min(ss, ps):max(se, pe)].strip()[:120]
            hits.append({"source": source, "line": _lineno_at(ss, offsets), "id": bid,
                         "label": label, "match": snippet, "status": status,
                         "reason": reason})
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
    print(f"Matching: per paragraph, DEWRAPPED (blank lines + list-item starts split "
          f"blocks), subject and predicate within {MAX_GAP} chars.")
    print("Quotation treated as citation (subject or predicate inside a mention):")
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
    """Known-bad + known-good injection (detector discipline, brief 28-bis).

    Each case is scanned as its OWN document, so paragraphs never bleed together.
    """
    print("check_phrasings.py --selftest -- injected known-bad/known-good\n")

    def st(lines, source="test.md"):
        return {h["status"] for h in scan_lines(lines, source)}

    def exempt_only(s):
        return bool(s) and FLAGGED not in s and s <= set(_EXEMPT)

    checks = [
        # -- known-BAD: must FLAG --
        ("[1] bare IT <<H1 esce piu forte>> is FLAGGED",
         st(["Risultato del brief: H1 esce più forte, e basta."]) == {FLAGGED}),
        ("[2] bare IT <<H2 rovesciata>> is FLAGGED",
         FLAGGED in st(["In sintesi: H2 rovesciata via Pigou."])),
        ("[3] bare EN <<H1 comes out stronger>> is FLAGGED",
         st(["The upshot is that H1 comes out stronger than before."]) == {FLAGGED}),
        # -- known-GOOD: citations of the ban, must be EXEMPT --
        ("[4] SAME phrase inside a guillemet ban citation is EXEMPT",
         exempt_only(st(["Mai scrivere «H1 esce più forte»: è un capo del bracket."]))),
        ("[5] ASCII-quoted <<H2 falls/holds>> citation is EXEMPT",
         exempt_only(st([r'The report never writes "H2 falls" or "H2 holds".']))),
        ("[6] licensed shorthand is EXEMPT (licensed)",
         EXEMPT_LICENSE in st(
             ["- H2, forma a due tempi (b17): il MECCANISMO è UCCISO e la "
              "CONCLUSIONE è ROVESCIATA -- due"], "METHODOLOGY.md")),
        ("[10] ban citation by negation marker (unquoted) is EXEMPT",
         EXEMPT_NEGATION in st(
             ["Vietato asserire che H1 esce più forte senza qualificarlo."])),
        ("[11] a violation inside run_brief17.py is EXEMPT (frozen record)",
         st(["    * ... -> H1 comes out STRONGER: it survives the respecification"],
            "scripts/run_brief17.py") == {EXEMPT_FROZEN}),
        # -- look-alikes: must NOT be hits --
        ("[7] innocent 'piu forte' without H1 is NOT a hit",
         st(["E il ricongiungimento più forte possibile con Teglio."]) == set()),
        ("[8] 'ipotesi rovesciata' without H1/H2 is NOT a hit",
         st(["Punto 10-bis: ipotesi ROVESCIATA -- a beta<0.1 zero wage-led."]) == set()),
        ("[9] neutral 'holds' without H2 is NOT a hit",
         st(["The committee holds a meeting; H3 is irrelevant."]) == set()),
        # -- Step 0: cross-line matching, and its cross-paragraph guard --
        ("[12] forbidden phrase WRAPPED across two lines is FLAGGED",
         st(["Il probe uccide il meccanismo di H2, e la sua",
             "conclusione è rovesciata via Pigou."]) == {FLAGGED}),
        ("[13] subject and predicate in DIFFERENT paragraphs are NOT joined",
         st(["Un paragrafo che nomina soltanto H2.",
             "",
             "Un altro in cui qualcosa è rovesciata."]) == set()),
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
