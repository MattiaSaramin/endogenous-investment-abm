#!/usr/bin/env python
r"""check_anglicization.py -- flag British spellings by ROOT, not by inflection.

Brief 27-quinquies Phase 1.  The brief 27-quater anglicization pass declared
"0 British forms", yet two survived, both in visible places:

    04_calibration.tex : \multicolumn{3}{l}{Modelling choices, ...}   (-ll- form)
    12_conclusion.tex  : more demand is not a stabiliser              (-iser, in
                                                                       the conclusion)

Why 27-quater missed them: it built its substitution list from the inflections it
had ALREADY OBSERVED and then checked THAT LIST.  A name-of-agent (``-iser``) and
a capitalised form inside ``\multicolumn`` were not in the observed list, so the
final check verified its own input rather than the declared property.  That is the
invariant-6 failure: a check that reports success without inspecting the thing is
worse than no check.  This detector inspects the thing.

WHAT IT DOES.  For each British ROOT (case-insensitive) it matches the root
followed by an EXPLICITLY ENUMERATED inflection set

    {'', e, es, ed, ing, er, ers, ation, ations}

across the whole paper body -- section titles, captions, table cells,
``\multicolumn`` and the frontmatter (the LaTeX table of contents is generated
from the section titles scanned here, so it is covered transitively).  A match is
classified:

    FLAGGED       a British form to convert            -> FAILURE (exit 1)
    FALSE-FRIEND  a word identical in both variants that a root catches by
                  accident (declared list below, printed in the output so the
                  run shows WHAT was excluded and WHY)
    EXEMPT        inside a generated ``do not hand-edit`` block, or inside a
                  literal quotation (``...'' / \enquote{...})

DECLARED FALSE FRIENDS.  ``analysis``/``analyses``/... , ``realism``, the NOUNS
``emphasis``/``hypothesis``/``synthesis`` (only the VERBS emphasise/hypothesise/
synthesise are British -- distinguished by inflection, not by root), and the
``-ise``-looking Latin/Greek words ``surprise``/``otherwise``/``comprise``/...
that a broader matcher would trip on.

  DECLARED ADDITION over the brief's enumerated list (surfaced by running the
  check, which is how a false friend is meant to be found): ``cancellation`` /
  ``cancellations``.  ``cancel`` doubles the -l- in the ``-ation`` form in BOTH
  variants (American *cancellation*, not *cancelation*), so root ``cancell`` +
  ``ation`` is a false positive, not a British marker.  The paper's one hit is
  "catastrophic cancellation" (a_validation.tex), a numerical-analysis term.
  Recorded here, not silently special-cased in the inflection set.

EXEMPTIONS unchanged from 27-quater: literal quotations of other authors,
``references.bib`` (not a scanned file, hence out of scope by construction),
proper names (``Blanchflower``/``Oswald`` -- no root matches them), and generated
blocks carrying the ``do not hand-edit`` marker.

CLOSURE CRITERION (brief 1.4): the final flagged count is PRINTED BY THIS SCRIPT,
not asserted in prose.  Expected 0 outside the exemptions, with the false friends
listed so the exclusions are auditable.

DETECTOR DISCIPLINE (brief 1.2, invariants 5/6): this is a detector, so it is run
against known-bad input before it is trusted --
``python check_anglicization.py --selftest`` injects British forms (must be
FLAGGED), false friends and American forms (must NOT be flagged), a generated
block and a quotation (must be EXEMPT), and asserts each outcome.
"""
from __future__ import annotations

import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))

# British roots (brief 27-quinquies 1.2), searched case-insensitively.  ``realis``
# is deliberately NOT here: the brief's root list omits it, and "realise" is
# verified absent from the paper (only American "realized" and the universal
# "realism"/"realistic" occur); its false friends are kept below defensively.
ROOTS = [
    # -our / -re / -ll- (British doubling) / -ol
    "labour", "behaviour", "colour", "favour", "honour", "neighbour",
    "centre", "metre", "litre", "theatre", "fibre",
    "modell", "travell", "labell", "signall", "cancell", "fuell", "enrol",
    # -is- family (British -ise / -isation)
    "organis", "recognis", "normalis", "maximis", "minimis", "utilis",
    "stabilis", "marginalis", "summaris", "characteris", "parametris",
    "parameteris", "endogenis", "exogenis", "initialis", "generalis",
    "specialis", "formalis", "rationalis", "prioritis", "criticis", "penalis",
    "capitalis", "emphasis", "hypothesis", "synthesis",
    # -yse family (British -yse)
    "analys", "paralys", "catalys",
]

