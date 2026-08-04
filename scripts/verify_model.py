#!/usr/bin/env python
"""Verify the paper's printed PARAMETER VALUES against the code's actual defaults.

This is the missing fourth axis of the toolchain (brief 26).  The three committed
verifiers cover paper-vs-artifact (``verify_paper.py``), document-vs-document
(``coherence.py``) and double-rounding (``sweep_rounding.py``); NONE of them checks
that the parameter values stamped in the paper are the values the code actually runs
with.  That is the gap this closes for the automatable half (the parameter defaults);
the equations are audited by hand in ``docs/audit_b26_paper_codice.md`` (Phase 2),
because parsing LaTeX equations would manufacture false positives.

WHAT IT CHECKS.  For every registered parameter it checks TWO independent things,
mirroring ``verify_paper.py``'s (a)/(b) split:

  (a) CODE:  read the ACTUAL default out of ``src/model.py`` -- via
      ``inspect.signature(MacroModel.__init__)`` for constructor defaults, via module
      attributes for the frozen constants (``U_REF``, ``ANCHOR_*``), or via a declared
      derivation (``u_min = None`` resolves to ``1/num_households``).  Reading the
      signature and the module attributes imports the model but RUNS NOTHING (no
      ``.step()``), honouring the brief's "no model run".  ``round(code, decimals) ==
      value`` -- rounding ONCE from the full value, ROUND_HALF_UP.
  (b) TEX:   ``needle`` (the value as PRINTED) occurs on a line of the named
      ``paper/`` file matching ``context`` EXACTLY ONCE.  ``context`` pins the row so
      the check cannot pass on a digit that happens to appear elsewhere (the
      substring-ambiguity blind spot, brief 22 #3).

REGISTRY.  A dict in this source (the brief permits "YAML o dict nel sorgente"),
modelled on the ``symbol`` field of ``paper_claims.yaml`` (LaTeX symbol -> code
name).  Each entry declares its own ``decimals`` and its own ``kind``:

  exact    a single numeric default printed as one decimal token
  swept    the paper prints "swept"; the code carries the NESTING default (eta = 0,
           rr = 0, sigma = 1) -- checked: the default equals the declared nesting
           value AND the row says "swept".  Reproduces the paper's own claim that the
           parameter is swept, not fixed at the nesting value.
  set      the paper prints a set (c0 in {1.0, 2.0}); the default must be a member and
           every member must be printed on the row.
  derived  the printed value is a derived default (U_min = 1/num_households at the
           default N); the derivation is declared and recomputed here.

Fraction needles (pi0 printed "1/3", not "0.333") carry an explicit ``needle`` and are
compared numerically at ``decimals`` against the resolved fraction.

OUTCOMES, one per parameter:  MATCH / MISMATCH (code default does not round to the
printed value) / NOT_IN_TEX (the paper does not print the value on the context row) /
AMBIGUOUS (printed more than once on context-matching lines -- a non-discriminating
check, counted apart, never a pass).

EXIT CODE is non-zero if any parameter MISMATCHes or is NOT_IN_TEX.  AMBIGUOUS does
not fail the build (same policy as ``verify_paper.py``).

SELFTEST.  ``python verify_model.py --selftest`` injects an ALTERED default into the
code-read path and asserts the checker turns MATCH -> MISMATCH.  A detector that
passes its selftest without inspecting anything is worse than no detector (project
rule, METHODOLOGY §6); this proves (a) actually reads the code value.

OUTPUT CSV: ``results/audit_b26_params.csv`` (this script is its committed generator).
"""
from __future__ import annotations

import argparse
import csv
import inspect
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import model as M  # noqa: E402  (import after sys.path fix; reads defaults, runs nothing)

OUT_CSV = os.path.join(ROOT, "results", "audit_b26_params.csv")

# Outcomes
MATCH = "MATCH"
MISMATCH = "MISMATCH"
NOT_IN_TEX = "NOT_IN_TEX"
AMBIGUOUS = "AMBIGUOUS"
FAILURES = {MISMATCH, NOT_IN_TEX}


# ---------------------------------------------------------------------------
# Code-value readers (import-only; no model instantiation, no .step())
# ---------------------------------------------------------------------------
_SIG = inspect.signature(M.MacroModel.__init__)


def _default(name: str):
    """The literal default of a MacroModel.__init__ parameter (resolved at def time)."""
    return _SIG.parameters[name].default


