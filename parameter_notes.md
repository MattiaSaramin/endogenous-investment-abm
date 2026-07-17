# Note bibliografiche — ancoraggio dei parametri (core Cobb-Douglas)

> Roadmap punto 4. Per ogni parametro: valore nel modello, stima empirica e
> range, fonte, come entra nel modello, e verdetto di ancoraggio. Da mantenere e
> estendere a ogni nuova estensione. Primo blocco: 2026-07.
>
> **Regola:** un valore è "ancorato" solo con fonte citabile. Dove il valore è
> una scelta di modellazione o di regime, va dichiarato tale — non spacciato per
> stima empirica. Diversi parametri di questo core sono scelte, non stime.

## Sintesi (tiers di ancoraggio)

| Parametro | Valore modello | Ancoraggio | Nota |
|---|---|---|---|
| `sigma` (σ) | **sweep**, default 1.0 | **Buono — e rigetta il default** | 0.40–0.60 (Chirinko 2008); ~0.40 (Chirinko & Mallick 2017); 0.45–0.87 meta-regressione che **rigetta Cobb-Douglas** (Knoblach et al. 2020); Fed SIGMA 0.5. Puzzle σ>1: Karabarbounis & Neiman (2014). **Da sweepare, non scegliere.** |
| `pi0` (π0) | 1/3 | **Buono** | = il vecchio `alpha` rinominato: unica nozione di quota del capitale nel codice |
| `K0`, `L0` | 41.87, 7.395 (per impresa) | **Scelta di modellazione** | ancora di normalizzazione CES; misurata una volta a σ=1, ρ=0.40, poi congelata |
| `Y0` | derivato | **Non libero** | `A·K0^π0·L0^(1−π0)`, calcolato — mai misurato |
| `alpha` | 1/3 | **Buono** | standard growth accounting; ma quota del capitale in aumento nel XXI sec. → ora `pi0` |
| `markup` | ~~0.5 (derivato)~~ | **RIMOSSO al punto 11** | sostituito dal salario fisso `w̄`; sezione sotto marcata STALE |
| `delta` | 0.05 | **Buono (congiunto)** | implicato da K/Y e I/Y; non ancorabile in isolamento |
| `retention_ratio` | 0.40 | **Buono (via I/Y)** | ρ fissa il tasso di investimento, non è un payout |
| `wealth_effect` (λ) | 0.08 | **Debole — sopra l'empirico** | empirico 0.03–0.05; scelto come leva di domanda |
| `c0`, `c1` | 1.0, ~0.9 | **Struttura sì, livello no** | forma da Teglio; `c0` è scala, non stima |
| `beta` (acceleratore) | 0.5 | **Debole** | esiste letteratura sull'acceleratore, ma nessun numero canonico |
| `investment_floor` | 0.1 | **Scelta di modellazione** | guardrail, nessun referente empirico |
| `target_utilization` | 0.90 | **Debole — sopra l'empirico** | utilizzo reale ~0.80 |

Benchmark di validazione (non parametri, ma target): quota salari, K/Y, quota
profitti, I/Y, utilizzo — vedi sotto.

---

## Parametri

### `alpha` = 1/3 — quota del capitale / elasticità del capitale
- **Ruolo:** esponente del capitale in `Y* = A·K^α·L^(1−α)`; determina anche le
  quote fattoriali (via il vincolo sul markup) e la relazione `K/Y = ρα/δ`.
- **Empirico:** ~1/3 è lo standard; range comune 0.25–0.40. Solow (1957) usò 0.35
  per gli USA. La quota della "compensation of employees" USA sta tra ~0.61 e
  0.68 (1960–2017), cioè quota del capitale ~0.32–0.39.
- **Fonti:** Gollin (2002), "Getting Income Shares Right"; Crafts (2021),
  *J. Economic Surveys* (growth accounting, α≈1/3 come buona approssimazione,
  cita Aiyar & Dalgaard 2005); Cottrell (2019), lecture notes Wake Forest
  (compensation share 0.61–0.68).
- **Caveat importante:** la quota del capitale è **cresciuta** nel XXI secolo
  (Karabarbounis & Neiman 2014, "The Global Decline of the Labor Share"); e la
  specificazione Cobb-Douglas a quote costanti è **empiricamente contestata**
  (Antràs 2004; Duffy & Papageorgiou 2000 rigettano Cobb-Douglas). α=1/3 è un
  benchmark difendibile, ma l'assunzione di quote costanti è una semplificazione,
  non un fatto.
