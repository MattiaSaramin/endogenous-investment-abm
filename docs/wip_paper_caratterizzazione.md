# Brief 27 Fase A — Caratterizzazione del WIP di `paper/` (SOLA LETTURA)

> **GATE.** Questo referto chiude la Fase A. **Nessun `git add` sotto `paper/`**
> prima della conferma esplicita di Mattia. Baseline: `HEAD = 7d51532`.

## Esito in testa (regola del gate)

- **RIMOZIONE_DI_CONTENUTO: 0.** Nessuna affermazione sparisce senza riapparire.
  Le 5 conseguenze operative del b23 e i sei-siti/H2 di `frontmatter` sono **tutti
  presenti** (dettaglio sotto, con riga e file).
- **REGRESSIONE: 2** — e **una è oltre `\clip`**, quindi **la decisione è di Mattia**:
  1. **`\clip`** perso in `eq:investment` (`03_model.tex`) — atteso, già accertato.
  2. **`paper/.gitignore` CANCELLATO** — ignorava artefatti di build LaTeX
     (`*.aux`, `*.log`, `*.pdf`, …). Cancellazione **quasi certamente non voluta**
     (brief §2.3): da **segnalare, non applicare**.
- Tutto il resto è **ANGLICIZZAZIONE + RISTRUTTURAZIONE** (British→American, reflow,
  rimozione di `\emph`/`\textbf`, em-dash→virgola). **Il WIP non muove numeri**:
  parità token decimali HEAD=WT confermata file per file (01: 3=3, 02: 7=7, 03: 3=3,
  08: 44=44; brief: 614=614). ⇒ la copertura 49/611 del b26 Fase 3 **non è
  contaminata**.

## 1. Diff annotato, file per file

`git diff --stat HEAD -- paper/` mostra **7 file con modifiche di contenuto**; altri
**3** (`b_notation.tex`, `main.tex`, `11_limitations.tex`) risultano ` M` in
`porcelain` ma **`git diff HEAD` li vede identici**: differiscono **solo per i
fine-riga** (CRLF↔LF, normalizzati da `.gitattributes`). Non sono modifiche reali.

| file | numstat (+/−) | classificazione | evidenza |
|---|---|---|---|
| `paper/.gitignore` | 0/16 (cancellato) | **REGRESSIONE** | ignorava `*.aux *.bbl *.bcf *.blg *.fdb_latexmk *.fls *.lof *.log *.lot *.out *.pdf *.run.xml *.synctex.gz *.toc`. Senza di lui, ogni build LaTeX in `paper/` diventa tracciabile → sporcizia nel repo. |
| `paper/sections/03_model.tex` | 7/25 | **ANGLICIZZAZIONE + RISTRUTTURAZIONE** + **REGRESSIONE** | anglicizzazione (`normalised→normalized`, `labour→labor`, `realised→realized`, `\Cref→\cref`, `\emph{}` rimossi) e reflow; **`\clip` perso** in `eq:investment` (l'unico delta d'equazione — le altre 6 equazioni sono intatte). |
| `paper/frontmatter.tex` | 7/38 | **ANGLICIZZAZIONE + RISTRUTTURAZIONE** | `First/Second/Third`→`(1)/(2)/(3)`, split di paragrafo, `\emph`/`\textbf` rimossi, reflow. **H2 bracket PRESERVATO** (§4). Nessun contenuto rimosso (word 362→361). |
| `paper/sections/01_introduction.tex` | 15/76 | **ANGLICIZZAZIONE + RISTRUTTURAZIONE** | em-dash→virgola, `\textbf{Supply./Demand./First/Second/Third}` de-emfatizzati, reflow, `organising→organizing`, `Summarised→Summarized`. Word-diff: **nessuna rimozione sostanziale**; refs 9=9. b23-1 presente (§2). |
| `paper/sections/02_literature.tex` | 11/103 | **ANGLICIZZAZIONE + RISTRUTTURAZIONE** | reflow (giunzione di righe con `%`), `optimiser→optimizer`, `profit-maximising→profit-maximizing`, `Blanchflower--Oswald→Blanchflower-Oswald`, `endogenised→endogenized`, en-dash→trattino sui range σ. Word-diff: **nessuna rimozione**; refs 19=19. b23-2 presente (§2). |
| `paper/README.md` | 30/82 | **ANGLICIZZAZIONE + RISTRUTTURAZIONE** | em-dash→punteggiatura, reflow, `2 000→2000`. **word 1093=1093, refs 5=5** ⇒ zero contenuto rimosso. |
| `paper/sections/08_fiscal.tex` | 1/1 | **RISTRUTTURAZIONE (cosmetica) — da confermare** | `phenomenon. \Cref{fig:government}` → `phenomenon. \\ \Cref{fig:government}`: aggiunge un `\\` (a-capo forzato) in testo corrente. Cosmetico; **nota**: `\\` fuori da tabella/align può emettere un warning LaTeX. Decisione di Mattia se tenerlo. |
| `b_notation.tex`, `main.tex`, `11_limitations.tex` | 0/0 (solo EOL) | **non-modifica** | differiscono solo per fine-riga; `git add` li normalizza a no-op. |