def read_code_value(entry: dict):
    """Resolve the code-side value for a registry entry.  Pure reads, no run."""
    src = entry["code"]
    kind, ref = src[0], src[1]
    if kind == "signature":
        return _default(ref)
    if kind == "module":
        return getattr(M, ref)
    if kind == "derived":
        # u_min = None resolves to 1/num_households at the DEFAULT num_households.
        # Declared derivation, recomputed here from the same default the code uses.
        if ref == "u_min_default":
            n = _default("num_households")
            return 1.0 / n if n > 0 else 0.0
        raise KeyError(f"unknown derived ref {ref!r}")
    raise KeyError(f"unknown code source {kind!r}")


# ---------------------------------------------------------------------------
# Rounding -- round ONCE from the full value, ROUND_HALF_UP (brief 26 §3).
# ---------------------------------------------------------------------------
def round_half_up(x: float, decimals: int) -> Decimal:
    q = Decimal(1).scaleb(-decimals)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def fmt(x: float, decimals: int) -> str:
    return str(round_half_up(x, decimals))


# ---------------------------------------------------------------------------
# Tex appears-in with a context regex (brief 19/22 discipline)
# ---------------------------------------------------------------------------
_LINES: dict[str, list[str]] = {}


def _lines(rel_path: str) -> list[str]:
    if rel_path not in _LINES:
        with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="replace") as fh:
            _LINES[rel_path] = fh.read().splitlines()
    return _LINES[rel_path]


def tex_status(needle: str, rel_path: str, context: str):
    """Count ``needle`` on lines of ``rel_path`` matching ``context``; classify.

    ``context`` is required for every entry: it pins the parameter's own row, so a
    digit shared with another row cannot make the check pass vacuously.
    """
    rx = re.compile(context)
    hits = [i for i, line in enumerate(_lines(rel_path), 1)
            if rx.search(line) and needle in line]
    if not hits:
        return NOT_IN_TEX, f"'{needle}' not on any /{context}/ line in {rel_path}"
    if len(hits) == 1:
        return "OK", f"line {hits[0]}"
    return AMBIGUOUS, f"'{needle}' on {len(hits)} /{context}/ lines {hits} in {rel_path}"


# ===========================================================================
# THE REGISTRY  --  LaTeX symbol -> code reference -> printed value
# ===========================================================================
# Every value below is printed in tab:params (paper/sections/04_calibration.tex),
# which is committed (not part of the paper working-tree WIP).  code = how to read
# the ACTUAL default; needle = the value as printed; context = a regex that lands on
# the parameter's own table row.
PARAMS_TEX = "paper/sections/04_calibration.tex"