- **Verdetto:** ben ancorato come valore standard; dichiarare l'assunzione di
  quote costanti come scelta.

### `sigma` (σ) = sweep, default 1.0 — elasticità di sostituzione K/L
> Introdotto dal brief 04 (branch `ces-production`). **È il parametro che determina
> il segno del risultato headline del progetto**, non un dettaglio tecnico.

- **Ruolo:** produzione **CES normalizzata**
  `Y* = Y0·[π0·(K/K0)^r + (1−π0)·(L/L0)^r]^(1/r)`, con `r = (σ−1)/σ`. Nidifica la
  Cobb-Douglas (σ=1, il core attuale) e la Leontief (σ→0). σ regola la forza della
  sostituzione capitale-lavoro, cioè **il meccanismo stesso** del risultato wage-led:
  più capitale ⇒ meno lavoratori per la stessa domanda ⇒ disoccupazione tecnologica.
- **Empirico:** la letteratura **rigetta esplicitamente σ = 1**.
  - Chirinko (2008), *J. Macroeconomics* 30(2): il peso dell'evidenza colloca σ tra
    **0.40 e 0.60**.
  - Chirinko & Mallick (2017), *AEJ: Macroeconomics* 9(4): stima **≈ 0.40**.
  - Knoblach, Roessler & Zwerschke (2020), *Oxford Bulletin of Economics and
    Statistics* 82(1): meta-regressione su **2.419 stime da 77 studi** → **0.45–0.87**,
    e **rigetta l'ipotesi Cobb-Douglas**.
  - Il modello **SIGMA** della Federal Reserve usa **0.5**.
  - **In controtendenza:** Karabarbounis & Neiman (2014), *QJE* 129(1), e Piketty &
    Zucman stimano **σ > 1**.
- **Il puzzle, dichiarato non nascosto:** la micro-letteratura converge sotto
  l'unità; la macro-letteratura sul declino della quota salari richiede σ>1. È una
  ragione **in più** per fare lo sweep invece di scegliere un valore.
- **Verdetto:** σ=0.5 è il valore centrale difendibile, ed è **più vicino a Leontief
  (σ=0) che alla Cobb-Douglas (σ=1)**: l'headline del branch `labour-market` poggia
  sull'estremo che i dati rigettano. Ma σ resta **uno sweep**, non un punto: il range
  plausibile (≈0.3–1.3, incluso il puzzle σ>1) copre entrambi i segni possibili.
  **Il default resta 1.0** perché deve riprodurre esattamente il branch precedente
  (criterio di identità), non perché 1.0 sia difendibile.

### `pi0` (π0) = 1/3 — quota del capitale nel punto base
- **Ruolo:** sostituisce `alpha` come **unica** nozione di quota del capitale nel
  codice. Con σ=1 è esattamente l'esponente Cobb-Douglas del capitale; per ogni σ è
  la quota del capitale **nel punto base** (proprietà della normalizzazione).
- **Ancoraggio:** identico ad `alpha` sopra (non è un parametro nuovo, è lo stesso
  rinominato). `Y0` è **derivato** (`A·K0^π0·L0^(1−π0)`), non un parametro libero.

### `K0`, `L0` = 41.87, 7.395 (per impresa) — ancora di normalizzazione
- **Ruolo:** punto base della CES normalizzata. **Scelta di modellazione, non una
  stima** — nessun referente empirico, e non ne serve uno.