# Inflection set, enumerated explicitly (brief 1.2).  Longest-first so the
# alternation is greedy at the word boundary (``organisations`` takes ``ations``,
# not ``ation`` + stranded ``s``).  The empty inflection is the trailing ``?``.
INFLECTIONS = ["ations", "ation", "ers", "er", "es", "ed", "ing", "e"]

# Words identical in both variants that a root match catches by accident.
# Lower-cased exact tokens, subtracted BEFORE the flagged count and printed.
FALSE_FRIENDS = {
    # analys*/-yse nouns and adjectives (the VERB "analyse" is NOT here -- it is
    # British and stays flaggable; only the noun family is a false friend)
    "analysis", "analyses", "analyst", "analysts", "analytical",
    "realism", "realistic",
    # emphasis/hypothesis/synthesis are NOUNS identical in both variants; only
    # the verbs emphasise/hypothesise/synthesise are British (kept flaggable)
    "emphasis", "hypothesis", "hypotheses", "synthesis",
    # -ise-looking Latin/Greek words a broader matcher would trip on
    "surprise", "otherwise", "comprise", "comprises", "precise", "concise",
    "wise", "exercise", "enterprise", "expertise", "promise", "compromise",
    "revise", "supervise", "devise", "arise", "arises", "rise", "rises",
    # DECLARED ADDITION (see module docstring): universal double-l -ation form
    "cancellation", "cancellations",
}

GEN_MARKER = re.compile(r"do not hand-edit", re.IGNORECASE)
GEN_END = re.compile(r"\\bottomrule|\\end\{tabular\}")

# Literal-quotation spans on a single line: LaTeX double quotes ``...'' and
# \enquote{...}.  Single-quote `...' spans are NOT matched (apostrophes and
# math primes make them ambiguous); cross-line quotations are a declared
# limitation -- none of the paper's root hits falls inside one.
_QUOTE_SPANS = [
    re.compile(r"``.*?''"),
    re.compile(r"\\enquote\{.*?\}"),
]

FLAGGED = "FLAGGED"
FALSE_FRIEND = "FALSE-FRIEND"
EXEMPT_GEN = "EXEMPT (generated block)"
EXEMPT_QUOTE = "EXEMPT (quotation)"

_ALT = "|".join(INFLECTIONS)
_ROOT_RES = [(root, re.compile(r"\b" + re.escape(root) + r"(?:" + _ALT + r")?\b",
                               re.IGNORECASE))
             for root in ROOTS]


def _quote_intervals(line: str):
    spans = []
    for rx in _QUOTE_SPANS:
        spans.extend((m.start(), m.end()) for m in rx.finditer(line))
    return spans


def _in_spans(pos: int, spans) -> bool:
    return any(a <= pos < b for a, b in spans)


def scan_lines(lines, source: str):
    """Classify every root+inflection hit in ``lines``.

    Returns a list of hit dicts: {source, line, token, root, status}.  Generated
    ``do not hand-edit`` blocks and single-line quotations are marked EXEMPT (and
    reported) rather than silently dropped, so the output is auditable.
    """
    hits = []
    in_generated = False
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        starts_generated = bool(GEN_MARKER.search(line))
        generated_here = in_generated or starts_generated
        spans = None if generated_here else _quote_intervals(line)
        for root, rx in _ROOT_RES:
            for m in rx.finditer(line):
                token = m.group(0)
                if generated_here:
                    status = EXEMPT_GEN
                elif _in_spans(m.start(), spans):
                    status = EXEMPT_QUOTE
                elif token.lower() in FALSE_FRIENDS:
                    status = FALSE_FRIEND
                else:
                    status = FLAGGED
                hits.append({"source": source, "line": lineno, "token": token,
                             "root": root, "status": status})
        # update generated-block state AFTER processing this line
        if starts_generated:
            in_generated = True
        if in_generated and GEN_END.search(line):
            in_generated = False
    return hits


def _target_files():
    files = (sorted(glob.glob(os.path.join(ROOT, "paper", "sections", "*.tex")))
             + sorted(glob.glob(os.path.join(ROOT, "paper", "appendices", "*.tex"))))
    fm = os.path.join(ROOT, "paper", "frontmatter.tex")
    if os.path.exists(fm):
        files.append(fm)
    return files