REGISTRY: list[dict] = [
    # --- anchored to a citable source -------------------------------------
    {"symbol": "sigma", "code": ("signature", "sigma"), "kind": "swept",
     "nesting": 1.0, "decimals": 1, "needle": "swept",
     "tex": PARAMS_TEX, "context": r"elasticity of substitution"},
    {"symbol": "pi0", "code": ("signature", "pi0"), "kind": "exact",
     "value": 1.0 / 3.0, "decimals": 4, "needle": "1/3",
     "tex": PARAMS_TEX, "context": r"base-point capital share"},
    {"symbol": "eta", "code": ("signature", "eta"), "kind": "swept",
     "nesting": 0.0, "decimals": 2, "needle": "swept",
     "tex": PARAMS_TEX, "context": r"wage-curve elasticity"},
    {"symbol": "lambda (wealth effect)", "code": ("signature", "wealth_effect"),
     "kind": "exact", "value": 0.05, "decimals": 2, "needle": "0.05",
     "tex": PARAMS_TEX, "context": r"wealth effect"},
    {"symbol": "rho (retention)", "code": ("signature", "retention_ratio"),
     "kind": "exact", "value": 0.40, "decimals": 2, "needle": "0.40",
     "tex": PARAMS_TEX, "context": r"retention ratio"},
    {"symbol": "rr (replacement)", "code": ("signature", "benefit_replacement_rate"),
     "kind": "swept", "nesting": 0.0, "decimals": 2, "needle": "swept",
     "tex": PARAMS_TEX, "context": r"replacement rate"},
    # --- declared conventions ---------------------------------------------
    {"symbol": "delta (depreciation)", "code": ("signature", "delta"),
     "kind": "exact", "value": 0.05, "decimals": 2, "needle": "0.05",
     "tex": PARAMS_TEX, "context": r"depreciation"},
    {"symbol": "U_min", "code": ("derived", "u_min_default"),
     "kind": "derived", "value": 0.01, "decimals": 2, "needle": "0.01",
     "tex": PARAMS_TEX, "context": r"w_\{\\min\}"},
    {"symbol": "w_min", "code": ("signature", "wage_floor"),
     "kind": "exact", "value": 0.45, "decimals": 2, "needle": "0.45",
     "tex": PARAMS_TEX, "context": r"w_\{\\min\}"},
    {"symbol": "max tau (tax cap)", "code": ("signature", "max_tax"),
     "kind": "exact", "value": 0.6, "decimals": 1, "needle": "0.6",
     "tex": PARAMS_TEX, "context": r"tax cap"},
    {"symbol": "I (investment floor)", "code": ("signature", "investment_floor"),
     "kind": "exact", "value": 0.1, "decimals": 1, "needle": "0.1",
     "tex": PARAMS_TEX, "context": r"investment floor"},
    {"symbol": "u-bar (target util)", "code": ("signature", "target_utilization"),
     "kind": "exact", "value": 0.90, "decimals": 2, "needle": "0.90",
     "tex": PARAMS_TEX, "context": r"target utilization"},
    # --- modeling choices, measured once then frozen ----------------------
    # brief 27-quinquies: these context regexes matched the paper's British
    # spelling; brief 27-quater anglicized tab:params to American (utilization,
    # normalization) but left these patterns British, so they silently went
    # NOT_IN_TEX (4 FAIL).  Aligned to American to finish the anglicization.
    {"symbol": "K0", "code": ("signature", "K0"), "kind": "exact",
     "value": M.ANCHOR_K0, "decimals": 2, "needle": "41.87",
     "tex": PARAMS_TEX, "context": r"normalization anchor"},
    {"symbol": "L0", "code": ("signature", "L0"), "kind": "exact",
     "value": M.ANCHOR_L0, "decimals": 3, "needle": "7.395",
     "tex": PARAMS_TEX, "context": r"normalization anchor"},
    {"symbol": "U_REF", "code": ("module", "U_REF"), "kind": "exact",
     "value": M.U_REF, "decimals": 5, "needle": "0.26047",
     "tex": PARAMS_TEX, "context": r"REF"},
    {"symbol": "w-bar", "code": ("signature", "wage_rate"), "kind": "exact",
     "value": 0.9, "decimals": 1, "needle": "0.9",
     "tex": PARAMS_TEX, "context": r"normalization point once"},
    {"symbol": "K_init", "code": ("signature", "initial_capital"), "kind": "exact",
     "value": 40.0, "decimals": 1, "needle": "40.0",
     "tex": PARAMS_TEX, "context": r"selects the basin"},
    {"symbol": "beta (accelerator)", "code": ("signature", "beta"), "kind": "exact",
     "value": 0.5, "decimals": 1, "needle": "0.5",
     "tex": PARAMS_TEX, "context": r"accelerator"},
    # --- declared non-anchorable ------------------------------------------
    {"symbol": "c0", "code": ("signature", "c0"), "kind": "set",
     "members": [1.0, 2.0], "decimals": 1, "needles": ["1.0", "2.0"],
     "tex": PARAMS_TEX, "context": r"autonomous consumption"},
]


# ===========================================================================
# Checker
# ===========================================================================
def check_entry(entry: dict, override=None):
    """Return a result dict for one registry entry.

    ``override`` (selftest only) replaces the code-read value, to prove the
    code-side comparison is live.
    """
    code_val = read_code_value(entry) if override is None else override
    kind = entry["kind"]
    dec = entry["decimals"]

    # --- value check (a): code default rounds to the printed value --------
    if kind in ("exact", "derived"):
        want = entry["value"]
        code_round = fmt(code_val, dec)
        want_round = fmt(want, dec)
        value_ok = code_round == want_round
        value_note = f"round({code_val!r},{dec})={code_round} vs {want_round}"
        needles = [entry["needle"]]
    elif kind == "swept":
        # the code carries the nesting default; the paper prints "swept"
        code_round = fmt(code_val, dec)
        want_round = fmt(entry["nesting"], dec)
        value_ok = code_round == want_round
        value_note = f"default={code_val!r} nests at {entry['nesting']!r}"
        needles = [entry["needle"]]
    elif kind == "set":
        members = entry["members"]
        value_ok = float(code_val) in members
        value_note = f"default={code_val!r} in {members}"
        needles = entry["needles"]
    else:
        raise KeyError(kind)

    value_status = MATCH if value_ok else MISMATCH

    # --- tex check (b): every needle printed on the context row -----------
    tex_states = []
    tex_notes = []
    for n in needles:
        st, note = tex_status(n, entry["tex"], entry["context"])
        tex_states.append(st)
        tex_notes.append(note)
    if any(s == NOT_IN_TEX for s in tex_states):
        tex_status_final = NOT_IN_TEX
    elif any(s == AMBIGUOUS for s in tex_states):
        tex_status_final = AMBIGUOUS
    else:
        tex_status_final = "OK"

    # --- verdict ----------------------------------------------------------
    if value_status == MISMATCH or tex_status_final == NOT_IN_TEX:
        verdict = MISMATCH if value_status == MISMATCH else NOT_IN_TEX
    elif tex_status_final == AMBIGUOUS:
        verdict = AMBIGUOUS
    else:
        verdict = MATCH

    return {
        "symbol": entry["symbol"],
        "code_ref": f"{entry['code'][0]}:{entry['code'][1]}",
        "kind": kind,
        "code_value": repr(code_val),
        "decimals": dec,
        "printed": " ".join(needles),
        "value_status": value_status,
        "value_note": value_note,
        "tex_file": entry["tex"],
        "tex_status": tex_status_final,
        "tex_note": " | ".join(tex_notes),
        "verdict": verdict,
    }