### Micro-note tipografiche (non contenuto, per completezza — decisione di Mattia)
- `Blanchflower--Oswald` → `Blanchflower-Oswald` e `$0.40$--$0.60$`/`$0.45$--$0.87$`
  → trattino singolo: en-dash→hyphen sui **range**. Tipograficamente i range vogliono
  l'en-dash (`--`); è un **downgrade cosmetico**, non contenuto (i token `0.40 0.60
  0.45 0.87` e le citazioni `Chirinko2008`/`Knoblach2020` **sopravvivono**, `02_literature:36`).
- `\Cref{fig:model}` → `\cref{fig:model}` in `03_model` a **inizio frase**: cleveref
  a inizio frase vuole `\Cref` (maiuscolo). Nit di stile, non contenuto; il target
  `fig:model` è preservato.

## 2. Verifica delle 5 conseguenze operative del b23 (`confronto_teglio.md §7`)

Tutte **presenti** nel working tree:

- [x] **b23-1 — congettura di Teglio** citata in `01_introduction.tex:10` («venture a
  conjecture about its outcome; the present extension is that development, and
  \cref{sec:shape} returns to the conjecture») e **ripresa in `06_shape.tex:116–126`**
  con «does not envisage income growth» (`:118`) e la distinzione dichiarata **«adjacent,
  not identical»** (`:121`) fra congettura e `dY/dρ` al ρ ancorato.
- [x] **b23-2 — razionalità e simmetria di rete congelate**, tabella inclusa, con
  l'**aggravante b10**: `02_literature.tex:13` («household rationality … and the symmetry
  of the interaction network are the independent variables … here both are held fixed …
  the heterogeneity cascade running precisely through the **fixed spending shares** … a
  failing firm's demand is destroyed rather than rerouted»); righe tabella `Rationality`/
  `Network` a `02_literature.tex:27`.
- [x] **b23-3 — numerario come contributo al modello base** (non solo limite): `01_introduction.tex:28`
  e `02_literature.tex:13` («The fixed price inherited from the base model … there the
  numéraire is innocuous … A wage curve changes that … holding the numéraire fixed is no
  longer free»).
- [x] **b23-4 — replica fiscale di Teglio come validazione incrociata**: `08_fiscal.tex:51–57`
  («\citeauthor{Teglio2025}'s central results is that redistribution … the same sign emerges
  here … That a base-model result survives the addition of those two channels is a
  **cross-validation** rather than a fresh finding»).
- [x] **b23-5 — punto 13 come clausola condizionale di Teglio** (non rifondazione): `06_shape.tex:118–119`
  («does not envisage income growth. Ours is exactly that model — constant $A$ and $g=0$ — so
  the conjecture is testable here»), `10_discussion.tex:59` («What it does not overturn is the
  conditional finding itself»), `11_limitations.tex:14` («With $g=0$, the model cannot match …»).

**Nessuna casella vuota ⇒ nessuna `RIMOZIONE_DI_CONTENUTO` sul materiale b23.**

## 3. `paper/.gitignore` (Fase A punto 3)

Cancellato. Ignorava **esclusivamente artefatti di build LaTeX**:
`*.aux *.bbl *.bcf *.blg *.fdb_latexmk *.fls *.lof *.log *.lot *.out *.pdf
*.run.xml *.synctex.gz *.toc` (header: «LaTeX build artefacts. The PDF is produced by
.github/workflows/paper.yml … so it is not tracked here»). **Se applicata**, ogni
compilazione locale renderebbe tracciabili `main.aux`, `main.log`, `main.pdf`, ecc.
⇒ **REGRESSIONE**: da segnalare, **non applicare** (brief §2.3). Raccomandazione:
**ripristinare** `paper/.gitignore` alla forma di HEAD.

## 4. `frontmatter.tex` — sito H2 (b22) (Fase A punto 4)

L'enunciato H2 è **ancora il bracket fra le due convenzioni di pass-through**, sia a
HEAD sia nel working tree (solo anglicizzato/riformattato):

> «The wage curve generates a fragility immune to demand instruments: three
> stabilization hypotheses fail through one wage→unemployment→capital-erosion channel.
> That immunity is diagnostic … **it is bracketed by the price convention: it stands
> under a fixed numéraire, and is switched off, through a Pigou effect, under complete
> instantaneous pass-through, with neither convention anchored.**»

- **Nessuna** delle tre formulazioni vietate compare: non «H2 cade», non «H2 tiene»,
  non «H2 è rovesciata». È il bracket, invariato.

## 5. Decisioni richieste al gate (di Mattia)

1. **`paper/.gitignore`**: ripristinare (raccomandato) o cancellare con motivazione scritta?
2. **`\clip`**: da ripristinare (Fase B.1, forma di HEAD = `\clip(\rho\Pi_{t-1}\varphi_t,
   \underline I, \Pi_t)` = codice `min(max(·, investment_floor), profit_last_period)`).
   Non è una scelta, è la riparazione mandata dal brief — confermo solo la forma.
3. **`08_fiscal.tex` `\\`**: tenere l'a-capo forzato o revertirlo (possibile warning LaTeX)?
4. **Downgrade tipografici** (en-dash→trattino sui range; `\Cref`→`\cref` a inizio frase):
   tenere l'anglicizzazione così com'è o revertire questi nit? (nessuno tocca il contenuto.)

Il resto del blocco (anglicizzazione + ristrutturazione, contenuto e b23 preservati) è
pronto a landare in **un unico commit** appena Mattia decide 1/3/4 e conferma il gate.

## 6. Esito del gate (deciso da Mattia, poi eseguito in Fase B)

Il gate è stato rispettato: **nessun `git add` sotto `paper/` prima di questa decisione**
(dimostrato dall'ordine dei commit — questo file è committato prima del blocco paper).
Decisioni:

1. **`paper/.gitignore`** → **RIPRISTINATO alla forma di HEAD** (`git checkout HEAD -- paper/.gitignore`).
2. **`\clip`** → **RIPRISTINATO** in `eq:investment` (forma HEAD `\clip\big(\rho\Pi_{t-1}\phi_t,
   \underline I, \Pi_t)`, = codice `min(max(·, investment_floor), profit_last_period)`).
3. **Tipografia** → Mattia ha scelto un intervento **più ampio del blocco WIP**:
   **de-dash PAPER-WIDE** (nessun em/en-dash `---`/`--` in tutto il documento). Eseguito su
   `sections/*.tex` + `appendices/*.tex` (123 em → virgola, 35 en → trattino). Due `--`
   restano **solo nei marcatori-commento** `do not hand-edit` (non renderizzati; ripristinati
   alla forma canonica per coerenza coi generatori). **Due celle `& ---`** (segnaposto n/a in
   `tab:repaired`/`tab:delta`, `09_sensitivity:62,139`) → **celle vuote** (`& \\`), non virgola.
   Conseguenza dichiarata sui token dello sweep: vedi `docs/audit_b26_paper_codice.md` §0.
4. **`08_fiscal.tex` `\\`** e nit vari → assorbiti nel blocco (nessun contenuto toccato).

Toolchain post-blocco: `pytest` 569, `verify_paper` 0 FAIL, `coherence` 0 DIVERGENT
(+ `DOCUMENT UNTRACKED: RESULTS.md`, Fase E), `verify_model` 19 MATCH, blocchi generati
byte-identici. `git diff HEAD -- paper/` **vuoto a fine brief** (tutto committato in blocco).