- **Perché serve:** la CES "da manuale" non è sweepabile. Variando `r` a `(A, a)`
  fissi si muovono anche le quote fattoriali implicite e l'efficienza, quindi `A` e
  `a` **non sono confrontabili tra σ diversi** e il cambio di comportamento è
  **inattribuibile**. La normalizzazione fissa un punto base per cui passano tutte le
  varianti di σ con le stesse quote: solo così due economie differiscono *solo* per σ.
  Fonti: **Klump & de La Grandville (2000)**, *AER* 90(1) (introduce la
  normalizzazione); **Klump & Saam (2008)**, *Economics Letters* 98(3) (calibrazione
  nei modelli dinamici; senza normalizzazione il confronto tra σ è "arbitrario e
  inconsistente"); **Klump, McAdam & Willman (2012)**, *J. Economic Surveys* 26(5)
  (rassegna).
- **Caveat da riportare, non da nascondere:** **Temple (2012)**, *J. Macroeconomics*
  34(2), critica l'idea che la normalizzazione isoli gli effetti "puri" di σ e che σ
  sia un parametro profondo. Qui la normalizzazione è dichiarata per quello che è —
  un **dispositivo di confronto** che rende commensurabili le varianti di σ in un
  punto base — **non** una garanzia di causalità.
- **Come è stata ottenuta:** **misurata una volta** sullo steady state del branch
  `labour-market` (σ=1) a `ρ=0.40`, seed {0,1,2}, 2000 step, media delle ultime 50
  osservazioni, tutti gli altri parametri ai default (`initial_capital=40`,
  `wage_rate=0.9`, `c0=2.0`, N=100, 10 imprese). Aggregati misurati:
  K = 418.7356984217038, L = 73.95333333333333 su 10 imprese. Poi **congelata** in
  `model.ANCHOR_K0` / `model.ANCHOR_L0`: **la stessa per tutta la griglia** (σ, ρ),
  altrimenti la normalizzazione non normalizza niente.
- **Nota:** a σ=1 l'ancora è **irrilevante** (l'identità con la CD vale per qualunque
  `(K0, L0)` purché `Y0` sia calcolato); conta solo per σ≠1, e centra l'esperimento
  sulla regione di interesse. Per rendimenti di scala costanti la CES normalizzata è
  omogenea di grado 1: ancora per-impresa e ancora aggregata danno la stessa funzione.
- **Verdetto:** scelta di modellazione, dichiarata. Da riportare come tale.

### `markup` = 0.5 — derivato da α
> ⚠️ **STALE**: il parametro `markup` è stato **rimosso** dal codice al punto 11
> (branch `labour-market`), dove il salario fisso `w̄` è diventato il parametro
> distributivo e il profitto il residuo. Questa sezione descrive il core
> Cobb-Douglas *precedente*. Non risolto qui: fuori dallo scope del brief 04.
- **Ruolo:** fissa i prezzi e quindi la quota salari (`1/(1+markup)`). Vincolato:
  `markup = α/(1−α)` ⇒ quota salari = 1−α.
- **Empirico:** i markup medi misurati sono ben più alti (De Loecker, Eeckhout &
  Unger 2020 stimano markup in forte crescita, ~1.2–1.6 sul costo marginale), ma
  **non è ciò che questo parametro rappresenta qui**: nel modello il markup è uno
  strumento di coerenza distributiva, non un markup di mercato osservato.
- **Verdetto:** per costruzione, non da ancorare a markup empirici. Da
  ri-discutere solo quando (roadmap punto 9) il markup diventerà endogeno — a
  quel punto si scollega dalla quota salari e va ricalibrato con dati sui markup.

### `delta` = 0.05 — tasso di deprezzamento
- **Ruolo:** legge del moto del capitale `K(t+1) = (1−δ)K(t) + I`; entra in
  `K/Y = ρα/δ`.
- **Empirico:** il deprezzamento aggregato dipende dal mix di asset. BEA/BLS
  stimano i tassi per asset (Hulten–Wykoff come base) via perpetual inventory
  method; equipaggiamento deprezza più veloce delle strutture. Calibrazioni macro
  tipiche: 0.04–0.10 annuo. Manuali (es. problema Mankiw) usano ~0.04; Angeletos
  (2007) usa 0.08; RBC spesso ~0.10 annuo (0.025 trimestrale).
- **Fonti:** BEA, *Fixed Assets* e "BEA Depreciation Rates"; BLS (2022),
  "Alternative Capital Asset Depreciation Rates"; Angeletos (2007).