def run(write_csv: bool = True) -> int:
    rows = [check_entry(e) for e in REGISTRY]

    if write_csv:
        os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
        cols = ["symbol", "code_ref", "kind", "code_value", "decimals", "printed",
                "value_status", "value_note", "tex_file", "tex_status", "tex_note",
                "verdict"]
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    print("verify_model.py -- paper tab:params vs MacroModel defaults\n")
    print(f"{'symbol':22s} {'code_ref':34s} {'printed':10s} {'verdict':10s}")
    print("-" * 80)
    n_fail = n_amb = 0
    for r in rows:
        if r["verdict"] in FAILURES:
            n_fail += 1
        elif r["verdict"] == AMBIGUOUS:
            n_amb += 1
        print(f"{r['symbol']:22s} {r['code_ref']:34s} {r['printed']:10s} "
              f"{r['verdict']:10s}  {r['tex_note']}")

    print("\nSummary:")
    print(f"  {sum(1 for r in rows if r['verdict']==MATCH):3d}  MATCH")
    print(f"  {sum(1 for r in rows if r['verdict']==AMBIGUOUS):3d}  AMBIGUOUS "
          f"(non-discriminating; not a failure)")
    print(f"  {sum(1 for r in rows if r['verdict']==MISMATCH):3d}  MISMATCH")
    print(f"  {sum(1 for r in rows if r['verdict']==NOT_IN_TEX):3d}  NOT_IN_TEX")
    if write_csv:
        print(f"\nReport written to {os.path.relpath(OUT_CSV, ROOT)} "
              f"({len(rows)} parameters).")
    print(f"\n{n_fail} FAIL, {n_amb} ambiguous.")
    return 1 if n_fail else 0


# ===========================================================================
# Selftest: inject an altered default, assert the checker FAILS net.
# ===========================================================================
def selftest() -> int:
    print("verify_model.py --selftest -- inject an altered default, expect MISMATCH\n")
    ok = True

    # Pick a known-good exact entry and confirm it MATCHes as-is.
    probe = next(e for e in REGISTRY if e["symbol"] == "delta (depreciation)")
    good = check_entry(probe)
    print(f"  [1] delta as coded            -> {good['verdict']:10s} "
          f"({good['value_note']})")
    if good["verdict"] != MATCH:
        print("        expected MATCH before injection   => FAIL")
        ok = False
    else:
        print("        expected MATCH before injection   => PASS")

    # Inject a wrong default (delta = 0.09, the BEA-implied figure the paper
    # explicitly says is NOT the value) and require the checker to catch it.
    bad = check_entry(probe, override=0.09)
    print(f"  [2] delta injected = 0.09     -> {bad['verdict']:10s} "
          f"({bad['value_note']})")
    if bad["verdict"] != MISMATCH:
        print("        expected MISMATCH after injection => FAIL "
              "(detector is not reading the code value!)")
        ok = False
    else:
        print("        expected MISMATCH after injection => PASS")

    # Also prove the tex side is live: an entry whose printed value the paper
    # does NOT carry must report NOT_IN_TEX.  Inject a bogus needle.
    forged = dict(probe)
    forged["value"] = 0.05
    forged["needle"] = "0.123456"   # not printed anywhere on the depreciation row
    forged_res = check_entry(forged)
    print(f"  [3] forged needle '0.123456'  -> {forged_res['verdict']:10s}")
    if forged_res["verdict"] != NOT_IN_TEX:
        print("        expected NOT_IN_TEX               => FAIL")
        ok = False
    else:
        print("        expected NOT_IN_TEX               => PASS")

    print("\n  SELFTEST VERDICT:", "ALL PASS -- code+tex comparison trusted"
          if ok else "FAILED -- do not trust this run")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="inject an altered default and assert the checker fails")
    ap.add_argument("--no-csv", action="store_true",
                    help="do not (re)write results/audit_b26_params.csv")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(write_csv=not args.no_csv)


if __name__ == "__main__":
    raise SystemExit(main())