def run() -> int:
    all_hits = []
    files = _target_files()
    for path in files:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            all_hits.extend(scan_lines(fh.read().splitlines(), rel))

    flagged = [h for h in all_hits if h["status"] == FLAGGED]
    ff = [h for h in all_hits if h["status"] == FALSE_FRIEND]
    exempt = [h for h in all_hits if h["status"] in (EXEMPT_GEN, EXEMPT_QUOTE)]

    print("=" * 74)
    print("check_anglicization.py -- British spellings by ROOT (brief 27-quinquies)")
    print("=" * 74)
    print(f"Scanned {len(files)} files: paper/sections + paper/appendices + "
          "frontmatter.")
    print(f"Roots: {len(ROOTS)}; inflections: {{'', "
          + ", ".join(i for i in INFLECTIONS) + "}.")

    print(f"\n-- FLAGGED British forms: {len(flagged)} --")
    for h in flagged:
        print(f"  {h['source']}:{h['line']}  '{h['token']}'  (root '{h['root']}')")
    if not flagged:
        print("  (none)")

    print(f"\n-- FALSE FRIENDS excluded before the count: {len(ff)} "
          "occurrence(s) --")
    seen = {}
    for h in ff:
        seen.setdefault(h["token"].lower(), []).append(f"{h['source']}:{h['line']}")
    for tok in sorted(seen):
        print(f"  {tok:16s} x{len(seen[tok])}  ({', '.join(seen[tok])})")
    if not ff:
        print("  (none matched)")

    print(f"\n-- EXEMPT (generated blocks / quotations): {len(exempt)} --")
    for h in exempt:
        print(f"  {h['source']}:{h['line']}  '{h['token']}'  {h['status']}")
    if not exempt:
        print("  (none)")

    print(f"\n-- DECLARED false-friend list ({len(FALSE_FRIENDS)} tokens) --")
    print("  " + ", ".join(sorted(FALSE_FRIENDS)))

    print("\n" + "-" * 74)
    print(f"FINAL COUNT: {len(flagged)} British form(s) outside the exemptions.")
    print("-" * 74)
    return 1 if flagged else 0


def selftest() -> int:
    """Known-bad + known-good injection (invariants 5/6)."""
    print("check_anglicization.py --selftest -- injected known-bad/known-good\n")
    lines = [
        r"British: Modelling choices and a stabiliser, plus labour and organise.",  # 4 flagged
        r"American forms not even matched: Modeling, stabilizer, labor, analysis.",  # 0 flagged (no root+infl)
        r"Root-matching false friends: analyses, hypothesis, synthesis, cancellation.",  # 0 flagged; FF
        r"\midrule % generated by scripts/x.py -- do not hand-edit",
        r"Inside block: labour behaviour colour \\",                                # EXEMPT (generated)
        r"\bottomrule",
        r"Quoted: the authors wrote ``labour markets'' verbatim.",                  # EXEMPT (quotation)
        r"After quote: a real stabiliser here counts.",                             # 1 flagged (line 8)
    ]
    hits = scan_lines(lines, "<scratch>")
    flagged = {h["token"].lower() for h in hits if h["status"] == FLAGGED}
    ff = {h["token"].lower() for h in hits if h["status"] == FALSE_FRIEND}
    gen = {h["token"].lower() for h in hits if h["status"] == EXEMPT_GEN}
    quo = {h["token"].lower() for h in hits if h["status"] == EXEMPT_QUOTE}
    # words that carry no British root + valid inflection are simply not matched
    matched = {h["token"].lower() for h in hits}
    friends = {"analyses", "hypothesis", "synthesis", "cancellation"}

    checks = [
        ("British forms flagged",
         flagged == {"modelling", "stabiliser", "labour", "organise"}),
        ("American forms carry no root, so are never hits",
         not ({"modeling", "stabilizer", "labor", "analysis"} & matched)),
        ("root-matching false friends classified as such", friends <= ff),
        ("false friends NOT flagged", not (friends & flagged)),
        ("generated block exempt (not flagged)",
         {"labour", "behaviour", "colour"} <= gen and "behaviour" not in flagged),
        ("quotation exempt (not flagged)",
         "labour" in quo
         and not any(h["status"] == FLAGGED and h["line"] == 7 for h in hits)),
        ("a real form after the quote is still flagged",
         any(h["status"] == FLAGGED and h["line"] == 8 for h in hits)),
    ]
    ok = True
    for label, passed in checks:
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
    print(f"\n  SELFTEST VERDICT: "
          f"{'ALL PASS -- detector trusted' if ok else 'FAIL -- stop'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return selftest()
    return run()


if __name__ == "__main__":
    sys.exit(main())