- **Verdetto: BUONO — e non è ancorabile in isolamento** (vedi §"Il sistema
  congiunto"). δ non è un parametro libero: dati i target `K/Y ≈ 2.6` e
  `I/Y ≈ 0.13`, l'identità di steady state `I = δK` impone
  `δ = (I/Y)/(K/Y) ≈ 0.05`. Il valore attuale è **esattamente** quello che rende
  i due benchmark reciprocamente coerenti in assenza di crescita di trend (il
  modello non ne ha). Confronto: Mankiw usa δ≈0.04 con K/Y≈2.5; Angeletos (2007)
  usa 0.08 (ma con altri target). **Non alzare δ "verso il centro della fascia
  di letteratura": sfonderebbe il target di I/Y.** Nota: se il "periodo" del
  modello non è un anno, l'interpretazione di δ (e di K/Y, I/Y) cambia —
  chiarire l'unità temporale.

### `retention_ratio` (ρ) = 0.40 — quota di profitto trattenuta/investita
- **Ruolo:** finanziamento interno; `I = clip(ρ·profit·util_effect, floor,
  profit)`; è il parametro headline dello sweep; determina `K/Y = ρα/δ`.
- **ATTENZIONE — errore di categoria da evitare.** ρ nel modello **non è una
  decisione di payout**: è il parametro che fissa il **tasso di investimento**
  (`I/Y = ρα`). Il modello non ha imposte né credito esterno, quindi l'impresa
  deve finanziare *tutto* l'investimento dalla ritenzione. Ancorare ρ al plowback
  ratio della corporate finance è quindi improprio: **va ancorato a I/Y**.
  (Cambierà al punto 14: col credito, ritenzione e investimento si scollegano e
  ρ tornerà a essere una vera decisione di payout, da ancorare ai dati di payout.)
- **Ancoraggio corretto (via I/Y):** con α=1/3, ρ=0.40 ⇒ `I/Y = 0.133`, contro un
  investimento fisso non residenziale/PIL USA di ~0.13–0.14. **Match buono.**
- **Dati aggregati sul payout (per riferimento, non per ancorare ρ qui):** in
  NIPA i profitti al lordo delle imposte (PBT) si scompongono in imposte +
  dividendi netti + **profitti non distribuiti** (= risparmio d'impresa, che
  finanzia gli investimenti di lungo periodo). L'analogo aggregato di un
  "retention ratio" sarebbe `undistributed profits / PBT`, che è **più basso** del
  plowback d'impresa (~0.4–0.6) perché le imposte prelevano una quota e i
  dividendi sono grandi. Indicazione di ordine: nella crescita dei profitti delle
  industrie non finanziarie domestiche post-COVID, ~76% è andato a dividendi, ~15%
  a profitti non distribuiti, ~9% a imposte (scomposizione della *crescita*, non
  dei livelli). I buyback complicano ulteriormente il quadro.
- **Fonti:** BEA, *NIPA Handbook* cap. 13 "Corporate Profits" (struttura
  PBT = imposte + dividendi + undistributed); BEA, "Corporate Profits"; St. Louis
  Fed (2025), "What's Driving the Surge in U.S. Corporate Profits?"; serie FRED
  rilevanti (CP, NFCPATAX). Corporate finance (plowback 0.4–0.6): Corporate
  Finance Institute; Wall Street Prep.
- **Verdetto:** 0.40 è **ben ancorato via I/Y**. Il fatto che coincida anche con
  la fascia bassa del plowback d'impresa è secondario e non va usato come
  giustificazione principale.

### `c0` = 1.0, `c1` ≈ 0.9 — consumo autonomo e MPC sul reddito
- **Ruolo:** funzione di consumo `C = c0 + c1·income + λ·wealth`. `c1` è l'MPC dei
  lavoratori; i capitalisti hanno MPC più bassa (leakage di risparmio).
- **Empirico/struttura:** la forma `c0 + c1·Y` viene direttamente da Teglio
  (2025): la domanda di consumo è la somma di una componente costante c0 e una
  proporzionale al reddito c1·Y. Il termine `λ·wealth` è l'estensione di questo
  progetto (wealth effect, vedi sotto). L'MPC aggregato è dibattuto (stime micro
  eterogenee, spesso 0.2–0.6 su shock transitori/permanenti; molto più alto per
  famiglie vincolate).
- **Fonti:** Teglio (2025) per la struttura c0+c1Y.
- **Verdetto:** la **forma** è ancorata a Teglio; il **livello** di `c0=1.0` è una
  scala del modello (10× la Fase 1), scelta per portare domanda nel regime
  capacity-constrained — è una scelta di regime, non una stima. `c1` come MPC è
  ragionevole ma non calibrato a una fonte specifica.

