# Censimento: detector accoppiati alla prosa del paper

Brief 28, Voce B. Misura del **debito di accoppiamento**: quali pattern di
matching dei detector dipendono dalla **prosa** del paper, e quindi possono
rompersi in silenzio a ogni passata di stile (anglicizzazione, de-enfasi,
de-em-dash). È la classe di difetto scoperta dal brief 27-quinquies: i quattro
pattern britannici di `verify_model.py` erano rimasti sulla prosa
(`utilisation`/`normalisation`) mentre il paper era passato all'americano, e il
«19 MATCH» registrato dal 27-quater era **stale** (in realtà 15/4).

**Ordine di preferenza per l'ancora** (dalla più stabile alla meno): simbolo
matematico `$...$` → `\label` → prosa (solo dove non c'è alternativa, dichiarato).

---

## 1. `scripts/verify_model.py` — RISOLTO in questo brief

Tutti i 19 `context` di `verify_model.py` erano su prosa (`elasticity of
substitution`, `retention ratio`, `accelerator`, ...) o sul simbolo di un'altra
riga (`w_\{\\min\}` usato sia per U_min sia per w_min). Ora **19/19 ancorano al
simbolo `$...$` della propria riga** di `tab:params`, che nessuna passata di
stile riscrive:

| # | ancore | note |
|---|---|---|
| 18 | **simbolo puro** `$...$` | es. `$\sigma$`, `$\bar{u}$`, `$(K_0,L_0)$`, `$c_0$` |
| 1 | **simbolo + label di riga** | `delta`: `$\delta$ (depreciation)` |
| — | prosa pura | **0** (era ~16) |

**L'unico residuo dichiarato è `delta`.** Il simbolo nudo `$\delta$` non basta:
δ ricorre nella prosa `$K/Y = (I/Y)/\delta$` (`04_calibration:182`), dove
`$0.0500$` contiene la sottostringa `0.05`. Ancorato quindi al simbolo **più** la
label di colonna `(depreciation)`, che è l'identificatore di riga in tabella, non
prosa di corpo. È l'anello «label» dell'ordine di preferenza, non «prosa».

Il `--selftest` ora dimostra la proprietà (caso `[4]`): riscritta la prosa di una
riga `tab:params`, l'ancora al **simbolo sopravvive** e l'ancora alla **prosa si
rompe** (`NOT_IN_TEX`). Un detector che non distingue i due casi non misura nulla.

---

## 2. `scripts/paper_claims.yaml` — CENSITO (debito, non convertito qui)

I 19 `context` del registro. Il brief converte i pattern di `verify_model.py`;
per `paper_claims.yaml` questo è il **censimento** dell'esposizione (item 2), non
una conversione. «0 CLAIM NOT FOUND» ha tenuto finora **per fortuna, non per
costruzione**.

| classe | conteggio | esempi | dipende dalla prosa? |
|---|---|---|---|
| **strutturale** `&` | 9 | separatore di cella di tabella | **NO** — una riga di tabella ha sempre `&` |
| **numerica** | 4 | `0\.800`, `0\.591`, `0\.680` | NO dalla prosa (ma accoppiata a un **numero fratello**: si rompe se quella cella cambia) |
| **simbolo non delimitato** | 1 | `sigma` (aggancia `\sigma`, riga `tab:sobol` l.99) | debole: aggancia la macro, ma anche un'eventuale «sigma» in prosa; **ritrofittabile** a `\$\\sigma\$` |
| **PROSA** | **5** | `reads` ×4 (caption `fig:sa-b14`, «$\delta$ reads $0.900$»), `Fraction viable` ×1 (`sec:whatfails`) | **SÌ** — si romperebbero se la parola venisse riformulata |

**Il debito residuo è 5 context su prosa** (`reads` ×4, `Fraction viable` ×1), più
1 simbolo non delimitato (`sigma`) ritrofittabile. Sono a **basso costo** di
retrofit: le righe bersaglio portano già il simbolo (`$\delta$ reads $0.900$`; la
riga `Fraction viable` è nel `remark` di `sec:whatfails`), quindi convertibili a
`\$\\delta\$` / a un'ancora di label quando un brief deciderà di saldare il debito.
Non fatto qui (fuori dallo scope dichiarato: l'azione è su `verify_model.py`).

**Analogia col debito dei generatori** (`tab:wagecurve`, b22): referente
identificato, retrofit a basso costo, rimandato. Qui: ancora identificata (il
simbolo sulla stessa riga), retrofit a basso costo, rimandato.

---

## 3. Regola operativa (registrata in `METHODOLOGY.md` §9)

Un detector che matcha **prosa** va **rieseguito, non citato**, dopo ogni passata
di stile sul paper; e il suo numero nel record deve venire dal **run di quel
brief**, non da uno precedente. Un pattern su prosa che si rompe è invisibile
finché non lo si riesegue: è come `verify_model` è andato stale al 27-quater.
