# Paper — LaTeX source

Scientific write-up of the whole project (briefs 01–13, plus the partial
brief-14 bridging experiment).

## Layout

`main.tex` holds structure only — no packages, no prose. Everything else is a
separate file, so two sections can be edited without touching each other.

The order is **argumentative, not chronological**: results are grouped by claim,
and everything methodological is gathered in Appendix A rather than left where
it happened to be discovered.

```
main.tex                  \input lines only
preamble.tex              packages, layout, macros
frontmatter.tex           title, abstract (249 words), table of contents
references.bib            37 entries, all cited
sections/
  01_introduction.tex     the three contributions
  02_literature.tex       relation to the literature
  03_model.tex            equations + period sequence
  04_calibration.tex      the three anchoring tiers; the capital block
  05_protocol.tex         experimental protocol
  06_shape.tex            RESULTS I  - Y(rho) is U-shaped; rho*; sigma*
  07_stress.tex           RESULTS II - wage curve, expectations, heterogeneity
  08_fiscal.tex           RESULTS III- the sign is conditional on fiscal policy
  09_sensitivity.tex      RESULTS IV - global SA, delta cliff, the estimator
  10_discussion.tex
  11_limitations.tex
  12_conclusion.tex
appendices/
  a_validation.tex        validation record: the invariant that held only at
                          the default, the reproducibility criterion and its
                          two limits, the 2x2 in full, withdrawn claims,
                          reproducibility
  b_notation.tex
figures/                  15 PNGs, copied from results/ and the repo root
```

Sections use `\input`, not `\include`: `\include` forces a page break before
and after every file, which is wrong for a continuous paper. The trade-off is
that `\includeonly` is unavailable — to compile a subset while drafting,
comment out the `\input` lines you do not need.

## Compiling on Overleaf

1. Upload the **whole `paper/` folder** (zip it and use *New Project → Upload
   Project*, which preserves the subfolders — a plain multi-file upload
   flattens them and the `\input` paths will break).
2. **Menu → Compiler → pdfLaTeX.** The bibliography uses `biblatex`, which
   Overleaf runs with `biber` automatically.
3. Compile **twice** on the first run so that `cleveref` cross-references and
   the bibliography resolve.

`\graphicspath` also points at `results/` and `./`, so the source still
compiles if you upload the repository root instead of just this folder.

### If Overleaf's free tier times out

The free plan caps compile time (roughly 20–30 s). The document has been kept
deliberately light for this reason — in particular it uses `mdframed` rather
than `tcolorbox`, because `tcolorbox` loads the whole of TikZ/PGF and is
normally the single most expensive thing in a document like this.

If it still times out, in order of effectiveness:

1. **Turn on fast-draft mode.** In `preamble.tex` set `\fastdrafttrue`.
   Figures become empty frames of the right size and the compile gets much
   faster. Set it back to `\fastdraftfalse` for the final PDF.
2. **Compile only the sections you are editing.** Comment out the `\input`
   lines you do not need in `main.tex`. Cross-references to the commented-out
   parts will show as `??` until you put them back — harmless while drafting.
3. **Drop `microtype`** from `preamble.tex`. It costs a noticeable amount of
   time and only affects micro-typography.
4. **Swap Biber for BibTeX.** Biber runs as a separate pass and counts against
   the timeout. Replace the `biblatex` block in `preamble.tex` with
   `\usepackage[authoryear,round]{natbib}`, and `\printbibliography[...]` in
   `main.tex` with `\bibliographystyle{apalike}\bibliography{references}`.
   `references.bib` needs no changes. This costs you `\parencite`-style
   niceties but the `\citet`/`\citep` calls used throughout keep working.

## Building without Overleaf

### GitHub Actions (recommended free route)

`.github/workflows/paper.yml` compiles the paper in a full TeX Live container
on every push that touches `paper/`. There is no compile timeout and nothing
to install.

- Push, then open the repository's **Actions** tab, click the run, and
  download the **`paper-pdf`** artifact.
- You can also start a build by hand: **Actions → Build paper → Run workflow**.
- On a failing build the artifact still contains `main.log`, so you can read
  the LaTeX error without reproducing it locally.

Public repositories get unlimited Actions minutes; private ones get 2 000
minutes a month, and this build takes about a minute.

### Locally

Not currently possible on this machine, for two independent reasons:

- **The TeX Live installation at `C:\texlive\2026` is incomplete** — 16
  executables and a single DLL in `bin\windows`, against the several hundred a
  working install has. The installer was interrupted; `install-tl` is still
  present, so it can be re-run.
- **Windows Smart App Control is enabled**, which blocks unsigned executables.
  TeX Live's binaries are unsigned, so they would be blocked even after a
  complete install.

Be aware before changing the second one: **on Windows 11, Smart App Control
cannot be switched back on once disabled — it can only be re-enabled by
reinstalling Windows.** That is a permanent reduction in the machine's
security posture in exchange for local LaTeX compilation, which the GitHub
Actions route already provides for free. It is not recommended.

## Before submitting

Placeholders to fill in `main.tex`:

- `\author{Mattia \textsc{[Surname]}}` — surname, email, institution
- the repository URL in the title footnote

## Provenance of the numbers

Every table traces to a committed CSV in `results/`:

| Paper table | Source |
|---|---|
| `tab:baseline`, `tab:frontier` | `ces_b05_*`, `ces_sign_frontier*` |
| `tab:wagecurve` | `ces_b07_sigma_star.csv` |
| `tab:expectations` | `ces_b08_sigma_star.csv` |
| `tab:government` | `ces_b09_dose_response.csv` |
| `tab:heterogeneity` | `ces_b10_*` |
| `tab:ownership` | brief-12 measurements (README §8) |
| `tab:sobol`, `tab:delta` | `ces_b13_sobol_indices.csv`, `ces_b13_sobol_byproducts.csv`, `ces_b13_summary.csv` |
| `tab:bridge`, `tab:turning` | `ces_b14_bridge_fixed.csv`, `ces_b14_taskB_slopes.csv` |
| `tab:repaired`, `tab:widesigma` | `ces_b14_summary.csv`, `ces_b14_wide_design.csv` |

Two discrepancies found while writing, both worth reconciling in the repo:

1. **`delta` viability bin 0.060–0.075.** `README.md` says `0.180`;
   `parameter_notes.md` says `0.183`. The committed CSV
   (`ces_b13_sobol_byproducts.csv`) gives `0.18270`, so **`0.183` is right**
   and the README rounds wrongly. The paper uses `0.183`.
2. **The `beta < 0.1` figures** quoted in `README.md` and `METHODOLOGY.md`
   ("0 wage-led points of 338, viability 0.385 vs 0.533") have **no
   corresponding row in any committed CSV** — `ces_b13_sobol_byproducts.csv`
   bins `beta` by quartile, not at a 0.1 cut. Rather than cite a number whose
   generator could not be located, the paper reports the equivalent claim from
   the committed quartile bins (lowest quartile: 2 of 353 viable points
   wage-led, viability 0.423; highest: 22.1 %, viability 0.523). Same
   direction, verifiable provenance. Per the project's §5 rule, the README
   figures should either be regenerated into a committed CSV or withdrawn.

## Status note

Brief 14 is **complete**: both arms of the bridging experiment have run, the
verdict is reported in §9 ("The estimator is part of the result") with the full
2×2 in Appendix A, and the apparent contradiction that motivated the experiment
turned out never to have existed — it is recorded among the withdrawn claims
rather than narrated as an open tension.
