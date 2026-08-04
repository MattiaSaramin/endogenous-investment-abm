# Brief 28 — Fase 0: record del gate (piano approvato)

Record del gate di Fase 0 del brief 28 («il b17 nel paper, e detector disaccoppiati
dalla prosa»). Il gate era sola-lettura: nessuna riga di `paper/` è stata toccata
per produrlo. Il piano qui sotto è quello **confermato da Mattia** in
`brief_28_gate_confermato.md` (che vince sul brief originale dove diverge). Questo
file è il commit di step 1 dell'ordine dei commit del gate.

---

## 0. Base dichiarata

Partenza: **`b27-verify`** (tip `5c8f800`). Il lavoro b27-\* **non è mergiato** in
`main` (`main` a `ec18707`). Il gate confermato dispone di **mergiare `b27-verify`
su `main` PRIMA** e aprire `b28-b17` da `main` — ma il merge e il push di `main`
restano **decisione esplicita di Mattia**, da chiedere, non da assumere.

## 1. Q1 — cosa il paper dice già di β (misurato, sola lettura)

| dove | cosa dice | numero `S1(slope\|viable)`? |
|---|---|---|
| `03_model:98` `eq:accelerator` | `φ_t = max{0, 1+β(u_{t-1}−ū)}` — utilizzo realizzato | — |
| `04_calibration:78` `tab:params` | β=0.5, «no canonical value exists; treated by [SA]» | — |
| `09_sensitivity:342` caption `fig:sa-b14` | «the panel in which the accelerator gain β **dominates**» (qualitativo) | **no** |
| `09_sensitivity:358–369` «The accelerator produces the sign» | quartili (0.6% vs 22.1%; viability 0.523 vs 0.423); «the headline depends on the one parameter with the weakest empirical claim» | **no** |

**`beta`/`accelerator`: ZERO occorrenze in `10_discussion.tex` e `11_limitations.tex`.**
Nessuna occorrenza di `u^e`, `\lambda_u`, «expected utilization», `0.641`, `0.370`,
`94.9` in `paper/`. Il b17 **non è nel paper**; il numero `S1(slope|viable)` per β
**non è stampato** (solo mostrato graficamente in `fig:sa-b14`).

## 2. Numeri ricalcolati dall'artifact (NON citati dal brief)

| quantità | sorgente | valore |
|---|---|---|
| `S1(slope\|viable)` β, corda (b13) | `ces_b13_sobol_indices` | **0.370**, rango **#1** su 17 |
| `S1(slope\|viable)` β, OLS riparata (b14) | `ces_b14_sobol_indices` | **0.641**, rango **#1** |
| Morris μ\* β (pendenza **non condizionata**, `slope_raw`) | `ces_b14_morris` | **94.9**, rango **6°** (δ 537, π0 334, c0 198, λ 134, mpc 125, **β 94.9**) |
| margine risolto | `ces_b17_margin` (30 righe) | **13/30** |
| celle a CI vuota (categoria «non risolto» distinta) | β=0.15, λ_u∈{0.25,0.5} | **2** — `margin_resolved=False`, side «ρ* not resolved»; qui `anchor_in_ci=False` **non** significa risolto (vuoto≠falso) |
| λ_u=0 (acceleratore spento) | ogni β | ρ\*=**0.35772138830328354** identico ∀β; ancora **0.3632216782659768** dentro la CI → margine **svanisce** (non si inverte) |
| margine risolto (falling, negativo) | λ_u∈[0.25,1.0] | consistente per **β≥0.5** (default 0.5 **sul bordo**); β=0.30 solo a λ_u=0.25; β≤0.15 mai |

## 3. Collocazione (un solo commit `paper/`, in blocco) — con R1/R2/R3

1. **`03_model` §3.4** (dopo `eq:accelerator`): specifica
   `u^e_t = u^e_{t-1} + λ_u(u_{t-1}−u^e_{t-1})`, l'acceleratore legge `u^e`;
   `eq:accelerator` come stampata è il **caso λ_u=1, annidamento byte-identico**
   (si **generalizza**, non si corregge — al default è corretta).
2. **§7 stress** — nuova sottosezione **dopo `sec:expectations`** (il test b08 su
   λ_e, aspettativa di **domanda**): la controparte b17 su λ_u (aspettativa
   sull'**investimento**), parte **(a)**: falsificazione del **segnale** — meccanismo
   caduto alla radice (`sd` di `util_effect` piatta su [0.25,1.0], zero solo a
   λ_u=0, perché `u` è quasi a radice unitaria); ρ\*/pendenza/wage-led
   **λ_u-invarianti**. **Senza il numero di β.**
3. **§9** («The accelerator produces the sign») — **[R2]** qui va il numero: corda
   **0.370** e OLS **0.641**, β **primo in entrambe** (reperto indipendente dalla
   riparazione della QoI); **nella stessa frase** il Morris lo mette **6°**
   (μ\*=94.9) perché misura la pendenza **non condizionata**, dove δ/π0 dominano
   **via viability**. Le due letture sono coerenti e non si separano.
4. **§10** accanto a `sec:frontierlocal` — parte **(b)**: H1 **load-bearing sulla
   FORZA** dell'acceleratore (margine risolto solo β≥0.5, default sul bordo;
   λ_u=0 → margine svanisce; due modi indipendenti di spegnerlo, λ_u=0 e β=0.05,
   danno lo stesso esito).