### `wealth_effect` (λ) = 0.08 — MPC sulla ricchezza
- **Ruolo:** termine `λ·wealth` nel consumo; leva di domanda che aiuta a portare
  l'economia capacity-constrained.
- **Empirico:** consenso robusto su **0.03–0.05** (3–5 cent per dollaro di
  ricchezza), range complessivo 0.02–0.07. Slacalek (2009): ~0.05 su 16 paesi.
  Case, Quigley & Shiller (2005): 3–4 cent (housing). Carroll, Otsuka & Slacalek
  (2011): immediato ~0.01–0.02, eventuale ~0.09 (housing). Fed FEDS note (2025):
  ~3.5 cent, in calo a ~2.7 cent. Effetto housing > finanziario.
- **Fonti:** Slacalek (2009); Case–Quigley–Shiller (2005); Carroll–Otsuka–
  Slacalek (2011); Federal Reserve FEDS note (2025), "Wealth Heterogeneity and
  Consumer Spending"; Paiella (2009) per la rassegna.
- **Verdetto:** **λ=0.08 è sopra il tetto empirico** e ~2× la stima centrale.
  Dichiarare esplicitamente come leva di regime. Per una calibrazione empirica,
  abbassare a ~0.03–0.05 (e ri-verificare che il regime capacity-constrained
  regga, o compensare con altre leve di domanda).

### `beta` = 0.5 — sensibilità dell'acceleratore all'utilizzo
- **Ruolo:** `util_effect = max(0, 1 + β·(u_last − target))`; modula
  l'investimento rispetto allo scostamento dell'utilizzo dal target.
- **Empirico:** esiste una lunga letteratura sull'acceleratore e sul
  "flexible accelerator" (Clark 1917; Chenery 1952; Koyck 1954) e su modelli di
  investimento (Jorgenson) e q di Tobin, ma **non c'è un valore canonico** per
  questa specifica elasticità in questa parametrizzazione.
- **Verdetto:** scelta di modellazione ragionevole; nessun ancoraggio numerico
  puntuale. Da esplorare in sensitivity analysis (roadmap punto 5) più che da
  "ancorare" a un singolo numero.

### `investment_floor` = 0.1 — capex minimo
- **Ruolo:** guardrail anti-collasso (con capitale essenziale, I=0 ⇒ K→0 ⇒ Y*→0).
- **Empirico:** nessun referente empirico diretto — è un espediente numerico.
- **Verdetto:** **scelta di modellazione** dichiarata; da testare in sensitivity
  (quanto il baseline a basso capitale dipende da questo valore).

### `target_utilization` = 0.90 — utilizzo di riferimento dell'acceleratore
- **Ruolo:** punto neutro dell'acceleratore; a `u = target`, `util_effect = 1`.
- **Empirico:** l'utilizzo medio USA (Fed) è ~80% (media dal 1967 ~81.6%; media
  1972–2025 ~79–80%); soglia inflazionistica ~82–85%. Quindi 0.90 è **sopra**
  l'utilizzo tipico osservato.
- **Fonti:** Federal Reserve G.17 (Industrial Production and Capacity
  Utilization); voce "Capacity utilization" (media storica ~81.6%).
- **Verdetto:** scelta di regime, sopra l'empirico. Coerente col fatto che il
  core opera a quasi-piena-capacità (vedi benchmark utilizzo).

---

## Il sistema congiunto (α, ρ, δ, K/Y, I/Y) — leggere prima di ricalibrare

**Questi parametri NON sono ancorabili in isolamento.** A steady state il modello
impone due sole relazioni indipendenti (dato α):

```
I/Y = ρ·α                    (l'investimento è la ritenzione, a util_effect≈1)
K/Y = ρ·α/δ                  (steady state: I = δK, nessuna crescita di trend)
  ⇒ I/Y = δ · (K/Y)          (identità)
```

Quindi: **ρ fissa I/Y; δ fissa K/Y dato I/Y.** Due gradi di libertà, non quattro.
Non si può scegliere δ "guardando la letteratura su δ" senza spostare I/Y o K/Y.

**La calibrazione attuale centra entrambi i benchmark simultaneamente:**

| | modello (α=1/3, ρ=0.40, δ=0.05) | empirico | esito |
|---|---|---|---|
| I/Y | 0.133 | ~0.13–0.14 (inv. fisso non res./PIL) | ✓ |
| K/Y | 2.67 analitico / 2.58 misurato | ~2.5–3 | ✓ |

E δ ≈ 0.05 **è implicato** dai due target: `δ = (I/Y)/(K/Y) = 0.133/2.6 ≈ 0.05`.

**Errore da non ripetere (commesso e corretto in fase di ricerca):** si era
proposto di alzare δ verso 0.06–0.07 "perché più centrale nella letteratura di
calibrazione", compensando con ρ→0.47–0.55 per tenere K/Y in banda. Sbagliato:
avrebbe portato **I/Y a 0.157–0.183**, sfondando il target di investimento.
δ=0.05 non è "fascia bassa da correggere": è il valore congiuntamente coerente.
Per confronto, Mankiw usa δ≈0.04 con K/Y≈2.5 — *più basso* del valore attuale.

**Conseguenza per la scrittura:** il match congiunto di K/Y *e* I/Y è un
risultato di calibrazione genuino e va rivendicato come tale — ma va detto che è
un sistema a due gradi di libertà, non due validazioni indipendenti.

---

## Benchmark di validazione (target, non parametri liberi)

### Quota salari / quota profitti — 0.667 / 0.333
- Nel modello: esatte per costruzione (markup = α/(1−α)). Empiricamente la quota
  salari USA è ~0.60–0.68 (compensation share) → il valore 0.667 è realistico.
  Fonte: Cottrell (2019); Gollin (2002). **Match buono.**

### K/Y — 2.58 (target 2.5–3)
- Nel modello: `K/Y = ρα/δ`. Empiricamente il rapporto capitale-prodotto
  *produttivo* è ~2.5–3 (manuali: ~2.5; misure variano col perimetro di
  capitale). Fonte: calibrazione standard (Mankiw). **Match buono**, ma dipende
  da δ (fascia bassa) e ρ.

### I/Y — 0.133
- Nel modello: `I/Y = ρα`. Da confrontare con l'investimento fisso non
  residenziale/PIL USA (~0.13–0.14) — **coincidenza incoraggiante, DA VERIFICARE**
  con dato primario (BEA NIPA); attenzione a gross vs net e al perimetro.

### Utilizzo della capacità — 0.99 (modello) vs ~0.80 (empirico)
- **Discrepanza rilevante, dichiarata.** Il modello opera a quasi-piena-capacità
  ovunque; l'economia reale opera ~80% con slack persistente. È la firma del
  regime supply-constrained del core (vedi README, *Interpretive frame*). Fonte:
  Federal Reserve G.17. **Non un match** — è una scelta di regime da esplicitare.

---

## Tensioni aperte / cose da fare

1. ~~Rafforzare `retention_ratio` con una fonte aggregata di payout~~ **RISOLTO
   diversamente:** ρ va ancorato a I/Y, non al payout (vedi voce `retention_ratio`
   e §"Il sistema congiunto"). Nessuna ricalibrazione δ/ρ: la coppia attuale è
   congiuntamente coerente.
2. **`wealth_effect=0.08` e `target_utilization=0.90`** sono sopra l'empirico:
   decidere se (a) ricalibrare verso i valori empirici e accettare un regime
   diverso, o (b) tenerli come leve di regime *dichiarate*. Non presentarli come
   stime.
3. **Unità temporale del periodo:** chiarirla, perché δ, K/Y, I/Y sono
   annualizzati implicitamente.
4. **Assunzione Cobb-Douglas a quote costanti:** dichiararla come scelta, citando
   la critica empirica (Karabarbounis–Neiman; Antràs).