5. **§11 limitations** — **[R1]** nuovo `\paragraph` come **rimando a §9 + il fatto
   nuovo** (load-bearing sulla forza di β, margine risolto solo β≥0.5, default sul
   bordo). §11 oggi **non menziona β affatto**: è un buco preesistente (la lista
   degli impegni non elenca il parametro peggio ancorato su cui §9 dice che poggia
   l'headline). **Non ripetere i quartili** (una volta sola, in §9).
6. **`app:validation`** — **[R3]** l'episodio del **gate** (NON `app:retractions`:
   non è stato ritirato niente). Record di protocollo: regola congelata → OPEN (6
   trigger) → decomposizione post-hoc (**4 degeneri λ_u=0 + 2 rumore near-anchor
   β=0.05 + 0 gradiente di lisciamento**) → chiusura decisa dal PI **sulla sostanza,
   sopra un gate aperto**, decisione meccanica **lasciata intatta nel record**. Il
   difetto è nel **disegno del gate** (includeva il controllo degenere nel test di
   movimento).

### Conclusione a due tempi (forma obbligatoria)

- **(a)** H1 **robusto alla specifica del SEGNALE** dell'acceleratore (ipotesi
  pre-registrata falsificata su due piani: meccanismo alla radice + λ_u-invarianza).
- **(b)** H1 **load-bearing sulla FORZA** dell'acceleratore (margine risolto solo
  β≥0.5, default sul bordo; λ_u=0 → svanisce).

### Formulazioni VIETATE

«H1 esce più forte»; «H1 sopravvive alla respecifica del canale che porta il 64%
della varianza».

### Due limiti di scope, ogni volta che si cita il risultato

1. Il **64% è marginalizzato**; la Fase A è **condizionale su un punto**; la **Fase
   B NON è stata eseguita** (gate chiuso sulla sostanza) — dirlo.
2. La Fase A **non** ha testato il regime di collasso `c0=2.0` — lacuna di
   **disegno del brief 17**, **coperta dal b21** — dirlo con questa attribuzione.

## 4. Q2 — tabella `tab:b17`, TRE stati (generatore committato)

Sì alla tabella, con `scripts/make_tab_b17.py` (terza con generatore dopo
`tab:sobol`/`tab:prices`; marcatore `do not hand-edit`; blocco inline
byte-identico). Ragione vincolante: in prosa i due «non risolto» si **collassano**,
e le due celle a CI vuota diventerebbero indistinguibili.

| stato | criterio sull'artifact |
|---|---|
| **risolto** (margine negativo) | `margin_resolved = True` |
| **non risolto — ancora dentro la CI** | `margin_resolved = False`, CI **presente**, `anchor_in_ci = True` |
| **non risolto — ρ\* non risolto, CI non stimabile** | `margin_resolved = False`, `ci_lo`/`ci_hi` **vuoti** |

`margin_resolved` è la **colonna autoritativa**; `anchor_in_ci=False` con CI vuota
**non** è «risolto». `margin_side` va nel documento. Il generatore **asserisce** che
i tre stati coprono le 30 righe **senza sovrapposizioni** (assert nel sorgente). La
colonna **λ_u=0** resta **a sé** (è metà del risultato, non riempitivo).

## 5. Q3 — workflow: mergiare prima, poi ramificare

1. Mergia `b27-verify` → `main` (cinque brief di prosa/strumenti, finito, verde,
   read-gate risolto).
2. Apri **`b28-b17`** da `main`, lavora lì.
3. **Voce B dopo** che la CI di Voce A è verde (Voce B non tocca `paper/`).

> **Merge e push di `main` = decisione esplicita di Mattia.** Da chiedere prima di
> eseguirli, non assumere.

## 6. Ordine dei commit (dimostra il gate)

1. **questo record del gate** (step 1)
2. **[conferma Mattia: merge `b27-verify`→`main`, nuovo ramo `b28-b17`]**
3. Voce A — blocco `paper/` (§3.4 + §7 + §9 + §10 + §11 + `app:validation`), **un commit**
4. `scripts/make_tab_b17.py` + blocco inline + `paper_claims.yaml`
5. sweep rigenerato **dopo** l'ultimo commit su `paper/` (b22-bis); token decimali nuovi, **misurati**
6. push → **CI verde**, quattro contatori, green-vs-tip
7. Voce B — disaccoppiamento dei detector (nessun `paper/`)
8. record in `METHODOLOGY.md` §8 (b22-ter) + `docs/`

## 7. Invarianti che restano in vigore

Vuoto≠falso; tutti i numeri ricalcolati dall'artifact; `eq:accelerator` si
generalizza (non si corregge); non toccare `src/`, `tab:delta`, blocchi
`do not hand-edit`; `b17_beta_S1_slope_given_viable` da SKIP a claim vero se β viene
enunciato; citare **entrambe** le vintage di `S1(slope|viable)` + Morris 6°; nessun
push su `main` senza conferma.