5. **Verificare I/Y** con dato BEA primario (serie NIPA investimento fisso non
   residenziale/PIL): il match a 0.133 regge su una cifra di ordine di grandezza,
   non ancora su una serie estratta. Attenzione a gross vs net e al perimetro di
   capitale (il modello ha solo capitale produttivo d'impresa, niente residenziale).
6. **Ancoraggio delle leve di domanda: rimandato al punto 11.** λ e
   `target_utilization` non vanno ancorati in questo core: l'empirico
   (λ≈0.05, u≈0.80) implica un regime **demand-constrained**, in cui il capitale
   non morde — cioè il regime che questo core esiste per superare. La tensione si
   scioglie con il mercato del lavoro, dove lo slack diventa disoccupazione e un
   regime demand-constrained realistico può convivere con un canale di offerta
   vivo. Fino ad allora: leve di regime **dichiarate**, non stime.
6. **Prossimo:** al punto 9 (markup endogeno) il legame markup↔quota salari salta
   e serviranno dati sui markup (De Loecker et al.).

---

## Riferimenti

- Teglio, A. (2025). Rationality, inequality, and the output gap: evidence from a
  disaggregated Keynesian cross diagram. *Journal of Economic Interaction and
  Coordination*, 20(1), 107–139. (online-first 2024)
  <https://link.springer.com/article/10.1007/s11403-024-00412-4>
- Gollin, D. (2002). Getting Income Shares Right. *Journal of Political Economy*.
- Crafts, N. (2021). Growth accounting in economic history. *Journal of Economic
  Surveys*. <https://onlinelibrary.wiley.com/doi/10.1111/joes.12348>
- Karabarbounis, L. & Neiman, B. (2014). The Global Decline of the Labor Share.
  *Quarterly Journal of Economics*, 129(1), 61–103.

### Elasticità di sostituzione σ (brief 04)
- Chirinko, R. S. (2008). σ: The long and short of it. *Journal of Macroeconomics*,
  30(2), 671–686.
- Chirinko, R. S. & Mallick, D. (2017). The Substitution Elasticity, Factor Shares,
  and the Low-Frequency Panel Model. *American Economic Journal: Macroeconomics*,
  9(4), 225–253.
- Knoblach, M., Roessler, M. & Zwerschke, P. (2020). The Elasticity of Substitution
  Between Capital and Labour in the US Economy: A Meta-Regression Analysis. *Oxford
  Bulletin of Economics and Statistics*, 82(1), 62–82.

### CES normalizzata (brief 04)
- Klump, R. & de La Grandville, O. (2000). Economic Growth and the Elasticity of
  Substitution: Two Theorems and Some Suggestions. *American Economic Review*,
  90(1), 282–291.
- Klump, R. & Saam, M. (2008). Calibration of normalised CES production functions in
  dynamic models. *Economics Letters*, 98(3), 256–259.
- Klump, R., McAdam, P. & Willman, A. (2012). The Normalized CES Production Function:
  Theory and Empirics. *Journal of Economic Surveys*, 26(5), 769–799.
- Temple, J. (2012). The calibration of CES production functions. *Journal of
  Macroeconomics*, 34(2), 294–303. (**critica**: la normalizzazione non isola effetti
  "puri" di σ; σ non è un parametro profondo — da riportare, non nascondere.)
- Antràs, P. (2004). Is the U.S. Aggregate Production Function Cobb-Douglas?
- Solow, R. (1957). Technical change and the aggregate production function.
- BEA, Fixed Assets Accounts & Depreciation Rates. <https://www.bea.gov/itable/fixed-assets>
- BLS (2022). Alternative Capital Asset Depreciation Rates for U.S. Capital.
  <https://www.bls.gov/opub/mlr/2022/article/alternative-capital-asset-depreciation-rates-for-us-capital-and-total-factor-productivity-measures.htm>
- Angeletos, G.-M. (2007). Uninsured idiosyncratic investment risk. (δ=0.08, α=0.36)
- Slacalek, J. (2009). What Drives Personal Consumption? The Role of Housing and
  Financial Wealth. *B.E. Journal of Macroeconomics*.
- Case, K., Quigley, J. & Shiller, R. (2005/2013). Comparing Wealth Effects.
- Carroll, C., Otsuka, M. & Slacalek, J. (2011). How Large Are Housing and
  Financial Wealth Effects? *Journal of Money, Credit and Banking*.
- Federal Reserve (2025). Wealth Heterogeneity and Consumer Spending. FEDS Notes.
  <https://www.federalreserve.gov/econres/notes/feds-notes/wealth-heterogeneity-and-consumer-spending-20250805.html>
- Paiella, M. (2009). The stock market, housing and consumer spending: a survey.
- Federal Reserve. G.17 Industrial Production and Capacity Utilization.
  <https://www.federalreserve.gov/releases/g17/current/>
- De Loecker, J., Eeckhout, J. & Unger, G. (2020). The Rise of Market Power.
  *Quarterly Journal of Economics*.
- Cottrell, A. (2019). The Cobb–Douglas Production Function. Lecture notes.
